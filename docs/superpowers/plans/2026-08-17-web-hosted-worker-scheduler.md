# Web-Hosted Worker Scheduler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the macOS/Markdown scheduler with a website-hosted worker whose schedules, execution state, audit, health, and backup lifecycle are managed through the local Web product.

**Architecture:** `research-os ui` supervises one child worker process. Web and worker coordinate through a WAL-mode `operations.db`; the worker uses APScheduler trigger primitives for timezone-aware next-fire calculations, claims SQLite leases, and invokes existing Job services directly. Starting the Web service starts scheduling, and stopping it terminates the worker and pauses all scheduled work.

**Tech Stack:** Python 3.12+, FastAPI lifespan, SQLite 3, APScheduler 3.x trigger primitives, Pydantic 2, pytest/unittest, existing MutationGateway and durable-backup adapters.

---

## Frozen Delivery Contract

Top-level delivery packages remain fixed at three:

1. `control-plane`: dependency, schema, repository, typed schedule policy, migration, and database mutation audit.
2. `worker-runtime`: Job execution split, worker loop, lease/retry/missed-run behavior, Web-owned supervisor, backup, and health.
3. `web-operations`: schedule forms and actions, Job/health/backup views, cutover, documentation, and final integration evidence.

Acceptance checklist:

- [ ] Starting `python -m research_os.ui` starts exactly one worker and reports a fresh heartbeat.
- [ ] Stopping the Web service leaves no worker child and no scheduled work continues.
- [ ] Schedule create/edit/pause/resume/run-now is available through typed Web forms with preview, one-use confirmation, version checking, and audit.
- [ ] Runtime schedule fields are imported from Channel Markdown once and never read from Markdown by the worker after cutover.
- [ ] Existing Job Markdown is preserved and imported; new runs are authoritative in `operations.db` and create no `JOB-*.md` files.
- [ ] `catch_up_once` creates at most one missed run per schedule; `skip_missed` advances without execution.
- [ ] Leases prevent overlap and stale leases recover after timeout.
- [ ] Candidate DB, `operations.db`, and Source assets are covered by durable backup, verification, and disposable restore.
- [ ] The bundled LaunchAgent and `run_daily.sh` have no production entry or documentation after cutover.
- [ ] Worker and Web paths cannot approve research objects or modify Thesis conclusion/confidence.

Explicit non-scope:

- Distributed queues, remote workers, multi-user operation, native desktop packaging, OS login startup, cron syntax, arbitrary shell jobs, automatic research approval, and changes to research rules or taxonomy.

Resource and verification budget:

- One implementation owner per file/behavior at a time.
- Focused tests after every task and atomic commits after each green task.
- No repeated full-suite runs between tasks.
- One complete repository gate after the final integration candidate; rerun only if a later fix invalidates that evidence.
- Existing unrelated failures are reported, not hidden or used to redefine completion.

## File Responsibility Map

Create:

- `src/research_os/services/operations_db.py`: operations database path, schema migrations, typed CRUD, leases, runs, worker state, and service events.
- `src/research_os/services/schedule_control.py`: APScheduler-backed interval/next-fire calculation and missed-run policy.
- `src/research_os/services/schedule_migration.py`: idempotent import of Channel runtime fields and historical Job Markdown.
- `src/research_os/services/scheduler_worker.py`: polling loop, heartbeat, lease claim, retry, Job invocation, and shutdown.
- `src/research_os/services/worker_supervisor.py`: child spawn, readiness, bounded restart, graceful stop, and orphan prevention contract.
- `src/research_os/services/web_schedule_mutations.py`: typed database mutation previews/plans for schedule CRUD and actions.
- `src/research_os/ui/scheduler_views.py`: schedule, run, worker, and backup HTML view helpers.
- `src/research_os/runtime/worker.py`: internal `python -m` worker entry point.
- `09_Automation/tests/test_operations_db.py`: schema/CRUD/lease/audit tests.
- `09_Automation/tests/test_schedule_control.py`: trigger and missed-run policy tests.
- `09_Automation/tests/test_schedule_migration.py`: import/idempotency/preservation tests.
- `09_Automation/tests/test_scheduler_worker.py`: worker execution, retry, heartbeat, and shutdown tests.
- `09_Automation/tests/test_worker_supervisor.py`: subprocess lifecycle tests.
- `09_Automation/tests/test_web_scheduler.py`: Web list/form/preview/commit/run-now tests.
- `09_Automation/tests/test_web_worker_lifecycle.py`: real Web lifespan and child-process E2E tests.

Modify:

