# Handover Baseline Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the four confirmed handover drifts so the repository, governance documents, UI wording, and generated PRJ-001 indexes describe the approved v0.3 state consistently.

**Architecture:** Treat governance Markdown as reviewed project state, generated indexes as derived output, and UI wording as a tested presentation contract. Make semantic corrections first, then rebuild indexes through the existing CLI so generated files are never edited by hand.

**Tech Stack:** Python 3.12, unittest/pytest, FastAPI TestClient, Markdown/YAML, `research-os` CLI.

---

## File Map

- Modify `09_Automation/tests/test_m5_dashboard_jobs.py`: regression tests for Candidate and Impact UI wording.
- Modify `09_Automation/tests/test_m6_release.py`: repository-level assertions for approved governance state and generated-index drift.
- Modify `src/research_os/ui/app.py`: correct the two confirmed display strings only.
- Modify `README.md`: replace obsolete 10-Source Gate wording with the completed state.
- Modify `00_System/v0.3_AI_Industry_Intelligence_OS/00_Master_Roadmap.md`: record the approved execution state.
- Modify `00_System/v0.3_AI_Industry_Intelligence_OS/01_Product_Charter_and_Governance.md`: mark RCP-v03-004/005/006/010 approved.
- Modify `00_System/Taxonomy_v2_Proposal.md` and `00_System/Taxonomy_v2_Mapping.md`: remove obsolete pending-proposal language while preserving taxonomy content.
- Regenerate `08_Indexes/Projects/PRJ-001/Source_Index.md`, `Thesis_Index.md`, `Review_Index.md`, and `Home_Dashboard.md` through `research-os index --project PRJ-001 --apply`.

### Task 1: Pin the confirmed drift with failing tests

- [ ] **Step 1: Add UI regression assertions**

In `09_Automation/tests/test_m5_dashboard_jobs.py`, extend the existing dashboard tests with:

```python
def test_candidate_queue_uses_discovery_time_label(self) -> None:
    with self.client() as client:
        response = client.get("/candidates")
    self.assertEqual(200, response.status_code)
    self.assertIn("发现时间", response.text)
    self.assertNotIn(">发布时间<", response.text)

def test_impact_page_describes_active_multihop(self) -> None:
    with self.client() as client:
        response = client.get("/impact")
    self.assertEqual(200, response.status_code)
    self.assertIn("1–3 跳", response.text)
    self.assertNotIn("多跳待 C-018", response.text)
```

- [ ] **Step 2: Add governance and index assertions**

In `09_Automation/tests/test_m6_release.py`, add a test that reads the real repository and asserts:

```python
def test_approved_v03_governance_and_project_indexes_are_current(self) -> None:
    root = Path(__file__).resolve().parents[2]
    charter = (root / "00_System/v0.3_AI_Industry_Intelligence_OS/01_Product_Charter_and_Governance.md").read_text(encoding="utf-8")
    for decision in ("RCP-v03-004", "RCP-v03-005", "RCP-v03-006", "RCP-v03-010"):
        row = next(line for line in charter.splitlines() if decision in line)
        self.assertIn("approved", row)
        self.assertNotIn("proposed", row)
    self.assertNotIn("10-Source Gate 待", (root / "README.md").read_text(encoding="utf-8"))

    from research_os.services.indexing import index_drift, render_project_indexes
    from research_os.services.validation import validate_repository
    objects, _ = validate_repository(root)
    self.assertEqual([], index_drift(root, render_project_indexes(objects, "PRJ-001")))
```

- [ ] **Step 3: Run the focused tests and confirm RED**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_m5_dashboard_jobs.py \
  09_Automation/tests/test_m6_release.py -q
```

Expected: the new wording/governance/index assertions fail while pre-existing tests pass.

### Task 2: Correct authoritative status and presentation wording

- [ ] **Step 1: Apply the four governance corrections**

Edit only the affected status sentences/rows:

```text
README: state that the 10-Source Gate is complete and link the existing gate record.
Master Roadmap: set the approved execution header/status already authorized by the recorded decisions.
Product Charter: set RCP-v03-004/005/006/010 to approved without changing their decision text.
Taxonomy Proposal/Mapping: describe Taxonomy v2 as approved/current and retain all mappings verbatim.
```

- [ ] **Step 2: Correct the UI strings**

In `src/research_os/ui/app.py`, change the Candidate column header from `发布时间` to `发现时间`. Replace the obsolete C-018 sentence with `reviewed Impact 支持 1–3 跳路径；每跳保留机制、Evidence 与置信度。` and describe the field-gate packet as approved.

- [ ] **Step 3: Run focused tests and confirm only index drift remains**

Run the Task 1 command. Expected: UI and governance assertions pass; the PRJ-001 drift assertion still fails until regeneration.

### Task 3: Rebuild derived PRJ-001 indexes

- [ ] **Step 1: Preview the exact generated changes**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os \
  --root . index --project PRJ-001 --dry-run
```

Expected: exactly the four confirmed files are reported as changed; no authoritative Thesis/Evidence/Source file is listed.

- [ ] **Step 2: Apply the generated indexes**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os \
  --root . index --project PRJ-001 --apply
```

Expected: the four PRJ-001 index files are rewritten by the generator.

- [ ] **Step 3: Verify the reconciled baseline**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_m5_dashboard_jobs.py \
  09_Automation/tests/test_m6_release.py -q
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . validate
git diff --check
```

Expected: tests pass, validation reports `0 errors, 0 warnings`, and `git diff --check` is silent.

- [ ] **Step 4: Commit the baseline reconciliation**

```bash
git add README.md 00_System src/research_os/ui/app.py \
  09_Automation/tests/test_m5_dashboard_jobs.py \
  09_Automation/tests/test_m6_release.py 08_Indexes/Projects/PRJ-001
git commit -m "fix: reconcile v0.3 handover baseline"
```
