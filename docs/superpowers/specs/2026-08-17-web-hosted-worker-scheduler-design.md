# Web-Hosted Worker Scheduler Design

Date: 2026-08-17
Status: draft - awaiting user review
Scope: Replace macOS launchd scheduling and Markdown runtime configuration with a
website-hosted worker and database control plane.

## Goal

Make the local website the sole runtime host and user-facing control plane for
scheduled research operations. Starting the website starts its worker; stopping the
website stops the worker. The scheduler must not depend on macOS `launchd`, `cron`,
login items, or manually edited Markdown runtime fields.

Research facts and governance records remain governed by the repository's existing
Markdown authority rules. This design moves operational scheduling and execution
state, not Source/Evidence/Thesis/Report authority.

## Frozen delivery contract

- Top-level delivery packages: 3 (`control-plane`, `worker-runtime`, `web-operations`).
- Implementation sequence: data/control plane, worker supervision and migration, Web
  configuration and recovery workflows.
- Resource budget: one feature branch, one implementation owner per behavior, focused
  tests per slice, and one complete repository gate against the final integration
  candidate.
- Non-scope: distributed queues, multi-user deployment, broker/trade execution,
  automatic research approval, automatic Thesis conclusion/confidence changes, and
  changing research rules or taxonomy.
- Existing Job Markdown and source assets are external operational state. Migration
  imports and preserves them; it does not delete or rewrite them merely to pass tests.

## Chosen architecture

The Web service owns a supervised worker child process:

```text
research-os ui
  -> Web UI/API
  -> worker supervisor
       -> research-os worker
            -> operations.db
            -> existing Job services
```

The Web service starts the worker during application startup and sends a graceful
shutdown during application shutdown. The worker has no independent production
service installation and no macOS-specific bootstrap. If the Web service is not
running, no scheduled work executes.

The worker is a separate process rather than a Web request task so a blocked network
operation or worker fault cannot block the UI event loop. The supervisor tracks the
child PID, startup time, heartbeat, exit status, and bounded restart attempts. A
worker that loses the parent heartbeat exits instead of becoming an orphan.

The worker calls existing application services directly. It does not shell out to
`research_os.py`, parse CLI output, or make Review/Thesis decisions.

Rejected alternatives:

1. Keep `launchd` as the scheduler. This preserves the current operational split and
   violates the website-only lifecycle requirement.
2. Run the scheduler inside the FastAPI process. This couples network work and UI
   availability and makes graceful isolation and restart behavior weaker.
3. Add a distributed queue. It is disproportionate for the current single-machine,
   local product boundary.

## Runtime control plane

Create `09_Automation/operational/operations.db` as the authoritative store for
runtime operations. It contains:

- `schedules`: stable schedule ID, name, target, interval/cadence, timezone, enabled
  state, retry policy, timeout, overlap policy, missed-run policy, version, and audit
  timestamps.
- `schedule_runs`: schedule ID, scheduled time, actual start/finish, status, attempt,
  worker/job ID, redacted message, and error classification.
- `worker_state`: singleton heartbeat, PID, process version, start time, current run,
  and last exit reason.
- `service_events`: start/stop, configuration changes, pause/resume, run-now,
  migration, and recovery events.

The existing Candidate SQLite store remains the Candidate Queue data store. Its
discovery lock and candidate records remain intact. New schedule configuration and
runtime history are not stored in the Candidate database so they have an explicit,
separately backed-up authority.

The existing Channel Markdown retains identity, source, license, and review metadata.
The following runtime fields are imported once and then owned by `operations.db`:

- `schedule`
- `timezone`
- `enabled`
- `max_candidates_per_run`
- runtime retry/timeout/overlap/missed-run policy

After migration, the worker never reads those runtime fields from Markdown. Website
mutations update the database through the existing preview, signed one-use token,
CSRF, fixed-human-identity, version-check, audit, and atomic-commit path.

## Worker lifecycle and scheduling semantics

1. Web startup opens or migrates `operations.db`, starts the worker, and waits for an
   initial heartbeat before reporting scheduler readiness.
2. The worker loads enabled schedules and computes due work using the stored timezone
   and interval policy.
3. Each run claims a database lease before invoking a Job service. A lease prevents
   overlapping runs for the same schedule and expires after the configured timeout.