- `pyproject.toml`: add APScheduler dependency.
- `requirements/ci.txt`: pin APScheduler and its transitive timezone dependency.
- `src/research_os/services/jobs.py`: separate execution from persistence and stop writing Job Markdown.
- `src/research_os/services/discovery.py`: remove Markdown schedule/due computation from the production scheduler path.
- `src/research_os/services/channels.py`: read operational enabled/schedule state from `operations.db` for Web rows.
- `src/research_os/services/web_operations_mutations.py`: route Job requests to the operations queue and retire Markdown operational requests.
- `src/research_os/services/operations_health.py`: report operations DB, worker, schedule, and database-backed run health.
- `src/research_os/services/durable_backup.py`: include and restore a verified `operations.db` snapshot.
- `src/research_os/services/product_capabilities.py`: declare schedule management and worker health routes.
- `src/research_os/ui/app.py`: install lifespan supervisor and Web scheduler routes; use view helpers.
- `src/research_os/ui/__main__.py`: keep one website launch entry while enabling supervision.
- `09_Automation/tests/test_m5_dashboard_jobs.py`: replace Markdown Job assumptions with operations DB assertions.
- `09_Automation/tests/test_web_operations_parity.py`: cover queued Job and schedule mutation behavior.
- `09_Automation/tests/test_product_capabilities.py`: cover the new route contract.
- `09_Automation/tests/test_durable_backup.py`: verify operations DB archive and restore integrity.
- `09_Automation/tests/test_ci_workflows.py`: ensure no hosted or OS scheduler is introduced.
- `README.md`, `09_Automation/README.md`, `09_Automation/launchd/RUNBOOK.md`, and `00_System/Recovery_Runbook.md`: document Web-hosted lifecycle, cutover, backup, and rollback.

Preserve without rewriting:

- Existing `05_Research/Operations/Jobs/JOB-*.md` records.
- Existing `09_Automation/launchd/logs/*` evidence.
- Existing Source assets and research Markdown authority files.

## Package 1: Control Plane

### Task 1: Operations database schema and repository

**Files:**
- Create: `src/research_os/services/operations_db.py`
- Create: `09_Automation/tests/test_operations_db.py`

- [ ] **Step 1: Write failing schema and CRUD tests**

```python
def test_schema_crud_and_optimistic_version(tmp_path: Path) -> None:
    db = operations_db_path(tmp_path)
    apply_migrations(db)
    created = create_schedule(
        db,
        ScheduleSpec(
            schedule_id="SCH-channel-sec-micron",
            name="Micron SEC",
            job_name="discover",
            target="CHN-sec-micron",
            project_id=None,
            interval_seconds=21600,
            timezone="Asia/Shanghai",
            enabled=True,
            retry_limit=2,
            retry_backoff_seconds=30,
            timeout_seconds=1800,
            overlap_policy="skip",
            missed_run_policy="catch_up_once",
        ),
        actor="max",
        now="2026-08-17T01:00:00Z",
    )
    assert created.version == 1
    assert get_schedule(db, created.schedule_id) == created
    updated = update_schedule(
        db,
        created.schedule_id,
        expected_version=1,
        changes={"enabled": False},
        actor="max",
        now="2026-08-17T01:01:00Z",
    )
    assert updated.version == 2
    with pytest.raises(ScheduleConflictError):
        update_schedule(
            db,
            created.schedule_id,
            expected_version=1,
            changes={"enabled": True},
            actor="max",
            now="2026-08-17T01:02:00Z",
        )
```

Also add tests that WAL mode and foreign keys are enabled, invalid enum/range values fail before SQL, one active lease per schedule is enforced, a stale lease can be reclaimed, and every mutation writes a redacted `service_events` row.

- [ ] **Step 2: Run the tests and verify the missing module failure**

Run: `PYTHONPATH=src python -m pytest 09_Automation/tests/test_operations_db.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: research_os.services.operations_db`.

- [ ] **Step 3: Implement the typed repository and schema migration**

Use immutable records and explicit enums:

```python
OverlapPolicy = Literal["skip"]
MissedRunPolicy = Literal["catch_up_once", "skip_missed"]
RunStatus = Literal["queued", "claimed", "running", "success", "failed", "cancelled", "skipped"]

@dataclass(frozen=True)
class ScheduleSpec:
    schedule_id: str
    name: str
    job_name: str
    target: str | None
    project_id: str | None
    interval_seconds: int
    timezone: str
    enabled: bool
    retry_limit: int
    retry_backoff_seconds: int
    timeout_seconds: int
    overlap_policy: OverlapPolicy
    missed_run_policy: MissedRunPolicy

@dataclass(frozen=True)
class ScheduleRecord(ScheduleSpec):
    next_run_at: str | None
    version: int
    created_at: str
    updated_at: str
```

Create schema version 1 with `schema_meta`, `schedules`, `schedule_runs`, `worker_state`, and `service_events`. Put `lease_owner` and `lease_expires_at` on `schedule_runs`; enforce one active `claimed/running` run per schedule with a partial unique index. Open every connection with `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`, and `PRAGMA busy_timeout=5000`.

