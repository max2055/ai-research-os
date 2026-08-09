# WP-603 Operations and Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver F-010 unified Operations and F-011 unified System Health as request-time, secret-safe, read-only snapshots and dashboard pages.

**Architecture:** Compose existing scheduling, Job, Action, review, forecast, recommendation, validation, asset, Candidate DB, Channel, and host-status services behind two read models. Health checks expose status and metadata only; secret/config values and source content never enter returned dictionaries or HTML.

**Tech Stack:** Python 3.12, FastAPI, SQLite, `shutil.disk_usage`, `zoneinfo`/datetime, unittest/pytest.

---

## File Map

- Create `src/research_os/services/operations_health.py`: `operations_snapshot` and `health_snapshot` plus small pure status helpers.
- Modify `src/research_os/ui/app.py`: render Operations and Health exclusively from the new snapshots.
- Modify `09_Automation/tests/test_m5_dashboard_jobs.py`: snapshot composition, redaction, route, empty state, and GET-only tests.
- Modify `09_Automation/tests/test_candidate_db.py`: Candidate DB integrity/version and absent/corrupt behavior.
- Modify `00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md`: mark WP-603 complete after acceptance.

### Task 1: F-010 unified Operations snapshot

- [ ] **Step 1: Write a failing cross-service contract test**

Build fixtures for a due Channel schedule, successful/failed/missed Job, overdue/open Action, due Project review, due Forecast, and stale Recommendation, then assert:

```python
snapshot = operations_snapshot(root, as_of="2026-08-09")
for key in ("schedules", "jobs", "actions", "reviews", "forecasts", "recommendations"):
    self.assertIn(key, snapshot)
self.assertEqual("overdue", snapshot["actions"][0]["timing"])
self.assertEqual("due", snapshot["forecasts"][0]["timing"])
self.assertEqual("stale", snapshot["recommendations"][0]["freshness"])
self.assertIn("next_due", snapshot["schedules"][0])
```

Assert invalid `as_of`, Project filtering, deterministic ordering, and an absent Candidate DB produce explicit empty/unknown results rather than exceptions.

- [ ] **Step 2: Run and confirm RED**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_m5_dashboard_jobs.py -k operations_snapshot -q
```

Expected: import failure for the new module/function.

- [ ] **Step 3: Implement the read-only composer**

Create:

```python
def operations_snapshot(
    root: Path,
    *,
    as_of: str | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Return schedule, Job, Action, review, Forecast and Recommendation work queues."""
```

Compose `due_channels`, Job object state, `action_rows`, Project `next_review_date`, `forecast_status_report`, and `recommendation_freshness`. Annotate every row with a normalized status/timing and source object ID; perform no writes.

- [ ] **Step 4: Run and confirm GREEN**

Run the Step 2 command. Expected: Operations snapshot tests pass.

### Task 2: Render the complete Operations page

- [ ] **Step 1: Write failing route coverage tests**

Assert `/operations` includes six labelled sections: schedules, Jobs, Actions, reviews, due Forecasts, stale Recommendations. Assert stored messages are escaped and the route methods equal `{"GET"}`.

- [ ] **Step 2: Render from `operations_snapshot`**

Replace `_operations_page` direct scans with the composer. Keep the Pipeline link, add compact tables with stable empty states, and preserve Project filtering via the existing `project` query parameter.

- [ ] **Step 3: Verify Operations**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_m5_dashboard_jobs.py -k operations -q
```

Expected: snapshot and UI tests pass.

### Task 3: Candidate DB and host health primitives

- [ ] **Step 1: Write failing Candidate DB health tests**

In `test_candidate_db.py`, assert the new helper reports:

```python
self.assertEqual("ok", candidate_db_health(db_path)["integrity"])
self.assertIsInstance(candidate_db_health(db_path)["schema_version"], int)
self.assertEqual("missing", candidate_db_health(missing_path)["status"])
self.assertEqual("corrupt", candidate_db_health(corrupt_path)["integrity"])
```

The returned mapping must contain no Candidate title/body/URL.

- [ ] **Step 2: Confirm RED and implement bounded checks**

Add `candidate_db_health(path: Path) -> dict[str, Any]` to `candidate_db.py`. Open SQLite read-only, run `PRAGMA quick_check`, read the existing migration version, close in `finally`, and return only path-relative status, version, size, modified time, and integrity.

- [ ] **Step 3: Confirm GREEN**

Run `pytest 09_Automation/tests/test_candidate_db.py -q`. Expected: all Candidate DB tests pass.

### Task 4: F-011 unified Health snapshot

- [ ] **Step 1: Write a failing health contract test**

Create controlled fixtures/env state and assert:

```python
snapshot = health_snapshot(root, now="2026-08-09T12:00:00+08:00")
for key in ("validation", "indexes", "assets", "candidate_db", "channels", "failed_runs", "backup", "host", "config", "model_cost"):
    self.assertIn(key, snapshot)
self.assertIn(snapshot["host"]["timezone"], ("Asia/Shanghai", "UTC"))
self.assertIn("free_bytes", snapshot["host"]["disk"])
self.assertNotIn(secret_value, repr(snapshot))
```

Cover global/project index drift, missing/hash-mismatch assets, pending Channel license review, failed Analysis/Job runs, missing/stale backup manifest, low disk threshold, wrong timezone, secret presence/absence, LLM config presence, and model cost status.

- [ ] **Step 2: Confirm RED and implement the snapshot**

Add:

```python
def health_snapshot(
    root: Path,
    *,
    project_id: str | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Return repository, operational store, channel, backup and host health."""
```

Compose `validate_repository`, global/project `index_drift`, `verify_source_assets`, `candidate_db_health`, Channel license/review/schedule metadata, failed Job/Analysis Runs, backup manifest age, `shutil.disk_usage`, local timezone, allowlisted secret/config variable presence, and configured cost-budget status. Return severity `P0`–`P3` and messages without environment values, source text, prompts, or API responses.

- [ ] **Step 3: Confirm GREEN**

Run `pytest 09_Automation/tests/test_m5_dashboard_jobs.py -k health_snapshot -q`. Expected: all health categories and redaction tests pass.

### Task 5: Render Health and close WP-603

- [ ] **Step 1: Write failing Health page tests**

Assert `/health` renders all ten categories, severity badges, backup age, DB integrity/version, license state, disk/timezone, and only boolean/present/missing configuration status. Assert a sentinel secret never appears and route methods equal `{"GET"}`.

- [ ] **Step 2: Render from `health_snapshot`**

Replace `_health_page` direct scans with snapshot sections. Use `esc()` for every external string and display `unknown` when a check cannot be performed, never `healthy` by assumption.

- [ ] **Step 3: Run WP-603 acceptance**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_candidate_db.py \
  09_Automation/tests/test_channels.py \
  09_Automation/tests/test_schedule.py \
  09_Automation/tests/test_m5_dashboard_jobs.py -q
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . validate
```

Expected: tests pass and validation reports no errors/warnings.

- [ ] **Step 4: Record completion and commit**

Mark WP-603 completed with test evidence, rebuild PRJ-001 indexes when drifted, then:

```bash
git add src/research_os/services/operations_health.py \
  src/research_os/services/candidate_db.py src/research_os/ui/app.py \
  09_Automation/tests/test_candidate_db.py \
  09_Automation/tests/test_m5_dashboard_jobs.py \
  00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md \
  08_Indexes/Projects/PRJ-001
git commit -m "feat: unify operations and system health"
```
