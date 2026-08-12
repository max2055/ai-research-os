# F-026 Web Mutation Foundation Design

Status: approved design

Date: 2026-08-12

Reviewer: max

Governing decision: `RCP-v03-011`

## 1. Goal

Build the reusable security and transaction foundation for authoritative Web
mutations, then prove it through one real, recoverable workflow: dismissing a
Candidate from its detail page.

The website is the sole user-facing product interface. Existing CLI code remains an
internal migration, scheduler, diagnostic, test, and disaster-recovery adapter until
F-027/F-028 reach parity and the CLI retirement Gate passes.

## 2. Frozen scope

Top-level implementation tasks: 6.

1. Local fixed Web identity and browser session/CSRF protection.
2. Shared preview-token and nonce lifecycle.
3. Operational mutation audit storage.
4. Candidate dismiss adapter with atomic business/audit commit.
5. Candidate detail, confirmation, and result/error Web flows.
6. Security, transaction, integration, and regression verification.

Resource budget: one local single-process implementation, one Candidate workflow,
focused tests during development, and one complete repository Gate on the final
integration candidate.

Non-scope:

- Candidate promote, restore, bulk actions, or arbitrary Candidate editing.
- Review approval or any authoritative research-object approval.
- Thesis editing or confidence changes.
- Login, multiple users, roles, remote access, or public deployment.
- Persistent preview tokens or a background command queue.
- F-027/F-028 workflow parity or physical CLI removal.
- Changes to Research Rules, Source Policy, Taxonomy, object schemas, or the F-023
  21-check release contract.

## 3. Existing system constraints

- FastAPI renders the local website from `src/research_os/ui/app.py`.
- The current application binds to loopback and has three non-GET LLM configuration
  routes. Those routes are the implementation baseline, not the future mutation
  security contract.
- `services.triage.dismiss_candidate()` already validates actor/reason, applies a
  SQLite transaction, and appends `candidate_actions` audit rows.
- `repositories.transaction.FileTransaction` provides atomic multi-file commit and
  rollback for later Markdown-backed workflows.
- `services.reviews` already enforces structured reviewer, decision, date, and target
  checks. F-026 does not expose it through the Web.
- Markdown remains authoritative for formal research objects. Candidate SQLite remains
  an operational store.

## 4. Chosen architecture

Use a shared Mutation Gateway between Web routes and existing domain services.

```text
FastAPI route
  -> loopback Host + same-origin Origin guard
  -> browser session + CSRF guard
  -> fixed server-side research identity
  -> Mutation Gateway
       -> canonical operation input
       -> target version snapshot
       -> signed preview token
       -> in-process nonce registry
       -> mutation audit
  -> Candidate dismiss adapter
  -> existing triage service
  -> Candidate SQLite + candidate_actions
```

The Gateway owns transport-independent mutation security. Business adapters own the
translation from a named operation to an existing domain service. Route handlers do
not duplicate Candidate or future Review rules.

Rejected approaches:

- Per-workflow security logic: faster for the first route but likely to produce
  inconsistent protection between operational and authoritative decisions.
- Persistent command queue: adds async execution, retries, recovery, and lifecycle
  states that the current local single-user product does not need.
- Commit with a repeated editable form payload: cannot prove that execution matches
  the content the researcher approved.

## 5. Fixed researcher identity

The application reads `researcher_id` and a high-entropy `mutation_signing_secret`
from `00_System/web.local.json`. The existing `*.local.json` ignore rule keeps this
file out of Git. The configuration must be owner-readable only (`0600` where supported).
Identity and secret are loaded server-side and are never accepted from a form, JSON
body, query parameter, header supplied by page JavaScript, or preview token override.

Requirements:

- A non-empty, bounded researcher ID is required for every mutation.
- Missing or invalid identity or signing-secret configuration does not prevent GET/read
  workflows.
- Mutation preview and commit return `503` when either required value is unavailable.
- Changing the configured identity invalidates outstanding previews because the token
  and nonce are bound to the original actor.
- Background jobs and Agents receive no browser session and no Mutation Gateway
  approval capability.

This is deliberately not an authentication system. Remote or multi-user deployment
requires a separate RCP with authentication and authorization.

## 6. Browser session and CSRF boundary

The local website creates an opaque browser-session identifier in a cookie with:

