# F-027C Research Workflow Web Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox
> (`- [ ]`) syntax for tracking.

**Goal:** Deliver the remaining Project-to-Decision research workflows through the
website without shelling out to the product CLI or granting automation approval or
Thesis mutation authority.

**Architecture:** Small typed Web adapters call existing domain `prepare_*` services
and convert their complete create/replace sets into `RepositoryMutationPlan` values.
FastAPI pages accept bounded domain fields, issue session-bound CSRF plus signed one-use
previews, and commit only the frozen server-side plan through the existing repository
mutation coordinator. Read-only views reuse existing read models.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, Markdown repositories, SQLite mutation
audit, pytest, Ruff, mypy, real loopback HTTP smoke.

---

## Frozen Delivery Contract

- Top-level task count: 4.
- Resource budget: one implementation owner, no delegated agents, focused tests per
  task, one complete repository Gate after the integrated candidate, and one release
  provenance refresh after that Gate.
- Acceptance checklist:
  - Every remaining F-027 capability registry row resolves to a real FastAPI route.
  - Every authoritative write uses detail/form -> preview -> confirm -> commit -> stable
    result, fixed local human identity, CSRF, signed one-use token, target version,
    redacted audit, and compensation on post-publication failure.
  - Commit endpoints accept only CSRF and preview token; actor, target paths, generated
    Markdown, model output, decisions, and final normalized content are server-frozen.
  - Generated Project, Action, Entity proposal, Ontology Assertion, Impact Assertion,
    Analysis Run, Thesis proposal, Forecast, Resolution, Valuation, and Recommendation
    objects retain their existing service defaults and review gates.
  - Review/activate/resolve/close/supersede operations are fixed-human-only and preserve
    stale-target checks and multi-file atomicity.
  - Analysis model calls execute once during preview; commit never calls a provider.
  - Thesis proposals remain non-authoritative proposal files. No F-027C route creates
    or edits a `THS-*` file, changes a Thesis conclusion, or changes confidence.
  - A real loopback disposable-repository smoke covers one primary workflow from each
    task and proves unrelated Thesis bytes remain identical.
  - Full quality, security, strict validation, global/PRJ-001/PRJ-002 index, and F-023
    Gates pass; F-023 retains exactly its five real-date/named-human blockers.
- Explicit non-scope: Channel/scheduler/jobs/brief/backup/recovery/benchmark/export,
  health/release mutations, remote auth, taxonomy or research-rule changes, automatic
  approval, automatic Thesis mutation, and any synthetic Pilot/cadence/resolution or
  release approval evidence.

### Task 1: Project, Action, Entity and Ontology Workbench

**Files:**
- Create: `src/research_os/services/web_registry_mutations.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/services/product_capabilities.py`
- Test: `09_Automation/tests/test_web_registry_parity.py`

- [ ] **Step 1: Write failing service and HTTP contract tests**

Cover Project create/advance-review, Action create/close, Company update proposal,
Entity create, and Ontology Assertion create. Assert bounded fields, unknown references,
pending defaults, fixed actor, CSRF, hostile Origin, replay, stale replacement,
transaction compensation, no browser-supplied path/content, and unchanged Thesis tree.

- [ ] **Step 2: Run the new tests and confirm route/adapter absence**

Run: `pytest -q 09_Automation/tests/test_web_registry_parity.py`

- [ ] **Step 3: Implement typed preparation adapters**

Call `prepare_project_draft`, `prepare_review_date_update`, `prepare_action_draft`, a
pure Action close preparation extracted from `close_action`, `prepare_entity_draft`,
`prepare_assertion_draft`, and `prepare_company_update_proposal`. Convert exact paths
and contents to one repository mutation plan without calling any CLI function.

- [ ] **Step 4: Add list/detail/forms and exact mutation routes**

Implement `/projects`, `/projects/new`, `/projects/{id}`, `/operations/actions`,
`/operations/actions/new`, `/operations/actions/{id}/close`, `/universe/entities/new`,
`/ontology/assertions/new`, and `/companies/{id}/update-proposals/new`, each with
explicit preview/commit/result routes as appropriate.

- [ ] **Step 5: Run focused tests and static checks, then commit**

Run the new test plus Project/Action/Ontology/domain suites, Ruff and mypy. Commit the
adapter, routes, capability registry, and tests together.

### Task 2: Impact and Analysis Workbench

**Files:**
- Create: `src/research_os/services/web_analysis_mutations.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/services/product_capabilities.py`
- Test: `09_Automation/tests/test_web_analysis_parity.py`

- [ ] **Step 1: Write failing Impact/Analysis authority tests**

Cover direct Impact proposal selection and draft creation, Analysis run/replay/eval,
and reviewed-run Thesis proposal. Assert reviewed-input gates, model call exactly once
during preview, frozen output at commit, pending review, provider error no-write,
replay/stale/audit compensation, and no `03_Theses` mutation.

