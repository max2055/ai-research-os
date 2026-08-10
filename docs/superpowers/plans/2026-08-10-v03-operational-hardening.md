# v0.3 Operational Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every current AI Research OS work item that is not gated by real elapsed time, while keeping WP-530, WP-620, and F-024 visibly blocked and preserving all human-review boundaries.

**Architecture:** Keep Markdown authoritative and treat Candidate SQLite, generated indexes, benchmark fixtures, backup receipts, and health views as operational or derived state. Harden the shared Discovery transport, add disposable performance measurement, expose a versioned read-only release evaluator, run asset-independent checks in private hosted CI, and isolate remote encrypted backup behind a tested backend. Research corrections remain traceable pending drafts; no Agent creates a human decision.

**Tech Stack:** Python 3.12, stdlib `urllib`/`ssl`/`sqlite3`/`tarfile`/`subprocess`, Pydantic, FastAPI, pytest, Ruff, mypy, GitHub Actions, GitHub CLI, and `age`.

---

## File Map

- `src/research_os/adapters/discovery.py`: retry classification, redirect policy, telemetry, and host enforcement.
- `src/research_os/services/discovery.py`: one-run lifecycle and Candidate-side effects.
- `src/research_os/services/candidate_db.py`: existing discovery metrics persistence; schema changes only after measured need.
- `src/research_os/services/candidate_queue.py`: deterministic ordering and post-collapse pagination.
- `src/research_os/services/benchmark.py`: disposable 10k Candidate Queue fixture and measurement.
- `src/research_os/services/release.py`: backward-compatible v0.2 and explicit v0.3 readiness evaluation.
- `src/research_os/services/validation.py`: strict default and explicit metadata-only byte availability mode.
- `src/research_os/services/durable_backup.py`: snapshot, archive, encryption, receipt, verification, and restore orchestration.
- `src/research_os/adapters/backup_remote.py`: private GitHub Release backend.
- `src/research_os/services/cost_monitoring.py`: Decimal monthly cost state machine.
- `src/research_os/services/operations_health.py`: local and durable backup health, alerts, and cost integration.
- `src/research_os/services/impact_audit.py`: deterministic pending Assertion audit validation and rendering.
- `.github/workflows/ci.yml`: private hosted, metadata-only, asset-independent checks.
- `05_Research/Reviews/Impact_Assertion_Agent_Audit.{json,md}`: structured and rendered pending human-review packet.

### Task 1: Preserve and audit the 30 Job records

**Files:**
- Add unchanged: `05_Research/Operations/Jobs/JOB-20260809*-001-*.md` (the exact 30 currently untracked files in the main worktree)
- Create: `00_System/v0.3_Discovery_Job_Audit_2026-08-10.md`
- Create: `09_Automation/tests/test_operational_job_audit.py`
- Regenerate: `08_Indexes/Home_Dashboard.md`

- [ ] **Step 1: Write the failing batch-contract tests**

Create tests with fixed IDs and these assertions. Use
`validate_repository(ROOT)` to build `jobs_by_id`, select the fixed 30 IDs,
and use `collections.Counter` for the exact counts:

```python
EXPECTED_FAILED = {
    "JOB-20260809154712-001": "CHN-arxiv",
    "JOB-20260809154743-001": "CHN-arxiv-agents",
}

assert Counter(job.metadata["status"] for job in batch) == {
    "success": 28,
    "failed": 2,
}
assert Counter(job.metadata["job_name"] for job in batch) == {
    "discover": 28,
    "expire": 2,
}
assert {
    job.object_id: job.metadata["target"]
    for job in batch
    if job.metadata["status"] == "failed"
} == EXPECTED_FAILED
```

Use concrete fixture helpers rather than leaving ellipses in the implementation. The fixed failed run reconciliation is:

```text
JOB-20260809154712-001 -> RUN-5103a52bd05d4b1c -> CHN-arxiv
JOB-20260809154743-001 -> RUN-7aa75664f4d74282 -> CHN-arxiv-agents
```

- [ ] **Step 2: Run RED**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_operational_job_audit.py -q
```

Expected: fail because the 30 Job files and audit record are absent in the feature worktree.

- [ ] **Step 3: Copy the Job records byte-for-byte and reconcile run links read-only**

```bash
MAIN_REPO=/Users/max/Coding/57-AI-Research-OS
FEATURE_WT=/Users/max/Coding/57-AI-Research-OS/.worktrees/v03-operational-hardening
JOB_MANIFEST=$(mktemp)
git -C "$MAIN_REPO" ls-files --others --exclude-standard \
  '05_Research/Operations/Jobs/*.md' | sort > "$JOB_MANIFEST"
test "$(wc -l < "$JOB_MANIFEST" | tr -d ' ')" = 30
rsync -a --relative --files-from="$JOB_MANIFEST" "$MAIN_REPO/" "$FEATURE_WT/"
while IFS= read -r relative; do
  cmp -s "$MAIN_REPO/$relative" "$FEATURE_WT/$relative"
done < "$JOB_MANIFEST"
```

Query the main Candidate DB with SQLite read-only mode and verify every successful RUN ID, channel, status, and count. Do not stage or alter `09_Automation/operational/`.

- [ ] **Step 4: Write the audit without changing incident history**

The document must contain `Scope and method`, `Facts`, `Retained incidents`, `Candidate run reconciliation`, `Inference`, `Operational judgment`, and `Post-fix verification`. Record 30 total, 28 success, 2 failed; describe transient transport as an inference, not an independently proven root cause. State that failed Jobs remain failed and research authority is unchanged.

- [ ] **Step 5: Run GREEN and rebuild indexes**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_operational_job_audit.py \
  09_Automation/tests/test_schemas.py -q
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . index --apply
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . validate
```

