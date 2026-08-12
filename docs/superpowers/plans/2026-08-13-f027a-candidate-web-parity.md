# F-027A Candidate Web Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add audited Candidate restore and promote workflows to the website and establish a machine-checked parity registry for the remaining Web-only migration.

**Architecture:** Extend the F-026 Mutation Gateway with operation adapters instead of adding route-specific security. Candidate restore stays inside one SQLite transaction with the generic audit; Candidate promote uses the existing staged Source/asset service, binds its complete preview to the signed token, and coordinates compensation evidence if the Candidate link transaction cannot complete. A tracked parity registry maps every current CLI command to its Web or internal disposition and fails closed on omissions.

**Tech Stack:** Python 3.12+, FastAPI/Starlette, Pydantic, SQLite, existing repository transaction service, pytest, Ruff, mypy.

---

## Frozen delivery contract

- Top-level task count: 6.
- Non-scope: Source/Event/Review/Impact/Decision editing; scheduler/backup/recovery; CLI removal; remote/multi-user authentication; Candidate bulk purge; changes to research authority or F-023 blockers.
- Acceptance: restore and promote each complete detail → preview → confirmation → commit → 303 → result; commit accepts only CSRF and preview token; failure leaves no half-authoritative Source or Candidate link; parity registry covers every current CLI parser leaf.
- Resource budget: focused test per task and one complete repository Gate after Task 6.

## File responsibility map

- Create `src/research_os/services/product_capabilities.py`: typed CLI/Web/internal parity registry and validation.
- Create `src/research_os/services/web_candidate_mutations.py`: restore/promote preview and commit adapters.
- Modify `src/research_os/services/mutation_audit.py`: allow repository-backed mutation audit records without secrets or raw content.
- Modify `src/research_os/services/promote.py`: expose staged transaction primitives and deterministic promotion version/input model.
- Modify `src/research_os/services/triage.py`: connection-scoped restore primitive.
- Modify `src/research_os/ui/app.py`: Candidate restore/promote forms, confirmations, commits, and results.
- Modify `src/research_os/ui/styles.css`: shared compact mutation form/result styling only.
- Create `09_Automation/tests/test_product_capabilities.py`: parser/registry/route parity tests.
- Create `09_Automation/tests/test_web_candidate_parity.py`: restore/promote service and HTTP tests.
- Modify `09_Automation/tests/test_m6_security.py`: exact expanded route allowlist and authority boundary.
- Modify governance/evidence files only after measured checks pass.

### Task 1: Complete product capability registry

**Files:**
- Create: `src/research_os/services/product_capabilities.py`
- Create: `09_Automation/tests/test_product_capabilities.py`
- Modify: `src/research_os/cli.py`

- [ ] **Step 1: Write failing registry completeness tests**

Add tests that call a new `cli_capability_keys()` helper, load `PRODUCT_CAPABILITIES`,
and assert exact equality. Each entry must declare `owner`, `disposition` (`web`,
`internal`, or `remove`), `web_routes`, `authority`, and `delivery_feature`. Also assert
that every non-GET FastAPI route appears in at least one capability.

```python
def test_every_cli_leaf_has_one_product_disposition(self) -> None:
    cli_keys = cli_capability_keys()
    registry_keys = {item.cli_key for item in PRODUCT_CAPABILITIES}
    assert registry_keys == cli_keys
    assert len(registry_keys) == len(PRODUCT_CAPABILITIES)

def test_current_candidate_web_routes_are_declared(self) -> None:
    routes = registered_mutation_routes(create_app(self.root))
    declared = {
        route
        for item in PRODUCT_CAPABILITIES
        for route in item.web_routes
        if item.disposition == "web"
    }
    assert routes <= declared
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_product_capabilities.py -q
```

Expected: import failure because the registry and parser introspection do not exist.

- [ ] **Step 3: Add parser introspection and the typed registry**

Refactor parser construction into `build_parser()` without changing CLI behavior.
Implement deterministic recursive argparse leaf discovery. Create frozen
`ProductCapability` records for every leaf. Current read-only capabilities may point to
existing GET pages; incomplete writes declare their target F-027/F-028 route; scheduler
runner entries use `internal`; the product CLI entry uses `remove` under F-029.

- [ ] **Step 4: Run registry and existing CLI tests**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_product_capabilities.py \
  09_Automation/tests/test_cli.py -q
```

Expected: PASS with no CLI output or parser regression.

- [ ] **Step 5: Commit**

```bash
git add src/research_os/cli.py src/research_os/services/product_capabilities.py \
  09_Automation/tests/test_product_capabilities.py
