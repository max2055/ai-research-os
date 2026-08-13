# F-027B Source and Evidence Web Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver complete website workflows for Source capture and maintenance, structured Event and Report creation, and human Review decisions without calling the product CLI.

**Architecture:** FastAPI routes accept bounded domain fields and prepare complete server-side write sets through existing ingestion, workflow, and review services. A reusable repository mutation coordinator freezes paths, before/after hashes, and content in a signed preview; commit revalidates versions, applies one `FileTransaction`, records redacted audit, and compensates filesystem writes if the cross-store audit step fails.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, SQLite mutation audit, Markdown repositories, pytest, Playwright/browser smoke, Ruff, mypy.

---

## Frozen Delivery Contract

- Top-level task count: 4.
- Resource budget: one implementation owner, no delegated agents, focused tests per task, one complete repository Gate after the final integrated candidate, and one dated release-provenance refresh after that Gate.
- Acceptance checklist:
  - Source URL and server-local-file registration use detail/form, preview, confirmation, commit, stable result, audit, replay rejection, and repository version checks.
  - Existing Source fetch, process, date confirmation, and asset verification are reachable from its website workbench; writes use the same mutation contract and verification is read-only.
  - Structured Event and Report forms call the existing typed workflow services and commit generated drafts as `review_status: pending`.
  - Review queue and approve/edit/reject flows are restricted to the fixed human Web identity; decisions retain domain approval guards and create a Review Decision record atomically.
  - No commit endpoint accepts actor, target path, generated Markdown, captured bytes, or normalized final content from the browser.
  - Host/Origin, CSRF, signed preview expiry, operation/target binding, one-use nonce, stale-version conflict, redacted audit, compensation, and refresh/replay behavior have focused HTTP and failure-injection tests.
  - A disposable loopback HTTP smoke exercises each primary workflow and proves Thesis and existing Review content are unchanged except for an explicitly reviewed test target.
  - Full repository quality, security, strict validation, index, and release evaluation Gates run once on the final candidate; F-023 returns exactly its five real-date/human blockers.
- Explicit non-scope: Project/Action, Entity/Ontology/Impact, Analysis/Forecast/Resolution/Valuation/Recommendation, Thesis proposal or confidence/conclusion changes, operations/scheduler/backup/recovery, CLI retirement, remote multi-user auth, and changes to research rules, taxonomy, or release blocker semantics.

### Task 1: Repository Mutation Coordinator

**Files:**
- Create: `src/research_os/services/web_repository_mutations.py`
- Modify: `src/research_os/services/mutation_audit.py`
- Test: `09_Automation/tests/test_web_repository_mutations.py`

- [ ] **Step 1: Write failing contract and failure-injection tests**

Cover create/replace write-set freezing, deterministic target version, exact before/after hashes, signed-preview payload round-trip, stale-file rejection, path confinement, audit redaction, one-use commit, and compensation after an injected audit failure.

- [ ] **Step 2: Run the focused test and confirm the missing coordinator fails**

Run: `pytest -q 09_Automation/tests/test_web_repository_mutations.py`

- [ ] **Step 3: Implement the smallest shared coordinator**

Define immutable `RepositoryWrite`, `RepositoryMutationPlan`, `prepare_repository_mutation`, `repository_target_version`, and `commit_repository_mutation`. Stage the frozen write set through `FileTransaction`; record only operation, actor, target IDs, hashes, status, and recovery-manifest path in SQLite. On post-publish failure, restore frozen originals or remove newly created files and emit a bounded redacted recovery manifest only if compensation itself cannot complete.

- [ ] **Step 4: Run coordinator tests, Ruff, and mypy for touched modules**

Run: `pytest -q 09_Automation/tests/test_web_repository_mutations.py && ruff check src/research_os/services/web_repository_mutations.py 09_Automation/tests/test_web_repository_mutations.py && mypy src/research_os/services/web_repository_mutations.py`

- [ ] **Step 5: Commit the shared mutation boundary**

Commit only the coordinator, audit extension, and focused tests.

### Task 2: Source Website Workbench

**Files:**
- Create: `src/research_os/services/web_source_workflows.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/services/product_capabilities.py`
- Test: `09_Automation/tests/test_web_source_parity.py`

- [ ] **Step 1: Write failing Source service and HTTP security tests**

Cover URL/local capture adapters, duplicate override, server-controlled local paths, preview content redaction, capture-once semantics, existing Source fetch, extraction, date override, read-only asset verification, malformed forms, hostile Origin, missing identity, CSRF failure, token replay, stale Source, and transaction rollback.

- [ ] **Step 2: Run the focused test and confirm the routes are absent**

Run: `pytest -q 09_Automation/tests/test_web_source_parity.py`

- [ ] **Step 3: Add typed Source workflow preparation adapters**

Convert bounded form values to existing `prepare_new_source_capture`, existing-Source capture, processing, and date-confirmation plans. Capture external content only during preview, freeze bytes and hashes server-side, and expose only metadata summaries to confirmation HTML.

