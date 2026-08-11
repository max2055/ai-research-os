# WP-610 to WP-612 Release Engineering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete F-012 through F-020 with measured performance, enforceable security, licensed-channel governance evidence, recoverable Candidate DB snapshots, rehearsed recovery/migration, and usable v0.3 operating documentation.

**Architecture:** Benchmark before optimizing and add no persistent authoritative cache. Keep backups immutable and verifiable through SQLite integrity plus SHA-256 manifests; recovery/migration drills operate on disposable clean copies. Turn safety and release claims into automated tests where machine-verifiable and dated audit records where human/external judgment is required.

**Tech Stack:** Python 3.12, pytest, FastAPI TestClient, SQLite backup API, SHA-256, existing scheduler/Job/migration/release services, ruff, mypy.

---

## File Map

- Modify `src/research_os/services/benchmark.py`: real Dashboard/read-model/SLO benchmark runner.
- Create `src/research_os/services/backup.py`: immutable Candidate DB snapshot, integrity verification, SHA-256 manifest, age status.
- Modify `src/research_os/services/schedule.py`, `src/research_os/services/jobs.py`, `src/research_os/cli.py`, and `src/research_os/runtime/product.py`: scheduled backup Job and CLI dry-run/apply surface.
- Modify `09_Automation/tests/test_m6_benchmark.py`: F-012/F-013 performance contracts.
- Create `09_Automation/tests/test_m6_security.py`: F-014 HTML/traversal/secret/bounds/mutation-route gate.
- Create `09_Automation/tests/test_backup.py`: F-016 snapshot, manifest, age, scheduler, and failure behavior.
- Modify `09_Automation/tests/test_m6_release.py`: require benchmark, security, license, backup, recovery, migration, runbook, and limitations records without relaxing Pilot/Resolution gates.
- Create `00_System/v0.3_Channel_License_Audit.md`: F-015 metadata audit of every enabled Channel.
- Create `00_System/v0.3_Performance_Benchmark.md`: F-012/F-013 measured profile/SLO results.
- Create `00_System/v0.3_Recovery_Drill.md`: F-017 clean-clone record with RTO/RPO.
- Create `00_System/v0.3_Migration_Rehearsal.md`: F-018 forward/rollback record.
- Create `00_System/v0.3_User_Runbook.md`: F-019 install and operating procedures.
- Create `00_System/v0.3_Known_Limitations.md`: F-020 boundaries.
- Modify `00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md`: mark WP-610/611/612 completed only after their respective evidence passes.

### Task 1: F-012 profile and F-013 SLO benchmark

- [ ] **Step 1: Write failing benchmark contract tests**

```python
result = benchmark_dashboard(root, repeats=5, impact_edges=50_000)
for operation in (
    "home",
    "candidate_queue",
    "company",
    "sector",
    "impact_3_hop",
    "validate",
    "index_rebuild",
):
    self.assertIn(operation, result.measurements)
    self.assertGreaterEqual(result.measurements[operation].samples, 5)
    self.assertGreaterEqual(result.measurements[operation].p95_seconds, 0)
self.assertEqual([], result.authoritative_writes)
```

Assert `repeats < 3`, negative sizes, and impact edges below path depth constraints raise `ValueError`. Assert the result reports current object/Candidate/edge counts and threshold/pass status per Phase 6 §5.

- [ ] **Step 2: Confirm RED and implement instrumentation**

Add `benchmark_dashboard(root, *, repeats=5, impact_edges=50_000) -> DashboardBenchmark` using `perf_counter`, existing snapshot composers, TestClient GETs, and the synthetic impact benchmark fixture. Compute p95 using the nearest-rank rule and compare to explicit seconds thresholds. Capture cProfile cumulative top calls for failing operations; do not create a persistent cache.

- [ ] **Step 3: Confirm GREEN and measure the real repository**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_m6_benchmark.py -q
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os \
  --root . benchmark-dashboard --repeats 7 --impact-edges 50000 \
  > /tmp/ai-research-os-v03-benchmark.txt