- [ ] **Step 4: Run focused tests**

Run: `PYTHONPATH=src python -m pytest 09_Automation/tests/test_operations_db.py -q`

Expected: all tests PASS.

- [ ] **Step 5: Commit the control-plane repository**

```bash
git add src/research_os/services/operations_db.py 09_Automation/tests/test_operations_db.py
git commit -m "feat(operations): add scheduler control database"
```

### Task 2: Timezone-aware schedule policy

**Files:**
- Create: `src/research_os/services/schedule_control.py`
- Create: `09_Automation/tests/test_schedule_control.py`
- Modify: `pyproject.toml`
- Modify: `requirements/ci.txt`

- [ ] **Step 1: Write failing trigger and missed-run tests**

```python
def test_next_fire_uses_timezone_and_interval() -> None:
    policy = SchedulePolicy(interval_seconds=21600, timezone="Asia/Shanghai")
    assert next_fire_time(policy, "2026-08-17T00:00:00Z") == "2026-08-17T06:00:00Z"

def test_catch_up_once_and_skip_missed() -> None:
    assert due_decision(
        next_run_at="2026-08-16T00:00:00Z",
        now="2026-08-17T00:00:00Z",
        policy="catch_up_once",
    ).action == "run_once"
    assert due_decision(
        next_run_at="2026-08-16T00:00:00Z",
        now="2026-08-17T00:00:00Z",
        policy="skip_missed",
    ).action == "advance_only"
```

Add DST-boundary coverage with `America/New_York`, invalid IANA timezone rejection, minimum/maximum interval checks, and proof that one decision never returns multiple catch-up executions.

- [ ] **Step 2: Run and verify failure**

Run: `PYTHONPATH=src python -m pytest 09_Automation/tests/test_schedule_control.py -q`

Expected: FAIL because `schedule_control` is missing.

- [ ] **Step 3: Add and pin APScheduler**

Add `"apscheduler>=3.11,<4"` to project dependencies. Pin the resolved APScheduler 3.x and `tzlocal` versions in `requirements/ci.txt`; install through `pip install -e ".[ui,dev]" --constraint requirements/ci.txt` and record the exact resolver result rather than guessing a transitive version.

- [ ] **Step 4: Implement policy using APScheduler trigger primitives**

Use `apscheduler.triggers.interval.IntervalTrigger` and `zoneinfo.ZoneInfo`. Convert all persisted timestamps to UTC ISO-8601 strings. Keep legacy natural-language parsing only in the migration adapter; the new runtime stores `interval_seconds` and never parses free-form schedule text.

- [ ] **Step 5: Run focused tests and dependency smoke**

Run:

```bash
PYTHONPATH=src python -m pytest 09_Automation/tests/test_schedule_control.py -q
python -c "import apscheduler; print(apscheduler.__version__)"
```

Expected: tests PASS and an allowed 3.x version prints.

- [ ] **Step 6: Commit the schedule policy**

```bash
git add pyproject.toml requirements/ci.txt src/research_os/services/schedule_control.py 09_Automation/tests/test_schedule_control.py
git commit -m "feat(scheduler): add timezone-aware schedule policy"
```

### Task 3: Idempotent Markdown-to-database migration

**Files:**
- Create: `src/research_os/services/schedule_migration.py`
- Create: `09_Automation/tests/test_schedule_migration.py`
- Modify: `src/research_os/services/schedule.py`

- [ ] **Step 1: Write failing migration tests**

Create a disposable repository with two Channel Markdown files and three historical Job files. Assert:

```python
first = migrate_operational_history(root, actor="system:migration", now=NOW)
assert first.channels_imported == 2
assert first.jobs_imported == 3
assert first.files_changed == ()
second = migrate_operational_history(root, actor="system:migration", now=NOW)
assert second.channels_imported == 0
assert second.jobs_imported == 0
assert sha256_tree(root / "02_Knowledge/Channels") == before_channels
assert sha256_tree(root / "05_Research/Operations/Jobs") == before_jobs
```

Also assert `daily 1x`, `daily 2x`, and `every 6 hours` import to 86400, 43200, and 21600 seconds; unparseable values produce a disabled schedule plus a migration warning; restricted/unreviewed Channels never import enabled.

- [ ] **Step 2: Run and verify failure**

Run: `PYTHONPATH=src python -m pytest 09_Automation/tests/test_schedule_migration.py -q`

Expected: FAIL because the migration service is missing.

- [ ] **Step 3: Implement migration and stable IDs**

Derive Channel schedule IDs as `SCH-channel-<channel-id-without-CHN-prefix>`. Historical Job rows retain their existing `JOB-*` IDs and use a migration-only `dedupe_key`. Store the complete original relative path in the imported run metadata, but do not copy Job bodies into the database.