- [ ] **Step 4: Add Source list/detail/forms and exact mutation routes**

Add `/sources`, `/sources/new`, `/sources/{source_id}`, and explicit `/preview`, `/commit`, and result routes for each Source write. Commit forms contain only CSRF and preview token. Add route/capability declarations and navigation.

- [ ] **Step 5: Run Source tests and static checks**

Run: `pytest -q 09_Automation/tests/test_web_source_parity.py 09_Automation/tests/test_m3_ingestion.py && ruff check src/research_os/services/web_source_workflows.py src/research_os/ui/app.py 09_Automation/tests/test_web_source_parity.py`

- [ ] **Step 6: Commit Source website parity**

Commit Source workflow, UI, registry, and tests together.

### Task 3: Structured Event and Report Website Creation

**Files:**
- Create: `src/research_os/services/web_research_drafts.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/services/product_capabilities.py`
- Test: `09_Automation/tests/test_web_research_drafts.py`

- [ ] **Step 1: Write failing typed-form, authority, and HTTP tests**

Cover complete Event facts/anchors/inferences/judgment/alternatives/unknowns/indicators and Report evidence selection/version/supersedes fields, unknown IDs, unprocessed Sources, unreviewed Evidence, duplicate fingerprints, pending status, CSRF/token/replay/stale conflict, and proof that no route writes Thesis files.

- [ ] **Step 2: Run the focused test and confirm the routes are absent**

Run: `pytest -q 09_Automation/tests/test_web_research_drafts.py`

- [ ] **Step 3: Build typed adapters over existing workflow services**

Parse repeated bounded form fields into `EventDraftSpec` and `ReportDraftSpec`, call `prepare_reviewable_event_draft` and `prepare_synthesized_report`, and return one-file repository mutation plans with server-generated IDs, paths, and Markdown.

- [ ] **Step 4: Add Event and Report forms, previews, commits, and results**

Expose `/evidence/events/new` and `/reports/new` plus explicit preview/commit/result routes. Show fact/inference/judgment separation, source anchors, contradicting evidence, unknowns, generated ID, and pending-review outcome without exposing raw generated Markdown.

- [ ] **Step 5: Run draft tests and static checks**

Run: `pytest -q 09_Automation/tests/test_web_research_drafts.py 09_Automation/tests/test_m4_workflow.py && ruff check src/research_os/services/web_research_drafts.py src/research_os/ui/app.py 09_Automation/tests/test_web_research_drafts.py`

- [ ] **Step 6: Commit Event and Report website parity**

Commit adapters, routes, registry changes, and focused tests.

### Task 4: Human Review Website and F-027B Gate

**Files:**
- Create: `src/research_os/services/web_review_mutations.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/services/product_capabilities.py`
- Modify: `00_System/v0.3_F027B_Source_Evidence_Web_Parity_Verification_2026-08-13.md`
- Modify: `00_System/v0.3_Release_Gate_Verification_2026-08-13.md`
- Test: `09_Automation/tests/test_web_review_parity.py`
- Test: `09_Automation/tests/test_web_only_parity.py`

- [ ] **Step 1: Write failing Review authority and atomicity tests**

Cover queue filters, one/many target preview, approve/edit/reject requirements, report/evidence approval guards, supersession writes, fixed reviewer identity, missing Web identity, forbidden automation identity, no browser-supplied reviewer/path/content, stale target, replay, and compensation/audit failure.

- [ ] **Step 2: Run the focused test and confirm the routes are absent**

Run: `pytest -q 09_Automation/tests/test_web_review_parity.py`

- [ ] **Step 3: Add Review plan adapter and website routes**

Call `review_queue` and `prepare_review`; freeze the Review Decision create plus every target/superseded-object replacement in one repository mutation plan. Bind reviewer to the fixed human Web identity and preserve all existing Thesis/Report approval guards.

- [ ] **Step 4: Update route parity and run focused integration tests**

Run: `pytest -q 09_Automation/tests/test_web_review_parity.py 09_Automation/tests/test_review_stage3.py 09_Automation/tests/test_web_only_parity.py`

- [ ] **Step 5: Run disposable loopback HTTP smoke**

Create Source, process it, create and review Event, create Report, and inspect audit/results through real HTTP. Assert replay is rejected, all generated objects begin pending, human approval is explicit, and unrelated Thesis/Review trees retain their pre-run digests.

- [ ] **Step 6: Run the complete repository Gate once**

Run the repository's canonical non-local pytest with branch coverage, Ruff check/format check, mypy, compileall, strict repository validation, and global index check. Record exact commands, counts, commit, and outcomes in the F-027B verification record.

- [ ] **Step 7: Commit implementation evidence, refresh release provenance, and re-evaluate F-023**

First commit the integrated F-027B code/tests/verification baseline. Then write that exact 40-character commit to the dated release Gate record and commit the provenance refresh separately. Run release evaluation and require exactly the five legitimate blockers: pilot completion, natural resolutions, cadence reviews, Known Limitations acknowledgement, and human release approval.