Expected: tests pass; validation reports 0 errors and 0 warnings; Dashboard retains the failed Job entries.

- [ ] **Step 6: Commit in two reviewable units**

```bash
git add 05_Research/Operations/Jobs/JOB-20260809*-001-*.md
git commit -m "chore: preserve operational job evidence"
git add 00_System/v0.3_Discovery_Job_Audit_2026-08-10.md \
  09_Automation/tests/test_operational_job_audit.py 08_Indexes/Home_Dashboard.md
git commit -m "docs: audit retained discovery incidents"
```

### Task 2: Add bounded Discovery retries and redirect enforcement

**Files:**
- Modify: `src/research_os/adapters/discovery.py`
- Create: `09_Automation/tests/test_discovery_transport.py`
- Modify: `09_Automation/tests/test_discovery.py`

- [ ] **Step 1: Write failing transport tests**

Cover immediate success; TLS EOF/reset/timeout/temporary DNS retry; permanent DNS and certificate rejection; HTTP 408/425/429/500/502/503/504 retry; valid/capped `Retry-After`; three-attempt exhaustion; no retry for size/type/decode/parse/policy errors; safe error redaction; initial-host rejection; allowlisted redirect; cross-host redirect blocked before follow; and five-hop maximum.

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_discovery_transport.py -q
```

Expected: import or assertion failures because policy types and injected timing controls do not exist.

- [ ] **Step 2: Implement the explicit transport contract**

Use these public definitions:

```python
MAX_FETCH_ATTEMPTS = 3
MAX_DISCOVERY_REDIRECTS = 5
RETRIABLE_HTTP_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})

@dataclass
class FetchTelemetry:
    attempts: int = 0
    retries: int = 0
    http_errors: int = 0

class DiscoveryTransportError(ValueError):
    failure_class: str
    attempts: int

fetch_text(
    url: str,
    *,
    headers: dict[str, str],
    allowed_hosts: frozenset[str],
    max_bytes: int = DEFAULT_RESPONSE_LIMIT,
    timeout: float = 30.0,
    max_attempts: int = MAX_FETCH_ATTEMPTS,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    sleeper: Callable[[float], None] = time.sleep,
    jitter_source: Callable[[], float] = random.random,
    telemetry: FetchTelemetry | None = None,
) -> str
```

The implementation must unwrap `HTTPError` and `URLError.reason`, retry only the approved classes, honor non-negative seconds or HTTP-date `Retry-After`, and emit only a safe failure class plus attempt count. Implement an `HTTPRedirectHandler` that validates the target before `super().redirect_request()` and keeps hop state per attempt.

- [ ] **Step 3: Pass explicit transport allowlists from every adapter**

```text
RSS: the Channel allow_hosts set
GitHub: api.github.com
arXiv: export.arxiv.org and arxiv.org
SEC: data.sec.gov and www.sec.gov
```

Update injected test fetchers to accept the new keyword contract. Do not loosen result-link allowlists.

- [ ] **Step 4: Run GREEN and commit**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_discovery_transport.py \
  09_Automation/tests/test_discovery.py -q
git add src/research_os/adapters/discovery.py \
  09_Automation/tests/test_discovery_transport.py \
  09_Automation/tests/test_discovery.py
git commit -m "fix: add bounded discovery transport retries"
```

### Task 3: Finalize every Discovery run and persist retry metrics

**Files:**
- Modify: `src/research_os/services/discovery.py`
- Modify: `src/research_os/services/candidate_db.py`
- Modify: `src/research_os/services/jobs.py`
- Modify: `09_Automation/tests/test_discovery.py`
- Modify: `09_Automation/tests/test_pipeline_metrics.py`
- Modify: `09_Automation/tests/test_m5_dashboard_jobs.py`
- Modify: `00_System/v0.3_Discovery_Job_Audit_2026-08-10.md`

- [ ] **Step 1: Write lifecycle regression tests**

Add tests named:

```text
test_retry_success_inserts_candidate_once_and_records_one_run
test_post_fetch_insert_failure_finalizes_run_failed
test_parse_failure_finalizes_run_and_increments_parse_errors
test_successful_run_persists_retry_and_http_error_counts
test_failed_run_message_includes_run_id_safe_class_and_attempts
test_discover_job_with_internal_retry_writes_one_success_job
```

Run the three targeted files and confirm the run left `running` or counters remained zero for the expected reason.

- [ ] **Step 2: Extend terminal update without a schema migration**

Extend `finish_discovery_run` with optional `retries`, `http_errors`, and `parse_errors`. The existing v1 schema already contains these columns, so keep `SCHEMA_VERSION = 2`.

Wrap adapter build/discover, filter, insert, cluster, and enrichment in one terminal lifecycle. An applied run creates one row, then is finalized exactly once as `succeeded` or `failed`. Dry-run creates no DB, Candidate, or Job write. Internal attempts never create duplicate Candidates, runs, or Jobs.

- [ ] **Step 3: Run targeted tests and commit**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_discovery.py \
  09_Automation/tests/test_candidate_db.py \
  09_Automation/tests/test_pipeline_metrics.py \
  09_Automation/tests/test_m5_dashboard_jobs.py -q
git add src/research_os/services/discovery.py \
  src/research_os/services/candidate_db.py src/research_os/services/jobs.py \
  09_Automation/tests/test_discovery.py \
  09_Automation/tests/test_pipeline_metrics.py \
  09_Automation/tests/test_m5_dashboard_jobs.py