Expose:

```python
@dataclass(frozen=True)
class MigrationResult:
    channels_imported: int
    jobs_imported: int
    warnings: tuple[str, ...]
    files_changed: tuple[Path, ...] = ()

def migrate_operational_history(
    root: Path, *, actor: str, now: str
) -> MigrationResult:
    db = operations_db_path(root)
    apply_migrations(db)
    channels, warnings = import_channel_schedules(root, db, actor=actor, now=now)
    jobs = import_historical_jobs(root, db, actor=actor, now=now)
    return MigrationResult(
        channels_imported=channels,
        jobs_imported=jobs,
        warnings=tuple(warnings),
    )
```

Keep `interval_from_schedule()` as a migration compatibility function and mark it non-runtime in its module documentation.

- [ ] **Step 4: Run migration and legacy parser tests**

Run:

```bash
PYTHONPATH=src python -m pytest 09_Automation/tests/test_schedule_migration.py 09_Automation/tests/test_schedule.py -q
```

Expected: all tests PASS.

- [ ] **Step 5: Commit the migration adapter**

```bash
git add src/research_os/services/schedule_migration.py src/research_os/services/schedule.py 09_Automation/tests/test_schedule_migration.py
git commit -m "feat(scheduler): import legacy schedule and job history"
```

## Package 2: Worker Runtime

### Task 4: Separate Job execution from operational persistence

**Files:**
- Modify: `src/research_os/services/jobs.py`
- Modify: `src/research_os/services/web_operations_mutations.py`
- Modify: `src/research_os/services/discovery.py`
- Modify: `src/research_os/services/channels.py`
- Modify: `09_Automation/tests/test_m5_dashboard_jobs.py`
- Modify: `09_Automation/tests/test_web_operations_parity.py`
- Modify: `09_Automation/tests/test_discovery.py`

- [ ] **Step 1: Write failing database-backed Job tests**

Update `SchedulerJobTests` so `run_job()` returns a database run ID, persists through `operations_db`, and does not create a Markdown Job file:

```python
before = tuple((root / "05_Research/Operations/Jobs").glob("JOB-*.md"))
result = run_job(root, "validate", started_at=STARTED)
assert result.status == "success"
assert get_run(operations_db_path(root), result.job_id).status == "success"
assert tuple((root / "05_Research/Operations/Jobs").glob("JOB-*.md")) == before
```

Add a test that Web Job preview/commit enqueues a typed manual run rather than writing `05_Research/Operations/Requests/REQ-*.md`. Add a test that production `due_channels()` reads `operations.db` and ignores changed Markdown runtime fields after migration.

- [ ] **Step 2: Run focused tests and verify the old Markdown assertions fail**

Run:

```bash
PYTHONPATH=src python -m pytest \
  09_Automation/tests/test_m5_dashboard_jobs.py::SchedulerJobTests \
  09_Automation/tests/test_web_operations_parity.py \
  09_Automation/tests/test_discovery.py -q
```

Expected: FAIL because Job and due discovery still use Markdown persistence/configuration.

- [ ] **Step 3: Extract a pure execution boundary**

Define:

```python
@dataclass(frozen=True)
class JobExecutionResult:
    status: Literal["success", "failed"]
    message: str

def execute_job(
    root: Path,
    job_name: str,
    *,
    project_id: str | None = None,
    target: str | None = None,
    as_of: str,
    durable_config: Path | None = None,
) -> JobExecutionResult:
    try:
        message = _execute_job(
            root,
            job_name,
            project_id=project_id,
            target=target,
            as_of=as_of,
            durable_config=durable_config,
        )
        return JobExecutionResult("success", redact_secrets(message))
    except Exception as exc:
        message = redact_secrets(f"{type(exc).__name__}: {exc}")
        return JobExecutionResult("failed", message)
```

`execute_job()` validates, invokes the existing service branch, catches and redacts errors, and performs no Job Markdown write. `run_job()` becomes a compatibility wrapper that creates one manual `schedule_runs` record, calls `execute_job()`, and finalizes the database row.

Replace `_request_plan()` for operational Jobs with an operations DB request plan; repository mutation plans remain unchanged for research Markdown. Update Channel rows and due discovery to join governance metadata from Markdown with operational values from `operations.db`.

- [ ] **Step 4: Run focused tests**

Run the Step 2 command again.

Expected: all selected tests PASS; no new `JOB-*.md` file appears in disposable fixtures.

- [ ] **Step 5: Commit the execution split**

```bash
git add src/research_os/services/jobs.py src/research_os/services/web_operations_mutations.py src/research_os/services/discovery.py src/research_os/services/channels.py 09_Automation/tests/test_m5_dashboard_jobs.py 09_Automation/tests/test_web_operations_parity.py 09_Automation/tests/test_discovery.py
git commit -m "refactor(jobs): persist operational runs in sqlite"
```

