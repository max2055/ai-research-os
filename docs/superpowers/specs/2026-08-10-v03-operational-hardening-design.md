# v0.3 Operational Hardening Design

Date: 2026-08-10

Status: approved design, implementation pending

Scope: close all current work that is not dependent on the natural-time gates in
WP-530 and WP-620.

## 1. Context and invariants

AI Research OS is a local-first, single-user research system. Markdown remains the
authority for research objects. The Candidate SQLite database, generated indexes,
Dashboard views, health data, benchmark fixtures, and backup receipts are operational
or derived state.

This work preserves the following invariants:

- facts, inferences, and judgments remain distinct;
- generated research stays `review_status: pending` until a real human decision;
- no Agent approves Evidence, Impact Assertions, Thesis confidence, Recommendations,
  or a release;
- failed Job records are immutable operational evidence, not records to rewrite;
- Dashboard authoritative research routes remain read-only and loopback-only;
- secrets, private keys, Candidate databases, raw licensed assets, and decrypted
  backup material never enter Git;
- WP-530 and WP-620 remain open until their real dates and observations;
- v0.3 release readiness is independent from engineering completion.

The implementation will run in an isolated Git worktree. Existing changes in the main
workspace will be preserved and incorporated only when they are in scope.

## 2. Work packages and order

The work is split into seven reviewable packages:

1. Job audit and Discovery transport reliability.
2. 10,000-Candidate benchmark and any evidence-driven index correction.
3. v0.3 F-023 release checker.
4. Private remote CI.
5. Durable encrypted backup, backup alerts, and cost monitoring.
6. Impact Assertion Agent audit and operations documentation.
7. Repository-wide Ruff formatting as an isolated mechanical change.

Packages 1-6 contain functional or research changes. Package 7 is separate so that
format churn cannot hide behavioral changes. The integration branch is pushed only
after local full verification. Remote CI is then observed to completion before merge.

## 3. Existing Job records

The 30 untracked Job files are append-only operational evidence. The audit currently
shows 28 successful Jobs and two failed arXiv Discovery Jobs. The failed records show
`SSL: UNEXPECTED_EOF_WHILE_READING`; later records show that the sweep continued and
other channels succeeded.

The implementation will:

- copy all 30 records into the isolated worktree without rewriting their result;
- validate their IDs, timestamps, status, target, message, and Candidate run links;
- regenerate derived indexes after the records are tracked;
- add a concise audit document that classifies the two failures as retained incidents
  and links them to the transport correction and post-fix verification;
- never change a failed Job to success or delete it to make Health look clean.

## 4. Discovery retry design

### 4.1 Root cause

The common `fetch_text` transport currently performs one `urlopen` call with a
30-second timeout. Operational logs show intermittent TLS EOF, DNS, and connection
failures followed by successful requests to the same classes of endpoints. The
transport therefore lacks bounded handling for transient network failures; feed
parsing and Channel policy are not the cause of those failures.

### 4.2 Policy

The shared fetcher will perform at most three attempts. Delay uses bounded exponential
backoff plus jitter. Tests inject the sleeper and jitter source so they remain fast
and deterministic.

Retriable failures are limited to:

- TLS EOF and handshake interruption;
- connection reset, timeout, and temporary DNS failure;
- HTTP 408, 425, 429, 500, 502, 503, and 504.

`Retry-After` is honored when valid and capped by the configured maximum delay.
Policy, allowlist, license, response-size, media, decoding, and parsing errors are not
retried. Redirect count is bounded, and every redirect target must remain inside the
adapter's explicit host allowlist; a rejected redirect is never retried.

After exhaustion, the exception states the safe failure class and attempt count. It
does not contain authorization headers, query secrets, or response bodies. One
Discovery run and one final Job outcome remain the audit unit; internal attempts do
not create duplicate Candidate rows or duplicate Job objects.

### 4.3 Verification

Tests cover immediate success, retry then success, exhaustion, non-retriable errors,
`Retry-After`, delay caps, response limits, redaction, and idempotent Candidate insert.
A real read-only arXiv Discovery run verifies the corrected transport without
promoting a Source or changing research authority.

## 5. 10,000-Candidate SLO benchmark

The benchmark uses a disposable schema-current SQLite database populated with exactly
10,000 representative Candidate rows. It does not modify the real Candidate store or
formal objects.