4. Job services continue to produce the existing domain effects, but the worker
   records canonical run status in `schedule_runs`.
5. Web shutdown stops accepting new run requests, asks the worker to finish or cancel
   according to the job's cancellation policy, then terminates the child within a
   bounded grace period.
6. On the next Web startup, each schedule with missed time is evaluated once. The
   default policy is `catch_up_once`: one run for the missed window, then the next
   normal interval. A schedule may explicitly use `skip_missed`.
7. A worker crash is visible in `/health`; the supervisor may perform a bounded
   restart. Repeated crashes become a persistent failed service state requiring an
   explicit Web restart.

The worker does not replay every missed interval, does not run disabled schedules,
and does not auto-promote Sources or alter Thesis confidence.

## Website operations

Add the following user-facing surfaces:

- `/operations/schedules`: list schedules, status, next run, last run, and worker
  readiness.
- `/operations/schedules/new` and `/operations/schedules/{id}/edit`: typed controls
  for cadence, timezone, enabled state, retry, timeout, overlap, and missed-run
  policy. These forms must not require raw JSON.
- `/operations/schedules/{id}/pause`, `/resume`, and `/run`: preview, explicit
  confirmation, commit, and result pages.
- `/operations/jobs`: recent run instances, status, duration, error class, and
  associated schedule.
- `/health`: worker heartbeat, child-process state, current run, last failure, database
  integrity, source assets, and backup health.
- `/operations/backups`: candidate/durable backup status, run-now, remote verify, and
  recovery entry points. Secret values never render in the browser or audit log.

The Web service may enqueue a typed run request or wake the worker through a local
application-owned control channel. It must not shell out from a request handler or
allow arbitrary command strings. Existing mutation security and authority rules stay
in force.

## Backup and recovery

The durable backup set must include:

- Candidate SQLite data;
- `operations.db`;
- raw Source assets.

The backup adapter continues to encrypt and verify the two data groups, with the new
operations database added to the operational set. Backup credentials remain outside
Markdown and outside browser-visible fields; the service receives them through its
startup secret boundary or an equivalent local secret store.

The health page treats missing, failed, invalid, or older-than-24-hours durable
receipts as P1. Recovery remains preview-first, requires an empty/disposable target,
and requires explicit confirmation before activation.

## Migration and rollback

Migration is one-way only after a verified snapshot:

1. Snapshot Candidate DB, Source assets, and existing Job Markdown.
2. Create `operations.db` schema and import Channel runtime fields.
3. Import existing Job Markdown into read-only historical run rows.
4. Run the worker in dry-run/read-only mode and compare due schedules with the current
   `discover due` output.
5. Enable Web-hosted worker execution and verify one complete discovery/expire cycle.
6. Disable and unload the existing LaunchAgent; retain its plist and logs as recovery
   artifacts, but remove it from the production path.
7. Mark the migration event and make the website the only documented scheduler entry.

Rollback before cutover restores the database snapshot and reloads the preserved
LaunchAgent. Rollback after cutover requires stopping the Web worker first so both
schedulers can never run concurrently.

## Verification and acceptance

- Unit tests cover schedule parsing, timezone conversion, lease expiry, retry,
  catch-up-once, skip-missed, shutdown, parent-loss exit, and worker restart.
- Service tests prove Web startup creates exactly one worker and Web shutdown leaves no
  worker child running.
- Web tests cover schedule CRUD, pause/resume, run-now preview/commit/replay,
  heartbeat/error rendering, and secret redaction.
- Migration tests compare imported schedule state and historical Job counts without
  changing canonical Source/Evidence/Thesis/Report files.
- A disposable end-to-end test starts the Web service, observes worker heartbeat,
  executes a deterministic job, stops the service, verifies no new run occurs, then
  restarts and verifies the configured missed-run policy.
- No production code references the bundled LaunchAgent or `run_daily.sh` after
  cutover. No worker path reads runtime schedule fields from Channel Markdown.
- The final repository gate runs once on the integrated candidate; existing unrelated
  test failures remain separately reported rather than hidden by this migration.

## Open implementation constraints

- The Web startup command must expose a deterministic worker-supervision lifecycle for
  both development and packaged execution.
- The local control channel must be authenticated to the same fixed local Web identity
  and must reject arbitrary shell payloads.
- Durable backup schema and recovery runbook must be updated before the old scheduler
  is removed.