### Task 5: Worker loop, leases, retry, and heartbeat

**Files:**
- Create: `src/research_os/services/scheduler_worker.py`
- Create: `src/research_os/runtime/worker.py`
- Create: `09_Automation/tests/test_scheduler_worker.py`

- [ ] **Step 1: Write failing deterministic worker tests**

Use an injected clock, sleeper, and executor. Cover:

```python
worker.tick(now="2026-08-17T06:00:00Z")
run = latest_run(db, schedule_id)
assert run.request_kind == "scheduled"
assert run.status == "success"
assert get_schedule(db, schedule_id).next_run_at == "2026-08-17T12:00:00Z"
```

Add tests for `catch_up_once`, `skip_missed`, live-lease overlap skip, stale-lease reclaim, retry sequence `30s -> 60s` bounded by `retry_limit`, heartbeat update while idle, graceful shutdown before claiming new work, parent PID loss exit, and secret redaction in failed rows.

- [ ] **Step 2: Run and verify failure**

Run: `PYTHONPATH=src python -m pytest 09_Automation/tests/test_scheduler_worker.py -q`

Expected: FAIL because `scheduler_worker` and runtime entry point are missing.

- [ ] **Step 3: Implement one-tick and run-forever APIs**

```python
class SchedulerWorker:
    def __init__(
        self,
        root: Path,
        *,
        worker_id: str,
        parent_pid: int,
        execute: JobExecutor = execute_job,
        clock: Clock = utc_now,
        sleep: Sleeper = time.sleep,
    ) -> None:
        self.root = root.resolve()
        self.worker_id = worker_id
        self.parent_pid = parent_pid
        self.execute = execute
        self.clock = clock
        self.sleep = sleep

    def tick(self, *, now: str | None = None) -> int:
        observed = now or self.clock()
        refresh_worker_heartbeat(self.root, self.worker_id, observed)
        claimed = claim_due_runs(self.root, self.worker_id, observed)
        for run in claimed:
            result = self.execute(
                self.root,
                run.job_name,
                project_id=run.project_id,
                target=run.target,
                as_of=run.as_of,
            )
            finalize_run(self.root, run.run_id, result, finished_at=self.clock())
        return len(claimed)

    def run_forever(self, stop: Event) -> None:
        while not stop.is_set() and parent_is_alive(self.parent_pid):
            self.tick()
            stop.wait(5.0)
        record_worker_stop(self.root, self.worker_id, stopped_at=self.clock())
```

Poll at a bounded interval (default 5 seconds), update heartbeat before and after each tick, and claim due/manual rows in one `BEGIN IMMEDIATE` transaction. Finalize every claimed row even when execution raises. The runtime module parses only `--root` and `--parent-pid`; it installs SIGTERM/SIGINT handlers and calls `run_forever()`.

- [ ] **Step 4: Run focused tests and entry-point smoke**

Run:

```bash
PYTHONPATH=src python -m pytest 09_Automation/tests/test_scheduler_worker.py -q
PYTHONPATH=src python -m research_os.runtime.worker --help
```

Expected: tests PASS and help lists only `--root` and `--parent-pid`.

- [ ] **Step 5: Commit the worker**

```bash
git add src/research_os/services/scheduler_worker.py src/research_os/runtime/worker.py 09_Automation/tests/test_scheduler_worker.py
git commit -m "feat(worker): execute scheduled jobs with leases"
```

### Task 6: Web-owned worker supervisor and lifespan

**Files:**
- Create: `src/research_os/services/worker_supervisor.py`
- Create: `09_Automation/tests/test_worker_supervisor.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/ui/__main__.py`

- [ ] **Step 1: Write failing supervisor lifecycle tests**

Use a small fixture child module that writes heartbeat and responds to SIGTERM. Assert one child per supervisor, readiness timeout cleanup, graceful stop, forced kill after grace timeout, no restart during Web shutdown, and at most three crash restarts in five minutes.

Add a FastAPI lifespan test:

```python
with TestClient(create_app(root, worker_factory=factory)) as client:
    assert factory.started == 1
    assert client.get("/health?refresh=1").status_code == 200
assert factory.stopped == 1
assert factory.live_children == 0
```

- [ ] **Step 2: Run and verify failure**

Run: `PYTHONPATH=src python -m pytest 09_Automation/tests/test_worker_supervisor.py -q`

Expected: FAIL because the supervisor and injectable lifespan do not exist.

- [ ] **Step 3: Implement subprocess supervision**

Spawn with:

```python
[
    sys.executable,
    "-m",
    "research_os.runtime.worker",
    "--root",
    str(root),
    "--parent-pid",
    str(os.getpid()),
]
```