- `HttpOnly`;
- `SameSite=Strict`;
- a bounded lifetime;
- `Secure` when the request is served over HTTPS;
- no researcher name, secret, or business data in the cookie.

Every state-changing form contains a session-bound CSRF token generated by the
server. Preview and commit require all of the following:

1. loopback Host accepted by the existing deployment boundary;
2. same-origin Origin matching the request scheme and Host;
3. a valid browser-session cookie;
4. a valid session-bound CSRF token.

Failure returns `403` with a generic response. The response and logs do not disclose
whether the session, Origin, or token was the failing component.

The preview signature and CSRF token solve different problems. CSRF proves that the
request came from the rendered site; the preview signature proves that commit matches
the exact server-calculated change the researcher saw.

## 7. Preview contract

Preview is read-only with respect to Candidate business state. The Candidate dismiss
adapter calls the existing service with `apply=False`, then creates this canonical
preview payload:

```text
mutation_id
operation = candidate.dismiss
actor
target_id
target_version
normalized_input = {reason}
summary = {status_before, status_after}
issued_at
expires_at
nonce
```

The current Candidate schema has no `updated_at` column. `target_version` is therefore
a SHA-256 digest of a canonical serialization of the complete current Candidate row,
with column names sorted and values normalized. This detects status changes as well as
concurrent enrichment or linkage changes without adding a new Candidate version field.
It is always recomputed from SQLite and never accepted from the browser.

The Gateway canonicalizes the payload, signs it with an application secret stored
outside Git, and returns a compact opaque preview token. The confirmation page renders
only server-calculated, HTML-escaped values. It contains the preview token and CSRF
token but no editable or authoritative copies of actor, target ID, reason, or status.

Preview writes one operational audit event with status `previewed`. It does not update
the Candidate and does not create a `candidate_actions` row.

## 8. Preview token and nonce lifecycle

Preview tokens expire 10 minutes after issuance. A process-local nonce registry stores
the mutation ID, actor binding, expiry, target version, and lifecycle state. It does
not store the signing secret or raw token.

States:

```text
issued -> committing -> consumed
                 \-> issued (retryable transaction failure only)
```

Rules:

- Restarting the Web process invalidates all outstanding previews.
- A missing nonce, expired token, consumed token, actor mismatch, signature failure,
  operation mismatch, or target-version mismatch never executes the adapter.
- A successful commit consumes the nonce immediately after the atomic business/audit
  transaction succeeds.
- A business or security conflict is not retryable with the same token.
- A transient transaction failure restores `committing` to `issued` if the token has
  not expired and the target version remains unchanged.
- In-process locking prevents concurrent commit requests from both entering the
  adapter for the same nonce.

## 9. Commit contract

The confirmation form posts only the preview token and CSRF token. Commit performs:

1. Host, Origin, session, CSRF, and fixed-identity validation.
2. Token signature, operation, actor, expiry, and nonce validation.
3. Current Candidate target-version recomputation.
4. A transition of the nonce from `issued` to `committing` under a process lock.
5. `candidate.dismiss` execution using the token-bound target and normalized reason.
6. One SQLite transaction that updates Candidate status, appends the existing
   `candidate_actions` row, and appends the `committed` mutation audit event.
7. Nonce consumption and `303 See Other` redirect to a GET result/detail page.

Commit accepts no alternate target ID, reason, actor, or desired status. Refreshing the
GET result page cannot repeat the POST.

## 10. Operational mutation audit

Add a generic mutation audit table through the next Candidate DB schema migration. The
migration increments `PRAGMA user_version`, preserves every existing Candidate/action,
has a tested rollback path, and is included in backup/recovery compatibility checks.
The table is operational state, not an authoritative research object, and does not
replace domain-specific audit rows.

The audit stores:

- event ID and mutation ID;
- event type/status (`previewed`, `committed`, `rejected`, or `expired`);
- operation;
- actor;
- target type and target ID;
- target-version digest;
- normalized-input digest, not the signing token;
- issued/event/expiry timestamps;
- redacted reason code;
- related domain action ID when committed.

It never stores the raw preview token, signing secret, CSRF token, session ID, provider
secret, or stack trace. Raw business input is stored only when the existing domain audit
already requires it; the generic audit uses a digest and bounded redacted metadata.