```

Expected: tests pass and output contains measured p95, scale, threshold, pass/fail, and profile evidence for any miss.

- [ ] **Step 4: Record the benchmark decision**

Write `v0.3_Performance_Benchmark.md` with command, commit, host, date/timezone, seven raw samples, p95, SLO, profile result, and decision. If an SLO misses, document it in Known Limitations; introduce an in-memory request-scoped preload only when the profile identifies repeated validation, and rerun the same benchmark to prove the improvement.

### Task 2: F-014 security regression gate

- [ ] **Step 1: Write the complete failing security suite**

`test_m6_security.py` must cover:

```python
def test_all_stored_strings_are_html_escaped(): ...
def test_object_and_asset_paths_cannot_escape_root(): ...
def test_secret_sentinels_never_appear_in_html_logs_or_snapshots(): ...
def test_query_depth_limit_and_candidate_page_size_are_bounded(): ...
def test_dashboard_routes_are_get_only_except_llm_configuration(): ...
def test_external_prompt_injection_text_is_rendered_as_data_only(): ...
```

The mutation invariant must enumerate `app.routes` and allow non-GET only for `/llm/config`, `/llm/models`, and `/llm/test`. Traversal payloads include `../`, percent-encoded traversal, absolute paths, and symlink escape. Bounds cover Impact depth outside 1–3 and Candidate limits above the documented maximum.

- [ ] **Step 2: Run RED and make minimal boundary fixes**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_m6_security.py -q
```

Use resolved-path containment, existing `esc()`, FastAPI `Query(ge=..., le=...)`, and allowlisted presence-only config state. Do not weaken or skip an exploit case.

- [ ] **Step 3: Confirm GREEN**

Run the Step 2 command. Expected: all attack payloads are rejected/escaped and no secret sentinel is present.

### Task 3: F-015 enabled Channel license audit

- [ ] **Step 1: Add a failing audit completeness test**

Parse all enabled `source_channel` objects and the audit table, then assert exact ID set equality and non-empty metadata columns:

```python
self.assertEqual(enabled_ids, audited_ids)
for row in audit_rows:
    self.assertIn(row["license_status"], {"reviewed", "restricted", "blocked"})
    self.assertTrue(row["license_notes"])
    self.assertRegex(row["robots_checked_at"], r"^\d{4}-\d{2}-\d{2}$")
```

The document must state that this is an internal metadata-governance audit, not fresh legal advice or live robots verification.

- [ ] **Step 2: Generate and review the metadata table**

Create one row per enabled Channel with ID, type, license status, review status, notes, robots check date, permitted ingestion mode, and follow-up. Preserve `unknown`/`pending` as a blocker rather than inventing approval.

- [ ] **Step 3: Verify audit completeness**

Run `pytest 09_Automation/tests/test_m6_release.py -k license -q`. Expected: the audit covers every enabled Channel and flags no unresolved status as passed.

### Task 4: F-016 Candidate DB backup automation

- [ ] **Step 1: Write failing backup tests**

Assert `create_candidate_snapshot` uses a live SQLite backup, refuses overwrite, verifies `PRAGMA integrity_check`, and emits a manifest containing relative file, SHA-256, bytes, source DB schema version, created time, and source DB maximum update timestamp. Tampering must fail `verify_candidate_snapshot`; `backup_age_status` must classify `fresh`, `stale`, and `missing` at a 24-hour RPO threshold.

- [ ] **Step 2: Confirm RED and implement backup primitives**

Create:

```python
def create_candidate_snapshot(
    root: Path, destination: Path, *, now: str | None = None
) -> dict[str, Any]: ...
def verify_candidate_snapshot(snapshot: Path, manifest: Path) -> dict[str, Any]: ...
def backup_age_status(
    manifest: Path, *, now: str | None = None, max_age_hours: int = 24
) -> dict[str, Any]: ...
```

Write to a sibling temporary file, fsync, verify, then atomically rename. The manifest contains no Candidate content, URL, or secret.

- [ ] **Step 3: Add CLI and scheduler integration with tests**

Add `research-os backup candidate --destination PATH --dry-run|--apply`, a daily schedule descriptor, and a Job record on apply. Dry-run must not create files or Jobs; failure creates a failed Job with a redacted message; apply refuses destinations inside authoritative Markdown directories.

- [ ] **Step 4: Verify backup behavior**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_backup.py \
  09_Automation/tests/test_candidate_db.py \
  09_Automation/tests/test_schedule.py -q