Do not use `shell=True`. Redirect stdout/stderr to rotating files under `09_Automation/operational/logs/worker.*.log`, pass a minimal inherited environment, wait for a database heartbeat matching the child PID, and expose `snapshot()` without secret/environment values.

Convert `create_app(root)` to accept an optional supervisor factory and install an `asynccontextmanager` lifespan. Startup applies operations migrations/import, starts the child, and publishes readiness. Shutdown closes new requests, stops the child, and shuts down existing executors.

- [ ] **Step 4: Run supervisor and existing Web smoke tests**

Run:

```bash
PYTHONPATH=src python -m pytest \
  09_Automation/tests/test_worker_supervisor.py \
  09_Automation/tests/test_ci_workflows.py::CiDashboardSmokeTests -q
```

Expected: all selected tests PASS with no leftover child process.

- [ ] **Step 5: Commit supervision**

```bash
git add src/research_os/services/worker_supervisor.py src/research_os/ui/app.py src/research_os/ui/__main__.py 09_Automation/tests/test_worker_supervisor.py
git commit -m "feat(web): supervise scheduler worker with app lifespan"
```

### Task 7: Operations backup and health integration

**Files:**
- Modify: `src/research_os/services/durable_backup.py`
- Modify: `src/research_os/services/operations_health.py`
- Modify: `09_Automation/tests/test_durable_backup.py`
- Modify: `09_Automation/tests/test_m5_dashboard_jobs.py`

- [ ] **Step 1: Write failing backup and health tests**

Assert the operational encrypted set contains both SQLite snapshots and manifests:

```python
with tarfile.open(candidate_archive) as archive:
    names = set(archive.getnames())
assert "candidate/candidates.db" in names
assert "operations/operations.db" in names
assert "operations/operations.db.manifest.json" in names
```

Restore into a disposable root and assert both databases pass their integrity/schema checks. Add health assertions for operations DB status, worker heartbeat age, worker `ready/stale/failed/stopped`, active schedule count, current run, and existing durable staleness alerts.

- [ ] **Step 2: Run and verify failure**

Run:

```bash
PYTHONPATH=src python -m pytest \
  09_Automation/tests/test_durable_backup.py \
  09_Automation/tests/test_m5_dashboard_jobs.py::OperationsHealthSnapshotTests -q
```

Expected: FAIL because backups and health do not include operations DB/worker state.

- [ ] **Step 3: Snapshot and verify operations DB**

Use SQLite's backup API, not file copying, for both databases. Extend the existing operational archive manifest with an `operations` entry containing `sha256`, `size_bytes`, `schema_version`, and `created_at`. Reject missing/corrupt operations databases during create and restore. Keep the outer durable receipt at two encrypted sets (`candidate` and `source_assets`) for remote compatibility.

Extend `health_snapshot()` with:

```python
"operations_db": operations_db_health(operations_db_path(root)),
"worker": worker_health(operations_db_path(root), now=now_dt),
"schedules": schedule_health(operations_db_path(root), now=now_dt),
```

Treat a worker as `stopped` without alert when the Web lifespan is not active; treat stale heartbeat while the supervisor reports a live child as an operational failure.

- [ ] **Step 4: Run focused backup/health tests**

Run the Step 2 command again.

Expected: all selected tests PASS.

- [ ] **Step 5: Commit backup and health integration**

```bash
git add src/research_os/services/durable_backup.py src/research_os/services/operations_health.py 09_Automation/tests/test_durable_backup.py 09_Automation/tests/test_m5_dashboard_jobs.py
git commit -m "feat(operations): back up and monitor scheduler state"
```

## Package 3: Web Operations

### Task 8: Typed schedule mutations and Web pages

**Files:**
- Create: `src/research_os/services/web_schedule_mutations.py`
- Create: `src/research_os/ui/scheduler_views.py`
- Create: `09_Automation/tests/test_web_scheduler.py`
- Modify: `src/research_os/services/product_capabilities.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `09_Automation/tests/test_product_capabilities.py`

- [ ] **Step 1: Write failing service and HTTP tests**

Cover list/new/edit/pause/resume/run-now with real HTML controls. The create form must expose `job_name`, target selector, numeric interval plus unit, timezone selector, retry limit/backoff, timeout, overlap policy, and missed-run policy. Assert there is no raw JSON textarea.

For each mutation assert:

```python
preview = client.post("/operations/schedules/new/preview", data=form, headers=origin)
assert preview.status_code == 200
committed = client.post(
    "/operations/schedules/new/commit",
    data=confirmation(preview),
    headers=origin,
    follow_redirects=False,
)
assert committed.status_code == 303
assert get_schedule(db, schedule_id).version == 1
assert replay_same_confirmation(client, committed_request).status_code == 409
```

Add restricted Channel enable rejection, stale-version conflict, CSRF/Origin rejection, audit redaction, pause preserving history, run-now queued rather than inline execution, and visible links from `/operations` and `/pipeline/channels`.

- [ ] **Step 2: Run and verify missing routes**

Run:

```bash
PYTHONPATH=src python -m pytest \
  09_Automation/tests/test_web_scheduler.py \
  09_Automation/tests/test_product_capabilities.py -q