git commit -m "fix: finalize discovery runs with retry metrics"
```

- [ ] **Step 4: Perform a real read-only arXiv verification**

Hash the real Candidate DB and count Jobs before and after:

```bash
shasum -a 256 09_Automation/operational/candidates.db
find 05_Research/Operations/Jobs -maxdepth 1 -name '*.md' | wc -l
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os \
  --root . discover run --channel CHN-arxiv
```

Expected: exit 0 and identical DB hash/Job count. Record actual UTC time, exit code, candidate count, retry count, and before/after equality in the Job audit. If all three attempts fail, record the actual failure and keep this verification step open; never rewrite the historical failed Jobs.

- [ ] **Step 5: Commit the real verification evidence**

```bash
git add 00_System/v0.3_Discovery_Job_Audit_2026-08-10.md
git commit -m "docs: record discovery transport verification"
```

### Task 4: Add stable pagination and measure the 10k Candidate Queue SLO

**Files:**
- Modify: `src/research_os/services/candidate_queue.py`
- Modify: `src/research_os/services/benchmark.py`
- Modify: `src/research_os/cli.py`
- Modify: `src/research_os/runtime/product.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `09_Automation/tests/test_candidate_queue.py`
- Modify: `09_Automation/tests/test_m6_benchmark.py`
- Modify: `09_Automation/tests/test_m5_dashboard_jobs.py`
- Modify: `00_System/v0.3_Performance_Benchmark.md`
- Modify: `00_System/v0.3_Known_Limitations.md`
- Modify: `00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md`

- [ ] **Step 1: Write failing order and pagination tests**

Assert priority non-null first, score descending, discovery time descending, Candidate ID ascending. Assert `offset` pages are stable, non-overlapping, complete, and applied after entity/tier filtering and duplicate-cluster collapse. Reject negative offsets and non-positive limits. UI previous/next links must preserve filters.

- [ ] **Step 2: Implement minimal pagination**

Use this compatible signature:

```python
queue_rows(
    root: Path,
    db_path: Path | None = None,
    *,
    status: str | None = "new",
    channel_id: str | None = None,
    entity_id: str | None = None,
    tier: str | None = None,
    min_priority: float | None = None,
    limit: int = 50,
    offset: int = 0,
    show_dups: bool = False,
) -> list[dict[str, Any]]
```

Perform pagination after the filtered/collapsed deterministic list. Do not apply SQL `LIMIT` before collapse. Add CLI/UI offset plumbing and URL-encoded navigation.

- [ ] **Step 3: Write failing benchmark tests and implement the disposable fixture**

Use these result and entry points:

```python
@dataclass(frozen=True)
class CandidateQueueBenchmark:
    rows: int
    repeats: int
    warmups: int
    page_size: int
    offset: int
    fixture_distribution: dict[str, dict[str, int]]
    samples_seconds: tuple[float, ...]
    p95_seconds: float
    threshold_seconds: float
    query_plan: tuple[str, ...]
    db_size_bytes: int
    environment: dict[str, str]
    authoritative_writes: tuple[str, ...]
    real_candidate_store_unchanged: bool

benchmark_candidate_queue(
    root: Path,
    *,
    rows: int = 10_000,
    repeats: int = 7,
    warmups: int = 1,
    page_size: int = 200,
    offset: int = 200,
    max_seconds: float = 2.0,
) -> CandidateQueueBenchmark
```

Populate exactly 10,000 deterministic schema-current rows in a temporary DB, measure filters/order/pagination/render, use nearest-rank p95, record all samples/environment/distribution/query plan/DB size, and compare formal paths plus the real Candidate DB before/after. Preserve the existing repository-scale benchmark CLI and add `benchmark-candidates` as an additive JSON command.

- [ ] **Step 4: Run tests and commit behavior**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_candidate_queue.py \
  09_Automation/tests/test_m6_benchmark.py \
  09_Automation/tests/test_m5_dashboard_jobs.py -q
git add src/research_os/services/candidate_queue.py \
  src/research_os/services/benchmark.py src/research_os/cli.py \
  src/research_os/runtime/product.py src/research_os/ui/app.py \
  09_Automation/tests/test_candidate_queue.py \
  09_Automation/tests/test_m6_benchmark.py \
  09_Automation/tests/test_m5_dashboard_jobs.py
git commit -m "feat: benchmark stable candidate queue pagination"
```

- [ ] **Step 5: Run and record the real 10k measurement**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os \
  --root . benchmark-candidates --rows 10000 --repeats 7 --warmups 1 \
  --page-size 200 --offset 200 --max-seconds 2 \
  > /tmp/ai-research-os-candidate-10k.json
```

Record the actual seven samples and p95. Remove only the limitation that this path was unmeasured; retain single-user/local-only/100k/distributed limitations.

- [ ] **Step 6: Apply the conditional index gate**

If p95 is below 2 seconds, prove `candidate_db.py` has no index/schema diff and skip migration work. If two idle-machine runs both miss, profile first. Add a v3 index only when cProfile and `EXPLAIN QUERY PLAN` identify SQLite ordering or cluster lookup as the bottleneck; then add idempotent v3 migration tests and a data-preserving v3-to-v2 rollback. Never use the existing destructive rollback for v3-to-v2.

- [ ] **Step 7: Commit measurement facts**

```bash
git add 00_System/v0.3_Performance_Benchmark.md \
  00_System/v0.3_Known_Limitations.md \
  00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md \
  09_Automation/tests/test_m6_benchmark.py
git commit -m "docs: record 10k candidate queue benchmark"
```

### Task 5: Implement the blocked-aware v0.3 F-023 checker