- [ ] **Step 2: Run the new tests and confirm failures are missing Web behavior**

Run: `pytest -q 09_Automation/tests/test_web_analysis_parity.py`

- [ ] **Step 3: Build service adapters over existing engines**

Use `propose_direct_impacts` plus `prepare_impact_draft`, `prepare_run`, frozen-input
replay preparation, `evaluate_run`/`render_evaluation_packet`, and
`prepare_thesis_proposal`. Every generated file becomes a repository write set and
every provider response is captured only in the preview plan.

- [ ] **Step 4: Add Impact/Analysis forms, confirmation and results**

Add `/impact/proposals/new`, `/analysis/runs/new`, `/analysis/runs/{id}/replay`,
`/analysis/runs/{id}/evaluate`, and `/analysis/thesis-proposals/new` with exact
preview/commit routes and non-authoritative proposal language.

- [ ] **Step 5: Run focused/domain tests and static checks, then commit**

Run Impact path/proposal/audit and Analysis runner/evaluator/insight tests with the new
HTTP suite, Ruff and mypy. Commit this task as one reviewed behavior slice.

### Task 3: Forecast, Valuation and Recommendation Workbench

**Files:**
- Create: `src/research_os/services/web_decision_mutations.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/services/product_capabilities.py`
- Test: `09_Automation/tests/test_web_decision_parity.py`

- [ ] **Step 1: Write failing lifecycle and authority tests**

Cover Forecast draft/open/resolve, Valuation draft/supersede, Scenario extraction and
template, Recommendation draft/activate/close/supersede. Assert exact existing gates,
reviewed evidence, natural resolution dates, fixed human actor, danger confirmation,
multi-object atomicity, stale target/replay, and unchanged Thesis content.

- [ ] **Step 2: Run the new tests and confirm missing routes fail**

Run: `pytest -q 09_Automation/tests/test_web_decision_parity.py`

- [ ] **Step 3: Adapt existing prepare services to frozen write sets**

Use `prepare_forecast_draft`, `prepare_open_forecast`, `prepare_resolution_draft`,
`prepare_valuation_draft`, scenario services, `prepare_recommendation_draft`, and all
`prepare_*` lifecycle functions. Preserve every replacement in one repository plan.

- [ ] **Step 4: Add Decision forms and explicit preview/commit/result routes**

Implement the capability registry routes under `/decision/forecasts`,
`/decision/valuations`, `/decision/scenarios`, and `/decision/recommendations`, with
server-rendered summaries and fixed human confirmation for lifecycle transitions.

- [ ] **Step 5: Run focused/domain tests and static checks, then commit**

Run Forecast/Resolution/Valuation/Scenario/Recommendation suites with the new HTTP
tests, Ruff and mypy. Commit the complete Decision workbench slice.

### Task 4: Batch Lifecycle and F-027C Gate

**Files:**
- Create: `src/research_os/services/web_candidate_batch.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/services/product_capabilities.py`
- Modify: `src/research_os/services/release.py`
- Modify: `09_Automation/tests/test_m6_release.py`
- Create: `00_System/v0.3_F027C_Research_Workflow_Web_Parity_Verification_2026-08-13.md`
- Modify: `00_System/v0.3_Release_Gate_Verification_2026-08-13.md`
- Test: `09_Automation/tests/test_web_candidate_batch.py`
- Test: `09_Automation/tests/test_product_capabilities.py`

- [ ] **Step 1: Write failing batch and real-route parity tests**

Cover Candidate expire/purge/enrich preview/commit, bounded selection/scope, fixed
operational human identity, exact action counts, rollback/audit, and prove every F-027
registry route exists with the declared authority.

- [ ] **Step 2: Implement batch plans and Web routes**

Prepare immutable Candidate row/action sets before issuing the signed preview and
commit them with one Candidate DB transaction plus mutation audit. Add batch forms and
stable result pages without exposing raw SQL or Candidate payloads.

- [ ] **Step 3: Run focused F-027C integration and real loopback smoke**

Exercise Project/Action, Impact/Analysis, Decision, and Candidate batch through real
HTTP on a disposable repository. Assert replay 409, pending defaults, explicit human
transitions, audit rows, and byte-identical unrelated Thesis tree.

- [ ] **Step 4: Run the complete repository Gate once**

Run non-local pytest with branch coverage, Ruff check/format, mypy, compileall, strict
validation, global/PRJ-001/PRJ-002 index checks, and exact capability/security audits.

- [ ] **Step 5: Record evidence, refresh release provenance, and re-evaluate F-023**

Commit the final code/test candidate, write the dated F-027C verification record with
its exact 40-character commit and Gate results, then refresh release provenance in a
separate commit. Require exactly the five legitimate F-023 blockers and no others.