```

Expected: FAIL with missing route/module assertions.

- [ ] **Step 3: Implement database mutation plans**

Define strict Pydantic commands:

```python
class ScheduleInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    job_name: Literal[
        "validate", "indexes", "metrics", "source-process", "refresh",
        "discover", "expire", "purge", "enrich", "daily-brief",
        "forecast-alerts", "backup-candidate", "backup-durable"
    ]
    target: str | None = Field(default=None, max_length=120)
    project_id: str | None = Field(default=None, max_length=80)
    interval_value: int = Field(ge=1, le=1000)
    interval_unit: Literal["minutes", "hours", "days", "weeks"]
    timezone: str
    retry_limit: int = Field(ge=0, le=5)
    retry_backoff_seconds: int = Field(ge=1, le=3600)
    timeout_seconds: int = Field(ge=30, le=86400)
    missed_run_policy: Literal["catch_up_once", "skip_missed"]
```

Use MutationGateway for signed preview/one-use confirmation. Bind target version to the schedule row version/digest and commit all database changes plus service audit in one SQLite transaction. Do not route schedule mutations through repository Markdown plans.

- [ ] **Step 4: Implement focused views and route registration**

Keep rendering in `scheduler_views.py`; keep request-bound MutationGateway integration in `app.py`. Add visible icon/text actions beside each schedule and Channel. Use selects, toggles, and numeric controls rather than JSON. Ensure controls have stable dimensions and mobile wrapping consistent with existing styles.

- [ ] **Step 5: Run focused tests**

Run the Step 2 command again.

Expected: all selected tests PASS.

- [ ] **Step 6: Commit the schedule UI**

```bash
git add src/research_os/services/web_schedule_mutations.py src/research_os/ui/scheduler_views.py src/research_os/services/product_capabilities.py src/research_os/ui/app.py 09_Automation/tests/test_web_scheduler.py 09_Automation/tests/test_product_capabilities.py
git commit -m "feat(web): manage scheduler from operations pages"
```

### Task 9: Worker, Job, and backup operational views

**Files:**
- Modify: `src/research_os/ui/scheduler_views.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/services/web_operations_mutations.py`
- Modify: `09_Automation/tests/test_web_operations_parity.py`
- Modify: `09_Automation/tests/test_web_scheduler.py`
- Modify: `09_Automation/tests/test_m6_security.py`

- [ ] **Step 1: Write failing click-path tests**

Assert a user can navigate without deep links:

```text
/operations -> Schedules -> Edit/Pause/Run now -> Preview -> Confirm -> Result
/operations -> Jobs -> Run detail
/health -> Worker failure/current run -> Jobs
/operations/backups -> Run candidate/durable backup -> Preview -> Confirm -> Result
```

Add tests that the generic Job form uses typed controls, durable backup resolves only the fixed ignored server-side config path, no browser field accepts a config path/token/recipient, worker stdout/stderr is redacted and bounded, and all unknown/replayed/stale operations produce distinct 4xx responses.

- [ ] **Step 2: Run and verify click-path failures**

Run:

```bash
PYTHONPATH=src python -m pytest \
  09_Automation/tests/test_web_operations_parity.py \
  09_Automation/tests/test_web_scheduler.py \
  09_Automation/tests/test_m6_security.py -q