git commit -m "feat(v0.3): track Web product capability parity"
```

### Task 2: Candidate restore adapter

**Files:**
- Modify: `src/research_os/services/triage.py`
- Create: `src/research_os/services/web_candidate_mutations.py`
- Create: `09_Automation/tests/test_web_candidate_parity.py`

- [ ] **Step 1: Write failing restore transaction tests**

Cover dry preview, complete Candidate-row target version, actor/operation binding,
atomic Candidate/action/audit commit, rollback after injected audit failure, stale
target, replay, expiry, and restore refusal for `new` or `promoted` candidates.

```python
def test_restore_commit_is_one_transaction(self) -> None:
    preview = preview_candidate_restore(self.root, "CND-x", actor="max")
    result = commit_candidate_restore(self.root, preview)
    assert result["status"] == "new"
    assert self.actions("CND-x") == [("restore", "max")]
    assert self.audit(preview.mutation_id) == [("committed", result["action_id"])]
```

- [ ] **Step 2: Run the restore tests and verify RED**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_web_candidate_parity.py -k restore -q
```

Expected: import failure for the restore adapter.

- [ ] **Step 3: Implement connection-scoped restore and adapter**

Make `restore_candidate(..., connection=None)` match the F-026 dismiss transaction
contract. The adapter normalizes the fixed restore reason, prepares a
`candidate.restore` preview, and commits Candidate state, action, and audit in one
`BEGIN IMMEDIATE` transaction.

- [ ] **Step 4: Run restore and triage tests**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_triage.py \
  09_Automation/tests/test_web_candidate_parity.py -k 'restore or triage' -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/research_os/services/triage.py \
  src/research_os/services/web_candidate_mutations.py \
  09_Automation/tests/test_web_candidate_parity.py
git commit -m "feat(v0.3): add atomic Candidate restore adapter"
```

### Task 3: Candidate restore website flow

**Files:**
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/ui/styles.css`
- Modify: `09_Automation/tests/test_web_candidate_parity.py`
- Modify: `09_Automation/tests/test_m6_security.py`

- [ ] **Step 1: Write failing HTTP tests**

Test dismissed/expired detail forms, preview rendering, escaped fields, commit with
token+CSRF only, 303 redirect, refresh-safe result, replay 409, hostile Origin 403,
missing identity 503, wrong Candidate route 403/409, and no restore form for new or
promoted rows.

- [ ] **Step 2: Run HTTP tests and verify RED**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_web_candidate_parity.py -k restore_http -q
```

Expected: 404 for restore routes.

- [ ] **Step 3: Add restore routes and renderers**

Add exactly:

```text
POST /pipeline/queue/{candidate_id}/restore/preview
POST /pipeline/queue/{candidate_id}/restore/commit
```

Reuse the existing Candidate result route keyed by mutation ID. The commit handler
accepts only `csrf_token` and `preview_token` form fields.

- [ ] **Step 4: Run Web/security tests**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_web_mutation.py \
  09_Automation/tests/test_web_candidate_parity.py \
  09_Automation/tests/test_m6_security.py -q
```

Expected: PASS and exact non-GET allowlist includes seven routes.

- [ ] **Step 5: Commit**

```bash
git add src/research_os/ui/app.py src/research_os/ui/styles.css \
  09_Automation/tests/test_web_candidate_parity.py \
  09_Automation/tests/test_m6_security.py
git commit -m "feat(v0.3): add Candidate restore Web flow"
```

### Task 4: Candidate promote transactional adapter

**Files:**
- Modify: `src/research_os/services/promote.py`
- Modify: `src/research_os/services/mutation_audit.py`
- Modify: `src/research_os/services/web_candidate_mutations.py`
- Modify: `09_Automation/tests/test_promote.py`
- Modify: `09_Automation/tests/test_web_candidate_parity.py`

- [ ] **Step 1: Write failing promote transaction tests**

Use a disposable local file capture and cover complete preview fields, canonical input
digest, Candidate target version, immutable Source/asset paths, duplicate refusal,
license/User-Agent validation, staged rollback before publish, Candidate-link failure
compensation, and committed audit without raw body/token/secret.

- [ ] **Step 2: Run promote tests and verify RED**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_promote.py \
  09_Automation/tests/test_web_candidate_parity.py -k promote -q
```

Expected: failures because promotion has no Gateway adapter or compensation record.

- [ ] **Step 3: Expose staged promotion primitives**

Keep `prepare_promote` as the sole validation and capture owner. Add an adapter preview
whose normalized input contains only bounded source metadata and immutable staged asset
hashes. Add a commit coordinator that publishes the repository transaction, links the
Candidate, records audit, and on post-publish failure records a recovery manifest and
restores the pre-commit repository bytes before returning failure.

- [ ] **Step 4: Run promote/service tests**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_promote.py \
  09_Automation/tests/test_web_candidate_parity.py -k promote -q
```