The measured operation is the Candidate Queue product path: common status/channel/
score filters, priority ordering, pagination, and row rendering. The benchmark records
machine/runtime details, fixture distribution, warm-up policy, all samples, nearest-
rank p95, query plan, database size, and authoritative write count.

Acceptance is Candidate Queue p95 below 2 seconds. Storage or caching architecture is
not changed when the target passes. If it fails, profiling must identify the query or
render bottleneck before a minimal index or query correction is proposed. Any SQLite
migration remains versioned, idempotent, backed up, and tested for rollback.

The result updates `00_System/v0.3_Performance_Benchmark.md` and removes only the
specific limitation that 10k Candidate filtering was unmeasured. It does not claim
multi-user, 100k-row, or distributed performance.

## 6. F-023 v0.3 release checker

The existing v0.2 18-gate checker remains backward compatible and remains the default.
The CLI adds an explicit v0.3 selection and a machine-readable representation.

Exit codes are stable:

- `0`: every selected release gate is ready;
- `1`: the check ran successfully and at least one gate is blocked;
- `2`: the checker could not evaluate its inputs.

The v0.3 checker maps every Phase 6 section 11 item to a stable key, requirement,
observed evidence, status, and evidence path. Machine-verifiable conditions are
computed from current objects, indexes, acceptance records, benchmark records,
recovery evidence, and security tests. Human or natural-time gates pass only when the
required real records exist with valid reviewer, date, and decision fields.

At the current date the checker must report `BLOCKED`. At minimum, WP-530 natural
Forecast resolution, WP-620 real Pilot evidence, and F-024 human release approval stay
visible as independent blockers. The checker never creates a release packet, Review
Decision, tag, or release.

Tests cover complete key coverage, missing and malformed evidence, reviewer denylist,
future-date protection, no mutation, v0.2 compatibility, text output, JSON output,
and exit codes.

## 7. Private remote CI

The private GitHub repository is the CI authority for pushed commits. A workflow runs
on pull requests, pushes to `main`, and manual dispatch with minimum read-only token
permissions.

The workflow installs the supported Python environment from the lockable project
metadata and runs:

- repository validation;
- global, PRJ-001, and PRJ-002 index checks;
- the complete pytest suite;
- Ruff lint and format checks;
- mypy over `src/research_os`;
- loopback Dashboard route smoke;
- v0.3 release check assertion that the command evaluates successfully and returns
  the currently expected blocked status.

CI does not require provider keys, decrypt backups, access raw ignored Source assets,
or treat unavailable secrets as a product failure. Dependency caches cannot contain
repository secrets. Logs and uploaded diagnostics are screened for sensitive values.

The implementation is not considered remotely verified until the branch is pushed
and the matching GitHub Actions run completes successfully.

## 8. Durable encrypted backup

### 8.1 Backup sets

The durable backup command covers two independent sets:

- the Candidate SQLite snapshot and its integrity manifest;
- the immutable Source asset tree and an inventory of source IDs, relative paths,
  sizes, and SHA-256 values.

Git and Markdown continue to be recovered from the private repository. Secrets,
local provider configuration, and scheduler installation are documented as separate
recovery prerequisites rather than silently bundled.

### 8.2 Encryption and destination

`age` is used for authenticated file encryption. One or more recipients are supplied
through an ignored local configuration file or explicit CLI arguments. Existing SSH
public keys may be recipients. Private identities are resolved only during restore
and never copied into backup manifests, logs, Markdown, GitHub configuration, or Git.

The first remote backend uploads ciphertext and a non-sensitive outer manifest to a
dedicated prerelease in the configured private GitHub repository. Asset names include
the UTC backup ID and set type. Upload is explicit `--apply`; dry-run performs all
preflight checks without creating local or remote files. The backend interface keeps
destination concerns separate so object storage can be added later without changing
snapshot or encryption semantics.

### 8.3 Transaction and evidence

The pipeline is:

```text
preflight
-> immutable local snapshot/archive
-> plaintext integrity verification
-> age encryption
-> ciphertext hash
-> remote upload
-> remote metadata verification
-> ignored local receipt
-> Job outcome
```

Temporary plaintext remains in a permission-restricted temporary directory and is
removed on success or failure. Existing backup assets are never overwritten. A
partial upload is reported as failed and cannot update the last-success receipt.