```

Expected: snapshot, tamper, age, CLI dry-run/apply, and Job tests pass.

### Task 5: F-017 clean-clone recovery drill

- [ ] **Step 1: Create a verified snapshot from the current Candidate DB**

Use an explicit temporary destination outside Git, then verify its hash and integrity with the new CLI. Record snapshot timestamp and maximum Candidate update timestamp as RPO evidence.

- [ ] **Step 2: Perform the drill in a disposable directory**

Clone the current branch into `mktemp -d`, restore `01_Inbox/_assets` as real files, restore the Candidate snapshot, install/use the pinned venv, rebuild global and PRJ-001 indexes, and run validate, full tests, ruff, mypy, Dashboard GET smoke, and one discovery dry-run. Verify a sampled Candidate→Source→asset chain.

- [ ] **Step 3: Record F-017 evidence**

`v0.3_Recovery_Drill.md` records commit, start/end timestamps, elapsed RTO, snapshot/data timestamps and RPO, every command/exit status, Candidate integrity/hash, asset hash result, smoke routes, recovered/not-recovered boundaries (including secrets and launchd), and an honest pass/fail against RTO <4h and RPO ≤24h.

### Task 6: F-018 migration and rollback rehearsal

- [ ] **Step 1: Add migration preservation tests**

Using a clean copied fixture, record hashes for append-only formal objects, run existing v0.2→v0.3 compatibility/migration dry-run and apply, verify schema/reference integrity, run rollback, and assert original object bytes are unchanged unless the migration explicitly owns that file.

- [ ] **Step 2: Execute the rehearsal on a disposable clean copy**

Run compatibility baseline, migration dry-run, migration apply, validate/index/test, rollback, validate/index/test. Never point rehearsal writes at the working repository.

- [ ] **Step 3: Record the migration decision**

`v0.3_Migration_Rehearsal.md` lists source/target versions, commit, commands, migrated files, before/after/rollback hashes, append-only preservation, Candidate DB version result, failure injection, rollback outcome, elapsed time, and pass/fail.

### Task 7: F-019 user runbook and F-020 Known Limitations

- [ ] **Step 1: Write documentation completeness tests**

Assert the runbook contains install/config, Dashboard, daily/weekly/monthly workflows, Candidate triage, Evidence/Impact/Analysis/Forecast/Decision review, backup/restore, failure response, secrets, and escalation. Assert Known Limitations covers data coverage/freshness, model uncertainty/provider retention, license constraints, SQLite/single-user limits, read-only Web UI, calibration insufficiency, no automated investment action, and WP-530/WP-620 real-time gates.

- [ ] **Step 2: Write the operator-focused runbook**

Every command uses the repository venv/PYTHONPATH, states dry-run vs apply, expected success signal, safe retry, and the authoritative/non-authoritative effect. Include P0–P3 handling from Phase 6 §6 and the restore sequence from Git/assets/Candidate snapshot/config/launchd through validation.

- [ ] **Step 3: Write the decision-boundary limitations**

Separate facts (measured counts/results), inferences (likely scaling implications), and judgments (release/operator boundaries). Link each measured claim to its benchmark/audit/drill record. State that Forecast outcomes must arrive naturally and that Recommendations are research drafts, not buy/sell/position/execution instructions.

### Task 8: Full verification and close-out

- [ ] **Step 1: Update Backlog without crossing real-time gates**

Mark WP-610/611/612 completed only when their evidence files/tests pass. Keep WP-530 and WP-620 open/proposed until natural Forecast resolutions and 30-day Pilot/human review requirements occur. Add no synthetic dates, outcomes, reviewers, or approvals.

- [ ] **Step 2: Rebuild indexes and run the complete gate**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . index --apply
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . index --project PRJ-001 --apply
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . validate
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest 09_Automation/tests/ -q
/Users/max/.venvs/ai-research-os/bin/python -m ruff check src 09_Automation/tests
/Users/max/.venvs/ai-research-os/bin/python -m mypy src
git diff --check
```

Expected: `0 errors, 0 warnings`; full pytest green with only the established skip; ruff/mypy/diff checks pass.

- [ ] **Step 3: Run real Dashboard smoke**

Start loopback server and GET `/`, `/impact`, `/analysis`, `/decision`, `/operations`, `/health`, one Company, one Sector, and `/candidates`. Expected: HTTP 200, required headings present, no secret sentinel, and no application traceback.

- [ ] **Step 4: Commit release engineering**

```bash
git add src 09_Automation/tests 00_System \
  08_Indexes docs/superpowers/plans
git commit -m "feat: complete v0.3 release engineering"
```

- [ ] **Step 5: Review branch history and hand off**

Run `git status --short --branch`, `git log --oneline --decorate -8`, and `research-os release check`. Report machine-verifiable passes and remaining WP-530/WP-620 blockers separately; do not describe v0.3 as released before the human/time gates pass.