Expected: PASS with no half-created Source or linked Candidate on injected failures.

- [ ] **Step 5: Commit**

```bash
git add src/research_os/services/promote.py \
  src/research_os/services/mutation_audit.py \
  src/research_os/services/web_candidate_mutations.py \
  09_Automation/tests/test_promote.py \
  09_Automation/tests/test_web_candidate_parity.py
git commit -m "feat(v0.3): coordinate audited Candidate promotion"
```

### Task 5: Candidate promote website flow

**Files:**
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/ui/styles.css`
- Modify: `09_Automation/tests/test_web_candidate_parity.py`
- Modify: `09_Automation/tests/test_m6_security.py`
- Modify: `09_Automation/tests/test_product_capabilities.py`

- [ ] **Step 1: Write failing promote HTTP tests**

Cover new Candidate form defaults, fixed actor, override validation, preview with Source
metadata and asset hashes, commit token-only fields, result links, 303 refresh safety,
replay/stale/Origin/CSRF/missing identity failures, and HTML escaping.

- [ ] **Step 2: Run HTTP tests and verify RED**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_web_candidate_parity.py -k promote_http -q
```

Expected: 404 for promote routes.

- [ ] **Step 3: Add promote routes and UI**

Add exactly:

```text
POST /pipeline/queue/{candidate_id}/promote/preview
POST /pipeline/queue/{candidate_id}/promote/commit
```

Use searchable Project/type/grade controls, server-derived publisher defaults, and a
dedicated confirmation page. Never accept actor or captured content from the browser.

- [ ] **Step 4: Run all Candidate Web tests**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_web_mutation.py \
  09_Automation/tests/test_web_candidate_parity.py \
  09_Automation/tests/test_product_capabilities.py \
  09_Automation/tests/test_m6_security.py -q
```

Expected: PASS and exact non-GET allowlist includes nine routes.

- [ ] **Step 5: Commit**

```bash
git add src/research_os/ui/app.py src/research_os/ui/styles.css \
  09_Automation/tests/test_web_candidate_parity.py \
  09_Automation/tests/test_product_capabilities.py \
  09_Automation/tests/test_m6_security.py
git commit -m "feat(v0.3): add Candidate promote Web flow"
```

### Task 6: F-027A integration evidence and governance

**Files:**
- Modify: `README.md`
- Modify: `00_System/Dashboard_Design_v2.md`
- Modify: `00_System/v0.3_User_Runbook.md`
- Modify: `00_System/v0.3_Known_Limitations.md`
- Modify: `00_System/v0.3_AI_Industry_Intelligence_OS/07_Phase_6_Productization_and_Scale.md`
- Modify: `00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md`
- Create: dated F-027A verification record

- [ ] **Step 1: Run complete integration Gate**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest -m 'not local_integration' -q
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest --cov=research_os --cov-branch --cov-report=term -m 'not local_integration' -q
/Users/max/.venvs/ai-research-os/bin/python -m ruff check src 09_Automation/tests
/Users/max/.venvs/ai-research-os/bin/python -m ruff format --check src 09_Automation/tests
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m mypy src/research_os
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m compileall -q src
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . validate --strict
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . index --check
```

Expected: all pass, branch coverage remains >=80%, validation 0/0, indexes current.

- [ ] **Step 2: Run real loopback disposable smoke**

Exercise Candidate restore and local-file promote through HTTP, including hostile
Origin, preview read-only, commit 303, result GET, replay 409, exact action/audit rows,
Source/asset integrity, and no Thesis or Review change.

- [ ] **Step 3: Update docs with measured state**

Mark Candidate dismiss/restore/promote complete, F-027 research-object parity still in
progress, and F-028/F-029 incomplete. Record exact commands, counts, commit, coverage,
smoke results, security paths, and unchanged F-023 blocker contract.

- [ ] **Step 4: Run final focused provenance checks**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_m6_release.py \
  09_Automation/tests/test_m6_security.py \
  09_Automation/tests/test_web_mutation.py \
  09_Automation/tests/test_web_candidate_parity.py \
  09_Automation/tests/test_product_capabilities.py -q
git diff --check
```

Expected: PASS; no external untracked Job record is staged.

- [ ] **Step 5: Commit**

```bash
git add README.md 00_System/Dashboard_Design_v2.md \
  00_System/v0.3_User_Runbook.md 00_System/v0.3_Known_Limitations.md \
  00_System/v0.3_AI_Industry_Intelligence_OS/07_Phase_6_Productization_and_Scale.md \
  00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md \
  00_System/v0.3_*Verification*.md
git commit -m "docs(v0.3): verify F-027A Candidate Web parity"
```
