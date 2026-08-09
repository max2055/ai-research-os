# WP-602 Research Workspaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver F-007 Impact Explorer, F-008 Analysis Workspace, and F-009 Decision Desk as complete read-only research workspaces backed by composable read models.

**Architecture:** Add three pure snapshot composers to `read_model.py` that validate once, compose existing domain services, and return display-neutral dictionaries. Keep `app.py` responsible only for escaping and rendering; no route may promote, resolve, approve, or otherwise mutate authoritative objects.

**Tech Stack:** Python 3.12, FastAPI, Pydantic-backed ResearchObject models, unittest/pytest, existing impact/analysis/forecast/valuation/recommendation services.

---

## File Map

- Modify `src/research_os/services/read_model.py`: add `impact_explorer_snapshot`, `analysis_workspace_snapshot`, and `decision_desk_snapshot`.
- Modify `src/research_os/ui/app.py`: render the three snapshots with query-only selectors.
- Modify `09_Automation/tests/test_m5_dashboard_jobs.py`: read-model contracts, rendered sections, escaping, empty states, and GET-only invariants.
- Modify `00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md`: mark WP-602 complete with test evidence after acceptance.

### Task 1: F-007 Impact Explorer read model

- [ ] **Step 1: Write a failing snapshot contract test**

Create fixture objects using the existing helpers in `test_m5_dashboard_jobs.py`, then assert:

```python
snapshot = impact_explorer_snapshot(root, start_id=event_id, max_depth=3)
self.assertEqual(event_id, snapshot["start_id"])
self.assertEqual(3, snapshot["max_depth"])
self.assertTrue(snapshot["direct_assertions"])
self.assertTrue(snapshot["paths"])
self.assertIn("hops", snapshot["paths"][0])
self.assertIn("weakest_confidence", snapshot["paths"][0])
self.assertIn("pruning_reasons", snapshot)
self.assertIn("conflicts", snapshot)
self.assertIn("countervailing_factors", snapshot)
self.assertIn("alternative_explanations", snapshot)
```

Also assert `max_depth=0` and `max_depth=4` raise `ValueError`, and pending assertions never appear in reviewed paths.

- [ ] **Step 2: Run the test and confirm RED**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_m5_dashboard_jobs.py -k impact_explorer_snapshot -q
```

Expected: import failure for `impact_explorer_snapshot`.

- [ ] **Step 3: Implement the minimal composer**

Add this public contract to `read_model.py`:

```python
def impact_explorer_snapshot(
    root: Path,
    *,
    start_id: str | None = None,
    max_depth: int = 3,
) -> dict[str, Any]:
    """Return reviewed direct assertions and explainable 1-3 hop paths."""
```

Validate `max_depth in {1, 2, 3}`; load repository objects once; select reviewed `impact_assertion` objects; call `expand_impact_paths`, `dedup_paths`, `path_confidence`, and `detect_contradictions`. Normalize every hop to `assertion_id`, `source_id`, `target_id`, `predicate`, `mechanism`, `evidence_ids`, `direction`, `horizon`, and `confidence`. Return deterministic ID-sorted direct assertions/paths plus explicit pruning reasons, contradictions grouped as positive/negative and multi-horizon, and deduplicated countervailing/alternative-explanation text from assertion metadata.

- [ ] **Step 4: Run the focused test and confirm GREEN**

Run the Step 2 command. Expected: all F-007 snapshot tests pass.

### Task 2: Render F-007 without mutation

- [ ] **Step 1: Write failing route assertions**

```python
response = client.get(f"/impact?start={event_id}&depth=3")
self.assertEqual(200, response.status_code)
for label in ("直接断言", "1–3 跳路径", "最弱环节置信度", "剪枝原因", "冲突信号", "反向因素", "替代解释"):
    self.assertIn(label, response.text)
self.assertIn("Evidence", response.text)
```

Assert `<script>` stored in mechanism text is rendered as `&lt;script&gt;`, invalid depth returns HTTP 422, and the `/impact` route methods equal `{"GET"}`.

- [ ] **Step 2: Confirm RED, then render the snapshot**

Run `pytest 09_Automation/tests/test_m5_dashboard_jobs.py -k 'impact_page' -q`. Update `_impact_page` to accept `start` and `depth`, render each hop and all required conflict/explanation sections using `esc()`, and pass the query parameters from the FastAPI route.

- [ ] **Step 3: Confirm GREEN**

Run the focused test. Expected: all F-007 route and escaping assertions pass.

### Task 3: F-008 Analysis Workspace read model

- [ ] **Step 1: Write failing contract and comparison tests**

```python
snapshot = analysis_workspace_snapshot(root, run_ids=[run_a, run_b])
self.assertEqual([run_a, run_b], [row["run_id"] for row in snapshot["runs"]])
for key in ("input_ids", "mode_version", "model_version", "template_version", "input_snapshot_hash", "prompt_hash", "output_hash", "evaluator_scores"):
    self.assertIn(key, snapshot["runs"][0])