**Files:**
- Modify: `src/research_os/services/release.py`
- Modify: `src/research_os/cli.py`
- Modify: `src/research_os/runtime/product.py`
- Modify: `09_Automation/tests/test_m6_release.py`

- [ ] **Step 1: Write RED tests for compatibility and v0.3 semantics**

Add tests for unchanged default 18-gate v0.2 output, exact 21 v0.3 keys, current WP-530/WP-620/F-024 blockers, malformed evidence as evaluation error, missing evidence as blocker, reviewer denylist, future date, no mutation, JSON, and exit codes 0/1/2.

- [ ] **Step 2: Add compatible release types and dispatch**

```python
@dataclass(frozen=True)
class ReleaseCheck:
    key: str
    passed: bool
    requirement: str
    observed: str
    evidence_paths: tuple[str, ...] = ()

class ReleaseEvaluationError(ValueError):
    pass

release_readiness_v03(root: Path, *, as_of: str | None = None) -> ReleaseReadiness

release_readiness_for(
    root: Path,
    *,
    version: str = "0.2",
    project_id: str = "PRJ-002",
    as_of: str | None = None,
) -> ReleaseReadiness
```

Keep `release_readiness()` and default text behavior unchanged. Implement `--version 0.3 --format json --as-of YYYY-MM-DD`. Parse approved Phase 3/4 acceptance and judgment JSON rather than stale packet headers. Human gates require a non-denylisted reviewer, valid decision, and decision date not after `as_of`.

- [ ] **Step 3: Use the 21 stable keys**

```text
evidence_universe.pilot_universe
evidence_universe.authoritative_references
evidence_universe.repository_validation
ingestion.pilot_completion
ingestion.no_silent_missed_runs
ingestion.channel_licenses
impact_analysis.impact_field_gate
impact_analysis.mode_field_gate
impact_analysis.counterevidence_divergence
decision.human_approved_forecasts
decision.natural_resolutions
decision.recommendation_pilot
decision.no_automated_trading
engineering.quality_suite
engineering.performance_slo
engineering.migration_recovery
engineering.recovery_boundaries
engineering.dashboard_security
human.cadence_reviews
human.known_limitations_read
human.release_approval
```

- [ ] **Step 4: Run GREEN and commit**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_m6_release.py -q
git add src/research_os/services/release.py src/research_os/cli.py \
  src/research_os/runtime/product.py 09_Automation/tests/test_m6_release.py
git commit -m "feat: add blocked-aware v0.3 release checker"
```

Expected on the real repository: default v0.2 remains ready; explicit v0.3 returns exit 1 and independently names WP-530, WP-620, and F-024. It creates no tag, release, or review record.

### Task 6: Add metadata-only private GitHub CI

**Files:**
- Modify: `src/research_os/services/validation.py`
- Modify: `src/research_os/cli.py`
- Modify: `src/research_os/runtime/product.py`
- Modify: `09_Automation/tests/test_research_os_core.py`
- Modify: `09_Automation/tests/test_cli.py`
- Create: `requirements/ci.txt`
- Create: `.github/workflows/ci.yml`
- Create: `09_Automation/tests/test_ci_workflows.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing validation-mode tests**

Define `ValidationMode = Literal["strict", "metadata-only"]`. Tests must prove strict remains default; metadata-only suppresses only unavailable raw bytes, including missing Source assets and byte-dependent citation checks, while retaining path escape, schema, references, governance, citation ownership, and index drift.

- [ ] **Step 2: Implement the explicit mode and CLI flags**

```python
validate_repository(
    root: Path,
    *,
    mode: ValidationMode = "strict",
) -> tuple[list[ResearchObject], list[Finding]]
```

Add `--metadata-only` to `validate` and `index --check`; do not allow it to weaken default strict calls from product services.

- [ ] **Step 3: Verify RED-to-GREEN**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_research_os_core.py \
  09_Automation/tests/test_cli.py -q
git add src/research_os/services/validation.py src/research_os/cli.py \
  src/research_os/runtime/product.py 09_Automation/tests/test_research_os_core.py \
  09_Automation/tests/test_cli.py
git commit -m "feat: add explicit metadata-only validation mode"
```

- [ ] **Step 4: Create a locked, read-only hosted workflow**

Generate a reviewed constraints file for `.[ui,dev]`. Pin third-party Actions to full commit SHAs. Workflow triggers are `pull_request`, `push` to `main`, and `workflow_dispatch`; permissions are `contents: read`; checkout uses `persist-credentials: false`; no cache, artifact, secret, raw asset, Candidate DB, backup, or provider key is used.

Run metadata-only validate and three index checks, asset-independent pytest, Ruff lint/format, mypy, a fixture-backed 10-route loopback Dashboard smoke, and a parser that expects v0.3 exit 1 with all three time/human blockers.

Register `local_integration` in `pyproject.toml` and apply it only to tests that
require the ignored real Source asset store or real Candidate DB. Prove the
selection in a temporary clean `git archive` checkout: `pytest -m
"not local_integration"` must pass there, while the final local gate still runs
the unfiltered complete suite against real assets.

- [ ] **Step 5: Add static security tests and commit**

```text
test_hosted_ci_is_read_only_metadata_only_and_has_no_secret_jobs
test_hosted_ci_asserts_expected_v03_blockers
test_workflow_never_uses_pull_request_target_cache_or_artifact_upload
test_action_references_are_full_sha_pins
```

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_ci_workflows.py -q
git add .github/workflows/ci.yml requirements/ci.txt pyproject.toml \
  09_Automation/tests/test_ci_workflows.py
git commit -m "ci: add metadata-only hosted checks"
```

