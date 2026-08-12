# Web-only Product Parity Design

Date: 2026-08-13
Status: approved by explicit autonomous-execution instruction
Scope: F-027 through F-029

## Goal

Make the local website the complete user-facing product for AI Research OS. Every
current CLI capability must end in exactly one of three states: represented by a
domain-specific Web workflow, retained only as a non-user scheduler/recovery service
entry, or deleted. Product documentation and navigation must require no terminal use.

## Frozen delivery contract

- Top-level delivery packages: 3 (`F-027`, `F-028`, `F-029`).
- Implementation sequence: research workflow parity, operations/recovery parity, CLI
  retirement.
- Resource budget: one feature branch, one implementation owner per behavior, focused
  tests per slice, and one complete repository Gate per delivery package.
- Authority: the user explicitly authorized autonomous planning and execution without
  intermediate product confirmation.
- Non-scope: remote or multi-user deployment; broker/trade execution; automatic
  approval; automatic Thesis conclusion/confidence changes; changing research rules,
  taxonomy, evidence authority, release blockers, or real-date Gate requirements.
- Existing untracked operational Job records are external state. They are never
  deleted, rewritten, or committed merely to make a Gate pass.

## Chosen architecture

Use a service-first Web command architecture. FastAPI handlers translate bounded form
input into typed application commands. Commands call existing domain services and
return canonical preview/result models. The browser never edits Markdown or SQLite
directly, and the server never shells out to the CLI.

The rejected alternatives are:

1. A browser terminal that runs CLI strings. It preserves CLI coupling, expands
   injection risk, and does not create a usable product workflow.
2. Reimplementing CLI branches in route handlers. It duplicates validation and creates
   behavioral drift.
3. Removing CLI before parity. It would break scheduling and recovery before their Web
   replacements are rehearsed.

## Shared components

### Parity registry

A tracked registry enumerates every parser command/subcommand and records its owner,
Web route, capability class, authority, scheduler status, and retirement disposition.
Tests compare the registry with the CLI parser and the FastAPI route table. An
unmapped command or a Web route without a capability declaration fails the Gate.

### Web mutation gateway

Extend the F-026 gateway rather than creating per-feature token systems. All writes
use fixed local identity, session-bound CSRF, Host/Origin enforcement, a short-lived
signed preview token, one-use nonce, operation binding, target version, input digest,
redacted audit, and atomic failure semantics.

Markdown mutations use a repository transaction with before/after hashes and staged
file writes. Candidate promotion coordinates the Markdown Source/asset transaction
with the Candidate operational transaction and records a recoverable mutation result.
No commit endpoint accepts editable actor, target, decision, or normalized content.

### Job control plane

Long-running operations use a persistent local job request and status model owned by
the application service, not an in-process background task. The website can preview,
confirm, enqueue, inspect, retry eligible failures, and cancel work that has not begun.
A dedicated internal runner consumes typed requests by calling services directly.
OS scheduling may start that runner, but users configure schedules, pause/resume, run
now, and inspect history in the website.

### Recovery boundary

Backup and restore remain local-first. Restore is always prepared into an absent or
empty disposable destination, verified there, and requires a second explicit Web
confirmation before any authoritative activation. Secrets are referenced by ignored
server-side configuration and never submitted back to the browser or stored in audit.

## F-027: Research workflow parity

Deliver in bounded slices:

1. Candidate promote/restore and batch lifecycle actions.
2. Source registration, fetch/process/date confirmation, asset verification, and
   structured Event/Report creation.
3. Project, Action, Review, Impact, Analysis, Forecast, Resolution, Valuation,
   Recommendation, Entity, Ontology assertion, and Thesis proposal workflows.

Approval screens are available only to the fixed human browser identity. Automated
jobs may create pending drafts and proposals but receive no route token or service
capability for approval. Thesis updates are human-submitted reviewed changes with
explicit Evidence IDs; no model or scheduler path may change confidence.

## F-028: Operations and recovery parity

The website supplies Channel enable/disable, due discovery, run-now controls, schedule
configuration/status, Job history, Daily Brief, validation, index check/rebuild,
metrics, Pilot status, scale assessment, export, benchmark, backup, remote verification,
disposable restore, doctor, health, and release evaluation.

Fast read operations may execute within the request. Network, benchmark, repository
write, backup, restore, and scheduler operations use the persistent job control plane.
The UI shows exact scope, expected writes, secret/config presence, timestamps, logs
with redaction, retry eligibility, and final artifacts.

## F-029: CLI retirement

Retirement is allowed only when:

- the parity registry has no user-facing CLI-only row;
- scheduler wrappers call the internal runner/service API, not CLI output;
- a clean-browser end-to-end suite covers all primary workflows;
- a disposable Web-initiated recovery rehearsal passes;
- user docs contain no terminal requirement;
- package entry points expose the Web server and explicitly named internal runner only;
- the full repository quality, security, validation, index, performance, recovery, and
  release provenance Gates pass.

The legacy `research-os` product CLI and `09_Automation/research_os.py` compatibility
entry are then removed. Internal automation is capability-limited and is not described
or installed as a user interface.

## User experience

Keep the current quiet, dense operational design. Add domain navigation, list/detail
pages, forms beside the object they affect, dedicated preview/confirmation pages,
stable result pages, and a persistent Jobs area for asynchronous work. Use familiar
icons for actions, compact status badges, searchable selectors for object IDs, and
explicit empty/error/conflict states. Do not expose CLI command names as product copy.

## Error handling and audit

- Validation errors return the same field-level meaning as the service and make no
  write.
- Conflict, replay, expired token, identity mismatch, and stale target are distinct
  states with redacted audit events.
- Repository transactions fail atomically and retain recovery artifacts when needed.
- Network/job failures are visible and retryable only when idempotency is proven.
- Restore, purge, supersede, close, and approval operations require an additional
  danger confirmation and exact target version.

## Verification

Each slice uses service contract tests, HTTP security tests, transaction failure tests,
and a disposable end-to-end smoke. Each package closes with the complete repository
Gate and a dated provenance record. F-029 additionally requires browser automation at
desktop and mobile widths, a Web-initiated disposable recovery rehearsal, a parity
registry audit, and proof that no user CLI entry remains.

Release readiness stays independent. This migration cannot synthesize Pilot days,
Forecast outcomes, cadence reviews, Known Limitations acknowledgement, or human release
approval.