for key in ("shared_facts", "evidence_omitted", "conflicting_signals"):
    self.assertIn(key, snapshot["comparison"])
self.assertIn("mode_metrics", snapshot)
```

Assert unknown run IDs raise `KeyError`, duplicate run IDs are deduplicated in caller order, and an empty selection returns all runs in stable newest-first order with `comparison=None`.

- [ ] **Step 2: Confirm RED and implement the composer**

Run `pytest 09_Automation/tests/test_m5_dashboard_jobs.py -k analysis_workspace_snapshot -q`. Add:

```python
def analysis_workspace_snapshot(
    root: Path,
    *,
    run_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Return immutable run provenance, evaluation, metrics, and comparison."""
```

Compose `compare_runs`, `evaluate_run`, and `mode_metrics`; preserve stored IDs/hashes/version strings without recomputation; return explicit shared facts, omitted evidence, and conflicting signals. Do not call proposal/promotion services.

- [ ] **Step 3: Confirm GREEN**

Run the Step 2 test command. Expected: Analysis Workspace composer tests pass.

### Task 4: Render F-008 comparison workflow

- [ ] **Step 1: Write failing route tests**

Request `/analysis?run=<A>&run=<B>` and assert visible sections for frozen inputs, versions, hashes, evaluator scores, shared facts, omitted Evidence, and conflicts. Assert all stored strings are escaped and `/analysis` exposes GET only.

- [ ] **Step 2: Render the snapshot and compare selector**

Change `_analysis_page` to receive selected run IDs. Use checkboxes in a GET form for selecting at most two runs, render provenance rows and comparison sections, and show an explicit empty state when no completed Runs exist. Do not add approve/promote controls.

- [ ] **Step 3: Verify the route**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_m5_dashboard_jobs.py -k analysis -q
```

Expected: read model, route, escaping, empty-state, and GET-only tests pass.

### Task 5: F-009 Decision Desk read model

- [ ] **Step 1: Write failing lifecycle/freshness tests**

```python
snapshot = decision_desk_snapshot(root, as_of="2026-08-09")
for key in ("open_forecasts", "due_forecasts", "overdue_forecasts", "calibration", "valuations", "recommendations", "resolution_history"):
    self.assertIn(key, snapshot)
self.assertEqual("insufficient_sample", snapshot["calibration"]["status"])
for key in ("age_days", "threshold_days", "freshness"):
    self.assertIn(key, snapshot["valuations"][0])
for key in ("catalysts", "falsification_conditions", "risks", "unknowns", "scenario_ids"):
    self.assertIn(key, snapshot["recommendations"][0])
```

Include due, overdue, resolved, fresh valuation, stale valuation, and absent-resolution fixtures. Assert invalid `as_of` raises `ValueError` and no synthetic resolution is created.

- [ ] **Step 2: Confirm RED and implement the composer**

Add:

```python
def decision_desk_snapshot(root: Path, *, as_of: str | None = None) -> dict[str, Any]:
    """Compose forecast lifecycle, calibration, valuation, and recommendation state."""
```

Compose `forecast_status_report`, `calibration_report`, `valuation_freshness`, and `recommendation_freshness`. Join scenario and resolution references by ID; expose unknown/missing fields honestly; return `calibration.status = "insufficient_sample"` until real Resolution objects satisfy the existing minimum sample rule.

- [ ] **Step 3: Confirm GREEN**

Run `pytest 09_Automation/tests/test_m5_dashboard_jobs.py -k decision_desk_snapshot -q`. Expected: all snapshot tests pass.

### Task 6: Render F-009 and close WP-602

- [ ] **Step 1: Write failing Decision Desk UI tests**

Assert `/decision` includes Open/Due/Overdue Forecast, calibration sample status, valuation age/threshold/freshness, catalysts, falsification conditions, risks, unknowns, scenarios, and resolution history. Assert GET-only routing and HTML escaping.

- [ ] **Step 2: Replace direct object scans with the snapshot**

Render all F-009 sections from `decision_desk_snapshot`. Preserve the statement that results are not prefilled before natural resolution, and expose no resolve/recommendation mutation control.

- [ ] **Step 3: Run WP-602 acceptance tests**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_impact_path.py \
  09_Automation/tests/test_analysis_evaluator.py \
  09_Automation/tests/test_mode_metrics.py \
  09_Automation/tests/test_phase5_lifecycle.py \
  09_Automation/tests/test_phase5_valuation.py \
  09_Automation/tests/test_m5_dashboard_jobs.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Record completion and commit**

Update WP-602 to `completed` with the exact acceptance command and keep WP-530/WP-620 unchanged. Rebuild PRJ-001 indexes if the Backlog is linked into them, then:

```bash
git add src/research_os/services/read_model.py src/research_os/ui/app.py \
  09_Automation/tests/test_m5_dashboard_jobs.py \
  00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md \
  08_Indexes/Projects/PRJ-001
git commit -m "feat: add research decision workspaces"
```