### Task 7: Build durable encrypted backup and safe restore

**Files:**
- Create: `src/research_os/services/durable_backup.py`
- Create: `src/research_os/adapters/backup_remote.py`
- Modify: `src/research_os/services/backup.py`
- Modify: `src/research_os/runtime/product.py`
- Create: `09_Automation/tests/test_durable_backup.py`

- [ ] **Step 1: Write RED tests for archive, encryption, backend, and cleanup**

Cover Source inventory path escape/symlink rejection; tar traversal/link/device/duplicate rejection; SQLite backup API usage; no sensitive outer metadata; private-repo preflight; existing-asset refusal; partial upload not advancing `latest-success`; empty restore destination; ciphertext/archive/hash/schema/inventory verification; and plaintext cleanup on success and failure.

- [ ] **Step 2: Implement stable data types and backend protocol**

```python
BackupSet = Literal["candidate", "source_assets"]

@dataclass(frozen=True)
class RemoteAsset:
    name: str
    asset_id: str
    size_bytes: int

@dataclass(frozen=True)
class EncryptedAsset:
    backup_set: BackupSet
    name: str
    sha256: str
    size_bytes: int
    remote: RemoteAsset

class BackupBackend(Protocol):
    """Private immutable storage operations used by durable backup."""

    def preflight(self, asset_names: tuple[str, ...]) -> None:
        raise NotImplementedError

    def upload(self, path: Path, *, name: str) -> RemoteAsset:
        raise NotImplementedError

    def inspect(self, *, name: str) -> RemoteAsset:
        raise NotImplementedError

    def download(self, *, name: str, destination: Path) -> None:
        raise NotImplementedError

@dataclass(frozen=True)
class DurableBackupRequest:
    root: Path
    recipients: tuple[str, ...]
    backend: BackupBackend
    apply: bool

@dataclass(frozen=True)
class DurableBackupReceipt:
    backup_id: str
    created_at: str
    status: str
    sets: tuple[EncryptedAsset, ...]
    remote_repository: str
    remote_release: str
```

The production backend and fake test backend implement all four methods.

The GitHub backend uses fixed prerelease tag `research-os-durable-backups-v1`, verifies the repository is private, and never uses `--clobber`. Use subprocess argument lists, not a shell.

- [ ] **Step 3: Implement the transaction**

```text
preflight -> immutable Candidate snapshot and Source archive
-> plaintext integrity check -> age encryption -> ciphertext hash
-> upload -> remote metadata verification -> ignored receipt -> Job caller result
```

Outer manifests contain only backup ID, set, UTC creation time, ciphertext filename/hash/size, and remote identifier. The encrypted inner manifest owns Source IDs/paths/sizes/hashes and Candidate integrity data. Temporary directories are mode 0700 and always removed.

- [ ] **Step 4: Implement restore rejection and verification**

Restore only to an absent or empty disposable destination. Reject absolute paths, `..`, symlink/hardlink/device members, duplicates, live Candidate paths, and authoritative Source asset paths. Verify ciphertext hash before decrypting and every inner entry afterward.

- [ ] **Step 5: Run GREEN and commit**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_backup.py \
  09_Automation/tests/test_durable_backup.py -q
git add src/research_os/services/durable_backup.py \
  src/research_os/adapters/backup_remote.py src/research_os/services/backup.py \
  src/research_os/runtime/product.py 09_Automation/tests/test_durable_backup.py
git commit -m "feat: add age encrypted durable backup core"
```

### Task 8: Expose audited backup commands and prove private remote restore

**Files:**
- Modify: `src/research_os/cli.py`
- Modify: `src/research_os/services/jobs.py`
- Modify: `src/research_os/schemas/job.py`
- Modify: `09_Automation/tests/test_backup.py`
- Runtime-only ignored: `09_Automation/operational/backup.local.json`
- Runtime-only ignored: `09_Automation/operational/backups/durable/`

- [ ] **Step 1: Write failing CLI and Job tests**

Test dry-run preflight/no writes; apply success receipt and immutable Job; failure Job redaction; remote verify; non-empty/live restore refusal; identity and recipient never appearing in output or Job content.

- [ ] **Step 2: Add explicit commands**

```text
BACKUP_CONFIG=09_Automation/operational/backup.local.json
AGE_IDENTITY=/Users/max/.config/ai-research-os/backup/age-identity.txt
research-os backup durable create --config "$BACKUP_CONFIG"
research-os backup durable create --config "$BACKUP_CONFIG" --apply
BACKUP_ID=$(jq -r .backup_id \
  09_Automation/operational/backups/durable/latest-success.json)
research-os backup durable verify-remote --backup-id "$BACKUP_ID"
research-os backup durable restore --backup-id "$BACKUP_ID" \
  --identity "$AGE_IDENTITY" \
  --destination "09_Automation/operational/restores/$BACKUP_ID" --apply
```

Dry-run performs tool/private-repo/recipient/DB/inventory/name-collision preflight but creates no local or remote file. Add an approved durable Job name and use existing redaction; do not put config, recipient, identity, token, or query secrets in target/message.

- [ ] **Step 3: Run tests and commit**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_backup.py \
  09_Automation/tests/test_durable_backup.py \
  09_Automation/tests/test_m5_dashboard_jobs.py -q
git add src/research_os/cli.py src/research_os/services/jobs.py \
  src/research_os/schemas/job.py 09_Automation/tests/test_backup.py
git commit -m "feat: expose audited durable backup commands"
```

- [ ] **Step 4: Install/configure `age` outside Git and run real end-to-end backup**