The receipt contains backup ID, set coverage, creation time, ciphertext hashes,
remote repository/release/asset identifiers, and verification status. It contains no
key, secret, raw Source content, or Candidate rows.

### 8.4 Restore and alerts

Restore is always explicit and targets a disposable directory by default. It verifies
the outer manifest and ciphertext hash before decrypting, then verifies SQLite
integrity/schema/hash and every Source asset inventory entry. It refuses unexplained
overwrites.

Health reports local snapshot age and durable remote receipt age separately. Missing,
failed, invalid, or older-than-24-hour durable backup status is P1. Configuration
presence is reported without values. Network verification is an explicit command;
normal Dashboard rendering reads the local receipt and does not make a remote call.

The recovery record distinguishes data recovery from private-key recovery. At least
one matching private identity must be tested locally before declaring the encrypted
backup usable; custody of a second independent key copy remains an operator security
responsibility and is stated explicitly.

## 9. Cost monitoring

Cost monitoring uses Decimal arithmetic and a single configured reporting currency.
It aggregates known numeric `cost_estimate` records over a configured monthly window
and compares them with `RESEARCH_OS_MODEL_COST_BUDGET`.

The state machine is:

- `unconfigured`: no valid budget;
- `no_data`: budget exists but no usable cost records;
- `ok`: known cost below 80 percent of budget;
- `warning`: known cost at or above 80 percent and below 100 percent;
- `exceeded`: known cost at or above budget;
- `invalid`: malformed budget or cost data.

The display includes period, currency, known total, budget, utilization, record count,
and invalid/unknown record count. It never equates missing records with zero cost.
Budget status is operational evidence, not an investment conclusion.

## 10. Impact Assertion Agent audit

Each of the 22 pending Impact Assertions is audited against its exact reviewed Event,
referenced Source and citation anchors, entity types, approved impact rule map, and
relevant ontology relations.

The checklist covers:

- Event and Source support;
- fact versus inference versus judgment boundaries;
- source attribution and company-claim labeling;
- source independence and known limitations;
- source and target entity correctness;
- impact type, direction, horizon, mechanism steps, and weakest-link confidence;
- reverse factors, contradicting evidence, and alternative explanations;
- company operating impact versus Security price impact;
- uncertainty, unknowns, and overclaim risk.

An assertion may receive one of three Agent recommendations:

- `ready_for_human_review`;
- `edit_required`;
- `reject_recommended`.

The Agent may correct a pending assertion only when the correction is directly
supported by traceable repository evidence and preserves manual notes. Every modified
assertion remains `review_status: pending`. The audit produces Markdown and structured
JSON packets with before/after notes and evidence paths. It does not create a Review
Decision, name a human reviewer, change Thesis confidence, or make pending assertions
visible in reviewed impact paths.

## 11. Documentation and formatting

The User Runbook, launchd runbook, recovery documentation, Known Limitations,
performance record, and Master Backlog are updated to match implemented commands and
measured evidence. Facts, inferences, judgments, remaining natural-time blockers, and
operator key-custody responsibilities remain explicit.

After all functional changes pass, `ruff format` is applied repository-wide as a
dedicated mechanical commit. The formatter commit contains no intentional behavior,
schema, research content, or generated-index changes. Ruff format check, compilation,
and the full test suite verify it separately.

## 12. Verification and delivery

Targeted tests are written before each behavioral correction. Completion requires all
of the following on the final branch state:

- `research-os doctor` without unresolved runtime failure;
- `research-os validate` with 0 errors and 0 warnings;
- global, PRJ-001, and PRJ-002 index drift at 0;
- complete pytest suite passing with only documented skips;
- Ruff lint and format checks passing;
- mypy passing for all source files;
- Git diff whitespace check passing;
- ten real repository Dashboard GET routes returning HTTP 200;
- real read-only Discovery verification;
- measured 10k Candidate Queue p95 below 2 seconds or an explicit failed Gate;
- encrypted backup creation, private remote upload, download, decryption, and
  integrity restore passing;
- v0.3 release check returning `BLOCKED` with WP-530/WP-620/F-024 visible;
- private GitHub Actions run passing for the pushed branch.

Commits are small and scoped. The integration branch is pushed, CI is observed, and
then it is merged into `main` without losing existing workspace data. A final
requirement-by-requirement audit records the command outputs, commits, remote run, and
remaining natural-time gates. No v0.3 tag or final release is created.