```

Expected: FAIL on missing links/forms and durable backup configuration wiring.

- [ ] **Step 3: Complete views and queued execution**

Replace the raw JSON Job form with typed job/target/project/as-of controls. Convert manual Job commit to enqueue a `schedule_runs` row with `request_kind="manual"`; return a stable result page that refreshes from queued/running to a terminal state. Pass the server-owned durable config to `execute_job()` only inside the worker.

Render worker state, heartbeat age, current run, restart exhaustion, schedule counts, last failures, candidate backup, and durable backup on `/health`. Bound run history to 50 rows per page with explicit pagination.

- [ ] **Step 4: Run focused security and click-path tests**

Run the Step 2 command again.

Expected: all selected tests PASS.

- [ ] **Step 5: Commit operational views**

```bash
git add src/research_os/ui/scheduler_views.py src/research_os/ui/app.py src/research_os/services/web_operations_mutations.py 09_Automation/tests/test_web_operations_parity.py 09_Automation/tests/test_web_scheduler.py 09_Automation/tests/test_m6_security.py
git commit -m "feat(web): complete worker and job operations flows"
```

### Task 10: Cutover, lifecycle E2E, and final repository gate

**Files:**
- Create: `09_Automation/tests/test_web_worker_lifecycle.py`
- Modify: `09_Automation/tests/test_ci_workflows.py`
- Modify: `README.md`
- Modify: `09_Automation/README.md`
- Modify: `09_Automation/launchd/RUNBOOK.md`
- Modify: `00_System/Recovery_Runbook.md`
- Modify: `00_System/v0.3_F028_Operations_Web_Parity_Verification_2026-08-13.md`
- Preserve: `09_Automation/launchd/com.aioresearchos.discovery.plist`
- Preserve: `09_Automation/launchd/run_daily.sh`
- Preserve: `09_Automation/launchd/logs/*`

- [ ] **Step 1: Write the failing real lifecycle E2E**

Start a disposable server on a free loopback port with a deterministic 1-second validate schedule. Assert worker heartbeat, one completed run, graceful Web stop, unchanged run count while stopped, restart, and one `catch_up_once` run. Record child PIDs and assert none remain after both shutdowns.

Add a static test that production entry points and README contain no `launchctl`, plist installation, `run_daily.sh`, or manual Channel schedule editing. Permit those strings only in the legacy rollback runbook and historical verification records.

- [ ] **Step 2: Run and verify failure before cutover docs**

Run:

```bash
PYTHONPATH=src python -m pytest \
  09_Automation/tests/test_web_worker_lifecycle.py \
  09_Automation/tests/test_ci_workflows.py -q
```

Expected: FAIL until lifecycle and documentation cutover are complete.

- [ ] **Step 3: Complete cutover documentation and rollback boundary**

Update user documentation so `python -m research_os.ui` is the only launch instruction and `/operations/schedules` is the only schedule-management instruction. Rewrite `09_Automation/launchd/RUNBOOK.md` as a clearly marked legacy rollback artifact: it must say the LaunchAgent is unloaded, must never run concurrently with the Web worker, and may be restored only after stopping the Web service and restoring the pre-cutover snapshot.

Update Recovery Runbook backup membership and restore verification for `operations.db`. Amend the dated F-028 record instead of silently rewriting its historical claim: add a dated superseding note that route parity did not provide full scheduler management and cite the new verification evidence.

- [ ] **Step 4: Run lifecycle, focused scheduler, and migration gates**

Run:

```bash
PYTHONPATH=src python -m pytest \
  09_Automation/tests/test_operations_db.py \
  09_Automation/tests/test_schedule_control.py \
  09_Automation/tests/test_schedule_migration.py \
  09_Automation/tests/test_scheduler_worker.py \
  09_Automation/tests/test_worker_supervisor.py \
  09_Automation/tests/test_web_scheduler.py \
  09_Automation/tests/test_web_worker_lifecycle.py \
  09_Automation/tests/test_durable_backup.py \
  09_Automation/tests/test_web_operations_parity.py \
  09_Automation/tests/test_product_capabilities.py -q
```

Expected: all focused tests PASS and no child process remains.

- [ ] **Step 5: Run the single complete repository integration gate**

Run:

```bash
research-os validate --strict
research-os index --check
research-os index --check --project PRJ-001
research-os index --check --project PRJ-002
python -m pytest
ruff check .
ruff format --check .
mypy src/research_os
python -m compileall -q src 09_Automation
```

Expected: every command exits 0. If an existing unrelated failure remains, preserve its evidence and stop for an explicit scope decision; do not alter research data or weaken the gate.

- [ ] **Step 6: Perform manual Web acceptance on the integration candidate**

Start `python -m research_os.ui` on a free loopback port. Verify `/operations/schedules`, `/operations/jobs`, `/operations/backups`, and `/health` on desktop and mobile widths; create a disabled test schedule, edit it, run it manually, confirm the result, pause/resume it, then leave it disabled through audited Web actions. Stop the server and verify the worker PID exits.

- [ ] **Step 7: Commit cutover and verification evidence**

```bash
git add README.md 09_Automation/README.md 09_Automation/launchd/RUNBOOK.md 00_System/Recovery_Runbook.md 00_System/v0.3_F028_Operations_Web_Parity_Verification_2026-08-13.md 09_Automation/tests/test_web_worker_lifecycle.py 09_Automation/tests/test_ci_workflows.py
git commit -m "feat(scheduler): cut over to web-hosted worker"
```

## Implementation Notes

- Never run the legacy LaunchAgent and Web worker concurrently against the same repository.
- Never delete historical Job Markdown or launchd logs during implementation.
- Do not add a new product CLI. The worker module is an internal child-process entry point owned by the Web supervisor.
- Do not expose raw schedule JSON, shell commands, environment values, backup recipients, tokens, or private paths in the browser or audit.
- Preserve the existing dirty-worktree changes and adjust tests around them; do not revert unrelated research or UI work.