Verify `gh auth status`, repository privacy, and `age`/`age-keygen`. Create or use a local identity under a permission-restricted ignored/operator directory; never print it. Run create `--apply`, remote verify, download, decrypt, and restore to a disposable ignored directory. Confirm Candidate `integrity_check`, schema/hash, and every Source asset hash. Record only backup ID, ciphertext hashes, remote identifiers, receipt path, restore counts, and command exit status.

Expected: private prerelease assets exist; restore passes; plaintext temp files are absent; `latest-success.json` points to the verified receipt. Do not create a v0.3 release or tag.

### Task 9: Add six-state cost monitoring and P1 durable backup alerts

**Files:**
- Create: `src/research_os/services/cost_monitoring.py`
- Modify: `src/research_os/services/operations_health.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/runtime/product.py`
- Create: `09_Automation/tests/test_cost_monitoring.py`
- Modify: `09_Automation/tests/test_m5_dashboard_jobs.py`

- [ ] **Step 1: Write RED tests for all states and alerts**

Test `unconfigured`, `no_data`, `ok`, `warning`, `exceeded`, and `invalid`; exact 80% and 100% boundaries; natural-month filtering; known/unknown/invalid counts; missing data not shown as zero; local versus durable backup; P1 for missing/failed/invalid/stale; no remote call during Dashboard render; no secret or raw budget value in HTML.

- [ ] **Step 2: Implement Decimal aggregation from `discovery_runs`**

```python
CostStatus = Literal[
    "unconfigured", "no_data", "ok", "warning", "exceeded", "invalid"
]

@dataclass(frozen=True)
class MonthlyCostReport:
    status: CostStatus
    period_start: str
    period_end: str
    currency: str
    known_total: Decimal | None
    budget: Decimal | None
    utilization: Decimal | None
    record_count: int
    unknown_record_count: int
    invalid_record_count: int

monthly_cost_report(
    db_path: Path,
    *,
    as_of: str | None = None,
    budget: str | None = None,
    currency: str = "USD",
) -> MonthlyCostReport
```

Read only current-month `discovery_runs.cost_estimate`. Missing values are unknown, not zero. Malformed, negative, or non-finite values and invalid/non-positive budgets produce `invalid`.

- [ ] **Step 3: Integrate local-only Health and UI**

Keep existing top-level local backup fields compatible and add durable detail plus structured alerts with stable `BKP_DURABLE_*` codes and priority `P1`. Normal snapshots read local receipts only.

- [ ] **Step 4: Run GREEN and commit**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_cost_monitoring.py \
  09_Automation/tests/test_m5_dashboard_jobs.py -q
git add src/research_os/services/cost_monitoring.py \
  src/research_os/services/operations_health.py src/research_os/ui/app.py \
  src/research_os/runtime/product.py 09_Automation/tests/test_cost_monitoring.py \
  09_Automation/tests/test_m5_dashboard_jobs.py
git commit -m "feat: add durable backup alerts and six-state cost health"
```

### Task 10: Fix future Impact proposal scope and build the audit validator

**Files:**
- Modify: `src/research_os/services/impact_proposal.py`
- Modify: `src/research_os/services/impact_draft.py`
- Modify: `09_Automation/tests/test_impact_proposal.py`
- Modify: `09_Automation/tests/test_impact_draft.py`
- Create: `src/research_os/schemas/impact_audit.py`
- Create: `src/research_os/services/impact_audit.py`
- Create: `09_Automation/audit_impact_assertions.py`
- Create: `09_Automation/tests/test_impact_agent_audit.py`

- [ ] **Step 1: Write RED scope propagation tests**

Assert direct proposals inherit sorted unique Event `project_ids` and materialized pending Assertions preserve them. Replace `_proposal_meta()` hard-coded empty project list with the proposal value.

- [ ] **Step 2: Run RED, implement minimal scope fix, and run GREEN**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_impact_proposal.py \
  09_Automation/tests/test_impact_draft.py -q
```

- [ ] **Step 3: Write RED audit-schema tests**

Use these stable literals and functions:

```python
AuditRecommendation = Literal[
    "ready_for_human_review", "edit_required", "reject_recommended"
]
AuditCheck = Literal["pass", "fail", "unknown", "not_applicable"]

@dataclass(frozen=True)
class ImpactAuditEntry:
    assertion_id: str
    path: str
    before_sha256: str
    after_sha256: str
    recommendation: AuditRecommendation
    rationale: str
    event: dict[str, Any]
    sources: tuple[dict[str, Any], ...]
    subject: dict[str, str]
    target: dict[str, str]
    declared_relation: dict[str, str]
    relevant_relations: tuple[dict[str, str], ...]
    rule_check: dict[str, Any]
    checks: dict[str, AuditCheck]
    issues: tuple[str, ...]
    changes: tuple[dict[str, Any], ...]
    preserved_note_fragments: tuple[str, ...]
    human_review_required: bool

@dataclass(frozen=True)
class ImpactAuditPacket:
    schema_version: int
    audit_id: str
    audit_date: str
    baseline_commit: str
    scope: dict[str, Any]
    guardrails: tuple[str, ...]
    summary: dict[str, int]
    assertions: tuple[ImpactAuditEntry, ...]
```

Implement these as strict Pydantic models in `schemas/impact_audit.py` while
preserving the field names and types above. Implement four concrete functions:
`load_audit_spec(path)` returns a
validated packet; `validate_audit_spec(root, packet)` returns validation error
strings; `render_audit_packet(packet)` returns deterministic Markdown; and
`check_rendered_packet(root, spec, markdown)` returns drift/error strings.