Preview audit is an independent committed event because it records what was shown but
does not alter business state. Successful commit audit and Candidate business changes
must use the same SQLite transaction. An attempted commit that is actually received
and rejected appends a rejected/expired audit event where safely attributable to a
known mutation ID. Merely reaching `expires_at` without another request is derived
state and does not create a fabricated event.

## 11. Candidate dismiss Web flow

1. The Candidate detail page shows a dismiss form only when the Candidate can be
   dismissed and a researcher identity is configured.
2. The researcher enters a required reason and submits Preview.
3. The server validates the request and domain rules without writing Candidate state.
4. A dedicated confirmation page shows actor, Candidate, current status, resulting
   status, reason, and expiry.
5. Cancel returns to the Candidate detail page with no business write.
6. Confirm posts only the preview token and CSRF token.
7. Success redirects with `303` to the Candidate detail/result page, which displays the
   resulting status and domain action/mutation audit identifiers.
8. The page offers a navigation hint to the existing Candidate workflow; Candidate
   restore is not implemented in this slice.

The UI follows the existing local Dashboard styling. It does not introduce a client
state framework or modal workflow.

## 12. Errors and retry behavior

| Condition | Status | Write behavior | User action |
|---|---:|---|---|
| Identity missing | 503 | none | configure local researcher identity |
| Host/Origin/session/CSRF invalid | 403 | no business write | reload from the local site |
| Invalid reason/input | 422 | no business write | correct input |
| Candidate cannot be dismissed | 409 | no business write | return to current Candidate state |
| Token invalid or actor mismatch | 403 | no business write; redacted rejection when attributable | start a new preview |
| Token expired/restart/nonce missing | 409 | no business write | start a new preview |
| Token consumed or commit already active | 409 | no duplicate write | use current Candidate state |
| Target version changed | 409 | no business write; `target_changed` audit | start a new preview |
| SQLite/transaction failure | 500 | Candidate/action/commit audit all roll back | retry same token if still valid |
| Success | 303 | one atomic business/audit commit | follow redirect |

Server responses never expose a signing secret, raw token, CSRF value, session ID,
absolute file path, SQL statement, or stack trace.

## 13. Testing strategy

All production behavior is implemented test-first. Each new behavior must first fail
for the expected missing-feature reason.

Unit/contract coverage:

- fixed identity loads from ignored local configuration and cannot be overridden;
- missing identity preserves GET access and blocks mutations with `503`;
- canonical payload and signature reject tampering and actor/operation mismatch;
- nonce expiry, restart, re-use, concurrent commit, and retry state transitions;
- target-version digest changes when mutable Candidate state changes;
- audit redaction excludes all tokens and secrets.

HTTP/security coverage:

- non-loopback Host and cross-origin Origin rejected;
- missing/wrong session or CSRF rejected;
- preview causes no Candidate or `candidate_actions` change;
- confirmation page escapes Candidate title and reason;
- hidden form contains no actor/target/reason override fields;
- tampered, expired, restarted, repeated, and stale-target commit rejected;
- successful commit returns `303` and refresh does not repeat it;
- existing LLM configuration behavior remains covered.

Transaction coverage:

- success updates Candidate, appends `candidate_actions`, and appends committed mutation
  audit in one transaction linked by `mutation_id`;
- injected failure at each write boundary rolls back all three business/commit records;
- preview audit remains accurate and does not imply that commit occurred.

Governance/regression coverage:

- no Gateway adapter exists for Review approval or Thesis confidence;
- background jobs cannot construct a named human browser session;
- strict repository validation and index checks remain clean;
- the existing F-023 21-check contract remains unchanged;
- the focused suite, complete repository tests, Ruff, mypy, and security checks pass on
  the final integration candidate.

## 14. Completion criteria

F-026's first vertical slice is complete only when:

- Candidate dismiss can be previewed and committed entirely through the website;
- the committed action exactly matches the signed preview;
- actor is fixed server-side and cannot be supplied by the request;
- CSRF, token, nonce, target-version, replay, and transaction-failure tests pass;
- Candidate state, domain action, and committed mutation audit are atomic;
- the shared Gateway API is sufficiently generic for later F-027 adapters without
  including their business logic;
- current read-only routes and LLM configuration routes do not regress;
- final repository verification passes;
- documentation states that F-027/F-028 and CLI retirement remain incomplete.