Tests must reject unknown recommendation and recursively reject `reviewer`, `decision`, or `reviewed_at`; require exactly the 22 real pending IMP paths; verify before/after hashes; preserve notes; enforce relation/rule map, weakest-link confidence, project scope, and reject recommendation for an Event whose substantive sections contain only unresolved markers or a Source without a verifiable asset.

- [ ] **Step 4: Implement deterministic validation and renderer**

Each JSON row contains Assertion path/hashes/recommendation/rationale, Event fields, complete Source provenance and anchors, subject/target, declared/relevant relations, rule check, the 20 audit checks, issue list, field changes with evidence basis, preserved note fragments, and `human_review_required: true`.

- [ ] **Step 5: Run GREEN and commit**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_impact_proposal.py \
  09_Automation/tests/test_impact_draft.py \
  09_Automation/tests/test_impact_agent_audit.py -q
git add src/research_os/services/impact_proposal.py \
  src/research_os/services/impact_draft.py src/research_os/schemas/impact_audit.py \
  src/research_os/services/impact_audit.py \
  09_Automation/audit_impact_assertions.py \
  09_Automation/tests/test_impact_proposal.py \
  09_Automation/tests/test_impact_draft.py \
  09_Automation/tests/test_impact_agent_audit.py
git commit -m "feat: validate pending impact assertion audits"
```

### Task 11: Correct and audit all 22 pending Impact Assertions

**Files:**
- Modify: the 22 `05_Research/Assertions/IMP-*.md` files dated 2026-08-07 through 2026-08-09
- Create: `05_Research/Reviews/Impact_Assertion_Agent_Audit.json`
- Create: `05_Research/Reviews/Impact_Assertion_Agent_Audit_Packet.md`
- Regenerate: `08_Indexes/Impact_Index.md`
- Regenerate: `08_Indexes/Projects/PRJ-001/Impact_Index.md`
- Regenerate: `08_Indexes/Projects/PRJ-002/Impact_Index.md`
- Regenerate: `08_Indexes/Home_Dashboard.md`

- [ ] **Step 1: Apply only traceable pending-draft corrections**

Set all 22 `project_ids` to the triggering Event scope (`PRJ-001`). Remove false `via ()` provenance and classify manual Assertions honestly. Align `valid_from` with Event date where supported. Cap confidence at the weakest Event/relation/source link; never increase it. Preserve manual Notes.

Specific evidence boundaries:

```text
reject_recommended: IMP-001, IMP-003, IMP-017, IMP-018
edit_required: IMP-002, IMP-004
```

For IMP-005/006/013-015 disclose TrendForce estimate/single-source and DRAM versus HBM limits. For IMP-010-012 use unknown magnitude/horizon and disclose competitor/customer ambiguity. For IMP-016 use uncertain direction and unknown magnitude. For IMP-019 separate Q1 capex fact from AWS-capacity inference. IMP-020-022 disclose legacy anchor gaps without inventing quotes. Other recommendations may be `ready_for_human_review` only after every material check passes; this is not approval.

- [ ] **Step 2: Build the structured packet and deterministic Markdown**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python \
  09_Automation/audit_impact_assertions.py --root . \
  --spec 05_Research/Reviews/Impact_Assertion_Agent_Audit.json --apply
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python \
  09_Automation/audit_impact_assertions.py --root . \
  --spec 05_Research/Reviews/Impact_Assertion_Agent_Audit.json --check
```

Expected: exact 22-row coverage; every Assertion remains `review_status: pending`; no human identity/decision/date is generated.

- [ ] **Step 3: Rebuild indexes and run research-boundary tests**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . index --apply
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . index --project PRJ-001 --apply
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . index --project PRJ-002 --apply
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_impact_agent_audit.py \
  09_Automation/tests/test_impact_assertion.py \
  09_Automation/tests/test_impact_draft.py \
  09_Automation/tests/test_impact_proposal.py \
  09_Automation/tests/test_impact_gate.py \
  09_Automation/tests/test_impact_path.py -q
git diff --exit-code 3a73972 -- 03_Theses 05_Research/Reviews/Decisions
```

Expected: PRJ-001 contains 22 pending Assertions; PRJ-002 contains none; no Thesis or Review Decision changed.

- [ ] **Step 4: Commit research drafts and audit evidence separately**

```bash
git add 05_Research/Assertions/IMP-*.md
git commit -m "fix: narrow pending impact assertions to reviewed evidence"
git add 05_Research/Reviews/Impact_Assertion_Agent_Audit.json \
  05_Research/Reviews/Impact_Assertion_Agent_Audit_Packet.md \
  08_Indexes/Impact_Index.md 08_Indexes/Projects/PRJ-001/Impact_Index.md \
  08_Indexes/Projects/PRJ-002/Impact_Index.md 08_Indexes/Home_Dashboard.md
git commit -m "docs: audit pending impact assertions"
```

### Task 12: Update operations docs and isolate Ruff formatting

**Files:**
- Modify: `00_System/Recovery_Runbook.md`
- Modify: `00_System/v0.3_User_Runbook.md`
- Modify: `00_System/v0.3_Known_Limitations.md`
- Modify: `09_Automation/launchd/RUNBOOK.md`
- Modify: `00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md`
- Modify: `README.md`
- Mechanically format: `src/` and `09_Automation/tests/`

- [ ] **Step 1: Add document contract tests before editing docs**

Extend release/backup tests to require exact commands, `age` install/preflight, private prerelease, recipient/identity separation, second-key custody, 24-hour RPO/P1 response, cost states, metadata-only CI boundary, strict local gate, and restore procedure. Assert WP-530, WP-620, and F-024 remain open and the earliest Forecast date remains 2026-10-31.

- [ ] **Step 2: Update docs and run the contract tests**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_backup.py \
  09_Automation/tests/test_m6_release.py -q
git add README.md 00_System/Recovery_Runbook.md \
  00_System/v0.3_User_Runbook.md 00_System/v0.3_Known_Limitations.md \
  00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md \
  09_Automation/launchd/RUNBOOK.md \
  09_Automation/tests/test_backup.py 09_Automation/tests/test_m6_release.py
git commit -m "docs: document hardened backup ci and release operations"
```

- [ ] **Step 3: Apply repository formatter as a mechanical-only change**

```bash
/Users/max/.venvs/ai-research-os/bin/python -m ruff format src 09_Automation/tests
git diff --check
git add src 09_Automation/tests
git diff --cached --stat
git commit -m "style: apply repository ruff formatting"
```

Before committing, verify the staged diff contains formatting only and does not include Markdown research objects, schema data, generated indexes, workflow YAML, or operational state.

- [ ] **Step 4: Verify the formatter commit**

```bash
/Users/max/.venvs/ai-research-os/bin/python -m ruff format --check src 09_Automation/tests
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m compileall -q src 09_Automation/tests
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest 09_Automation/tests -q
```

Expected: format check and compile pass; full suite passes with only documented skips.

### Task 13: Run full local gates, push, observe CI, and merge without data loss

**Files:**
- Create: `00_System/v0.3_Operational_Hardening_Verification_2026-08-10.md`
- Possibly update: benchmark, Job audit, and backup evidence with actual final command/run identifiers

- [ ] **Step 1: Run fresh local verification**

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . doctor
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . validate --strict
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . index --check
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . index --project PRJ-001 --check
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . index --project PRJ-002 --check
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest 09_Automation/tests -q
/Users/max/.venvs/ai-research-os/bin/python -m ruff check .
/Users/max/.venvs/ai-research-os/bin/python -m ruff format --check src 09_Automation/tests
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m mypy src/research_os
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m compileall -q src 09_Automation/tests
git diff --check
```

Expected: doctor has no unresolved runtime failure; validate is 0/0; all three index checks pass; tests/lint/format/mypy/compile/diff checks pass.

- [ ] **Step 2: Verify ten real Dashboard routes and release status**

Use FastAPI `TestClient` against the real root for ten documented GET paths and assert 200 plus GET-only route contracts. Then run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . release check
set +e
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os --root . \
  release check --version 0.3 --format json --as-of 2026-08-10 \
  > /tmp/v03-release.json
V03_EXIT=$?
set -e
test "$V03_EXIT" = 1
```

Parse JSON and assert v0.2 remains 18/18 Ready, v0.3 is evaluated but blocked, and WP-530/WP-620/F-024 are separate blockers.

- [ ] **Step 3: Write and commit the verification record**

Record actual commands, timestamps, counts, p95 samples, Discovery result, durable backup ID/restore result, branch commits, and remaining natural-time gates. Do not claim a v0.3 release.

```bash
git add 00_System/v0.3_Operational_Hardening_Verification_2026-08-10.md
git commit -m "docs: record operational hardening verification"
```

- [ ] **Step 4: Push the integration branch and require matching private CI**

```bash
git push -u origin codex/v03-operational-hardening
gh pr create --base main --head codex/v03-operational-hardening \
  --title "v0.3 operational hardening" \
  --body 'Implements the approved operational-hardening plan; v0.3 remains blocked by WP-530, WP-620, and F-024.'
RUN_ID=$(gh run list --workflow ci.yml \
  --branch codex/v03-operational-hardening --limit 1 --json databaseId \
  --jq '.[0].databaseId')
test -n "$RUN_ID"
gh run watch "$RUN_ID" --exit-status
```

Expected: opening or updating the same-repository PR triggers the new workflow,
and the exact branch SHA has a successful private Actions run. If CI fails,
preserve the run evidence, fix via RED/GREEN, rerun local gates, push, and wait
for a new matching success. Do not rely on `workflow_dispatch` before the new
workflow exists on the default branch.

- [ ] **Step 5: Preserve main-worktree state before merge**

Compare all 30 main-worktree Job files byte-for-byte with the committed branch
versions. In the main worktree, run strict validation and render its current
canonical Dashboard; require the existing `Home_Dashboard.md` to match that
render. Stage only those 30 Job files and that Dashboard and commit them as the
pre-existing operational evidence snapshot. Do not stage
`09_Automation/operational/` or any unrelated path. This turns the user's dirty
in-scope state into recoverable Git history before the branch merge, without a
reset, checkout, move, or deletion.

- [ ] **Step 6: Merge and verify the merged main state**

The user already selected local merge and authorized push. Merge
`codex/v03-operational-hardening` into `main` without a v0.3 tag. Confirm the
identical Job add/add changes and Dashboard merge resolve to the feature
branch's canonical final tree, while ignored runtime-only data remains present
with unchanged hashes. Rerun strict validate, three index checks, full pytest,
Ruff, mypy, and release checks on `main`. Push `main` and wait for the matching
push CI run.

- [ ] **Step 7: Final invariant audit**

```text
30 historical Jobs retained byte-for-byte; two remain failed
22 Impact Assertions remain pending; no reviewer/decision/reviewed_at created
no Thesis confidence increased
no raw asset, Candidate DB, key, identity, decrypted backup, or secret tracked
WP-530, WP-620, and F-024 remain blocked
no v0.3 tag or release exists
```

Only after every line has fresh evidence may the operational-hardening goal be marked complete.
