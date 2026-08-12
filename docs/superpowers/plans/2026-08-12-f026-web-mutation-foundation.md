# F-026 Web Mutation Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a secure, replay-resistant Candidate dismiss workflow entirely through the local website, with an exact preview-to-commit contract and atomic operational audit.

**Architecture:** Add a shared Mutation Gateway between FastAPI and the existing triage service. Fixed local identity and browser-session CSRF protection establish who may act, the Gateway binds an opaque ten-minute token to the exact preview and one process-local nonce, and the Candidate adapter commits the status change, domain action, and generic mutation audit in one SQLite transaction.

**Tech Stack:** Python 3.12+, FastAPI/Starlette responses, stdlib `hashlib`/`hmac`/`secrets`, SQLite, unittest/pytest, Ruff, mypy.

---

## Frozen Delivery Contract

- Top-level task count: 6.
- Resource budget: one local process, one Candidate workflow, focused tests after each task, and one complete repository Gate against the final integration candidate.
- Non-scope: Candidate promote/restore/bulk edit; Review approval; Thesis or confidence mutation; login/multi-user/remote access; persistent command queue; F-027/F-028 parity; physical CLI removal; research rule, taxonomy, object schema, or F-023 21-check contract changes.
- Worktree: `/Users/max/Coding/57-AI-Research-OS/.worktrees/f026-web-mutation` on `codex/f026-web-mutation`.
- Raw source assets remain ignored and untouched. Focused fixture tests run in the worktree; final local-integration and repository Gates run with the main workspace's existing ignored assets available read-only.

## File Responsibility Map

- Create `src/research_os/services/mutation_audit.py`: mutation-audit schema, redacted event model, and connection-scoped inserts.
- Create `src/research_os/services/web_identity.py`: ignored local identity config plus opaque browser-session and CSRF lifecycle.
- Create `src/research_os/services/mutation_gateway.py`: canonical preview model, signed opaque token, nonce state machine, validation, and retry transitions.
- Modify `src/research_os/services/candidate_db.py`: schema v3 migration, v3-to-v2 rollback, and canonical Candidate version digest.
- Modify `src/research_os/services/triage.py`: connection-scoped dismiss primitive so the Web adapter can share one transaction.
- Modify `src/research_os/ui/app.py`: security guard, Candidate adapter, preview/confirm/result routes, and server-rendered forms.
- Modify `src/research_os/ui/styles.css`: compact form, confirmation, status, and responsive action styling.
- Create `09_Automation/tests/test_web_mutation.py`: Gateway, HTTP security, replay, stale-target, escaping, and transaction tests.
- Modify `09_Automation/tests/test_candidate_db.py`: schema v3, preservation, rollback, and version digest tests.
- Modify `09_Automation/tests/test_triage.py`: externally managed transaction behavior and rollback tests.
- Modify `09_Automation/tests/test_m5_dashboard_jobs.py`: intentional Candidate mutation route contract while all other research routes remain GET-only.
- Modify `09_Automation/tests/test_m6_security.py`: updated exact route allowlist and mutation-boundary security assertions.
- Modify `09_Automation/tests/test_backup.py`, `09_Automation/tests/test_m6_release.py`, and operational evidence parsers only where schema v3 invalidates a literal v2 expectation.
- Modify `src/research_os/services/release.py`: require the newly measured Candidate schema version without weakening performance evidence parsing.
- Modify `00_System/v0.3_Performance_Benchmark.md`, `00_System/v0.3_Recovery_Drill.md`, and the final dated verification record with newly executed evidence; never edit old measured values speculatively.
- Modify `README.md`, `00_System/v0.3_User_Runbook.md`, `00_System/v0.3_Known_Limitations.md`, `00_System/v0.3_AI_Industry_Intelligence_OS/07_Phase_6_Productization_and_Scale.md`, and `00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md` to describe the delivered Web slice and remaining non-scope. These files have newer uncommitted governance edits in the main workspace; integrate with those edits after implementation instead of replacing them from the worktree baseline.

### Task 1: Candidate Schema v3 and Redacted Mutation Audit

**Files:**
- Create: `src/research_os/services/mutation_audit.py`
- Modify: `src/research_os/services/candidate_db.py`
- Test: `09_Automation/tests/test_candidate_db.py`

- [ ] **Step 1: Write failing migration, rollback, preservation, and digest tests**

Add tests that create a v2 database, seed a Candidate and action, migrate to v3, insert an audit event, and prove v3-to-v2 drops only `mutation_audit`. Also prove every Candidate column contributes to the version digest.

```python
def test_v3_migration_preserves_candidate_and_action_and_rolls_back_to_v2(self) -> None:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "candidates.db"
        connection = sqlite3.connect(path)
        try:
            connection.executescript(candidate_db._SCHEMA_V1)
            connection.executescript(candidate_db._SCHEMA_V2)
            connection.execute("PRAGMA user_version = 2")
            connection.commit()
        finally:
            connection.close()
        self._seed_candidate_and_action(path)
        candidate_db.apply_migrations(path)
        self.assertEqual(3, candidate_db.current_version(path))
        connection = sqlite3.connect(path)
        try:
            connection.execute(
                "INSERT INTO mutation_audit (event_id, mutation_id, event_status, "
                "operation, actor, target_type, target_id, target_version, "
                "input_digest, issued_at, event_at, expires_at, reason_code, "
                "domain_action_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("MA-1", "MUT-1", "previewed", "candidate.dismiss", "max",
                 "candidate", "CND-x", "a" * 64, "b" * 64,
                 "2026-08-12T00:00:00Z", "2026-08-12T00:00:00Z",
                 "2026-08-12T00:10:00Z", None, None),
            )
            connection.commit()
        finally:
            connection.close()
        candidate_db.rollback_migrations(path, to_version=2)
        self.assertEqual(2, candidate_db.current_version(path))
        connection = sqlite3.connect(path)
        try:
            self.assertEqual("dismiss", connection.execute(
                "SELECT action FROM candidate_actions WHERE action_id = 'CA-1'"
            ).fetchone()[0])
            self.assertIsNotNone(connection.execute(
                "SELECT candidate_id FROM candidates WHERE candidate_id = 'CND-x'"
            ).fetchone())
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("SELECT * FROM mutation_audit").fetchall()
        finally:
            connection.close()

def test_candidate_version_changes_for_any_row_change(self) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = self._prepared_root(temp)
        before = candidate_db.candidate_version(root, "CND-x")
        connection = sqlite3.connect(candidate_db.candidate_db_path(root))
        try:
            connection.execute(
                "UPDATE candidates SET snippet = ? WHERE candidate_id = ?",
                ("changed", "CND-x"),
            )
            connection.commit()
        finally:
            connection.close()
        self.assertNotEqual(before, candidate_db.candidate_version(root, "CND-x"))
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_candidate_db.py -q
```

Expected: FAIL because `SCHEMA_VERSION` is 2, `mutation_audit` does not exist, v3-to-v2 rollback is destructive, and `candidate_version` is undefined.

- [ ] **Step 3: Add the audit model and connection-scoped insert**

Create `mutation_audit.py` with bounded, redacted fields and no token/session/secret fields.

```python
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from research_os.services.mutation_gateway import MutationPreview

MUTATION_AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS mutation_audit (
    event_id TEXT PRIMARY KEY,
    mutation_id TEXT NOT NULL,
    event_status TEXT NOT NULL CHECK (
        event_status IN ('previewed', 'committed', 'rejected', 'expired')
    ),
    operation TEXT NOT NULL,
    actor TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_version TEXT NOT NULL,
    input_digest TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    event_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    reason_code TEXT,
    domain_action_id TEXT
);
CREATE INDEX IF NOT EXISTS mutation_audit_mutation_idx
    ON mutation_audit(mutation_id, event_at);
CREATE INDEX IF NOT EXISTS mutation_audit_target_idx
    ON mutation_audit(target_type, target_id, event_at);
"""

@dataclass(frozen=True)
class MutationAuditEvent:
    mutation_id: str
    event_status: str
    operation: str
    actor: str
    target_type: str
    target_id: str
    target_version: str
    input_digest: str
    issued_at: str
    event_at: str
    expires_at: str
    reason_code: str | None = None
    domain_action_id: str | None = None

    @classmethod
    def from_preview(
        cls,
        preview: MutationPreview,
        *,
        event_status: str,
        event_at: str,
        reason_code: str | None = None,
        domain_action_id: str | None = None,
    ) -> MutationAuditEvent:
        return cls(
            mutation_id=preview.mutation_id,
            event_status=event_status,
            operation=preview.operation,
            actor=preview.actor,
            target_type=preview.target_type,
            target_id=preview.target_id,
            target_version=preview.target_version,
            input_digest=normalized_input_digest(preview.normalized_input),
            issued_at=preview.issued_at_iso,
            event_at=event_at,
            expires_at=preview.expires_at_iso,
            reason_code=reason_code,
            domain_action_id=domain_action_id,
        )

def normalized_input_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def record_mutation_event(
    connection: sqlite3.Connection, event: MutationAuditEvent
) -> str:
    event_id = f"MA-{uuid.uuid4().hex[:16]}"
    connection.execute(
        "INSERT INTO mutation_audit (event_id, mutation_id, event_status, "
        "operation, actor, target_type, target_id, target_version, input_digest, "
        "issued_at, event_at, expires_at, reason_code, domain_action_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (event_id, event.mutation_id, event.event_status, event.operation,
         event.actor, event.target_type, event.target_id, event.target_version,
         event.input_digest, event.issued_at, event.event_at, event.expires_at,
         event.reason_code, event.domain_action_id),
    )
    return event_id
```

- [ ] **Step 4: Implement schema v3, selective rollback, and canonical Candidate digest**

Set `SCHEMA_VERSION = 3`, apply `MUTATION_AUDIT_SCHEMA` only when upgrading from v2, and branch rollback behavior so v3-to-v2 preserves all earlier tables. Serialize the complete SQLite row by sorted column name and JSON-normalized values.

```python
def candidate_version_on_connection(
    connection: sqlite3.Connection, candidate_id: str
) -> str:
    connection.row_factory = sqlite3.Row
    row = connection.execute(
        "SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown candidate {candidate_id}")
    canonical = json.dumps(
        {key: row[key] for key in sorted(row.keys())},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

def candidate_version(root: Path, candidate_id: str) -> str:
    path = candidate_db_path(root.resolve())
    if not path.exists():
        raise ValueError(f"unknown candidate {candidate_id}")
    connection = _connect(path)
    try:
        return candidate_version_on_connection(connection, candidate_id)
    finally:
        connection.close()
```

For rollback, execute this branch before the existing destructive v0 rollback:

```python
if version == 3 and to_version == 2:
    connection.execute("DROP TABLE IF EXISTS mutation_audit")
    connection.execute("PRAGMA user_version = 2")
    connection.commit()
    return
```

- [ ] **Step 5: Run focused tests and commit**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_candidate_db.py -q
/Users/max/.venvs/ai-research-os/bin/python -m ruff check \
  src/research_os/services/candidate_db.py \
  src/research_os/services/mutation_audit.py \
  09_Automation/tests/test_candidate_db.py
```

Expected: all Candidate DB tests pass and Ruff reports no errors.

```bash
git add src/research_os/services/candidate_db.py \
  src/research_os/services/mutation_audit.py \
  09_Automation/tests/test_candidate_db.py
git commit -m "feat(v0.3): add mutation audit schema"
```

### Task 2: Fixed Web Identity, Browser Session, and CSRF

**Files:**
- Create: `src/research_os/services/web_identity.py`
- Test: `09_Automation/tests/test_web_mutation.py`

- [ ] **Step 1: Write failing config and browser-session tests**

```python
class WebIdentityTests(unittest.TestCase):
    def test_identity_requires_private_ignored_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "00_System" / "web.local.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "researcher_id": "max",
                "mutation_signing_secret": "s" * 64,
            }), encoding="utf-8")
            path.chmod(0o600)
            self.assertEqual("max", load_web_identity(root).researcher_id)
            path.chmod(0o644)
            self.assertIsNone(load_web_identity(root))

    def test_session_csrf_is_bound_expires_and_contains_no_identity(self) -> None:
        now = datetime(2026, 8, 12, tzinfo=UTC)
        sessions = BrowserSessionRegistry(now=lambda: now)
        session_id, csrf = sessions.issue()
        self.assertTrue(sessions.validate(session_id, csrf))
        self.assertFalse(sessions.validate(session_id, "wrong"))
        self.assertNotIn("max", session_id + csrf)
        sessions.clear()
        self.assertFalse(sessions.validate(session_id, csrf))
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_web_mutation.py -q
```

Expected: FAIL because `web_identity` and its registry do not exist.

- [ ] **Step 3: Implement private config loading and session-bound CSRF**

Use `path.stat().st_mode & 0o077 == 0` on POSIX, reject malformed JSON, unknown types, IDs outside 1-128 characters, and signing secrets shorter than 32 characters. Do not raise during app creation; return `None` so GET routes stay available.

```python
@dataclass(frozen=True)
class WebIdentity:
    researcher_id: str
    mutation_signing_secret: bytes

def load_web_identity(root: Path) -> WebIdentity | None:
    path = root.resolve() / "00_System" / "web.local.json"
    try:
        if os.name == "posix" and path.stat().st_mode & 0o077:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        researcher_id = value["researcher_id"].strip()
        secret = value["mutation_signing_secret"]
        if not 1 <= len(researcher_id) <= 128 or len(secret) < 32:
            return None
        return WebIdentity(researcher_id, secret.encode("utf-8"))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
```

Implement a locked in-memory mapping from random session IDs to `(csrf_digest, expires_at)`. Compare CSRF digests with `hmac.compare_digest`; never put identity or secrets in either random value.

- [ ] **Step 4: Run focused tests and commit**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_web_mutation.py -q
/Users/max/.venvs/ai-research-os/bin/python -m ruff check \
  src/research_os/services/web_identity.py \
  09_Automation/tests/test_web_mutation.py
```

Expected: identity/session tests pass; later Gateway/HTTP tests may still fail because their production modules and routes are not present.

```bash
git add src/research_os/services/web_identity.py \
  09_Automation/tests/test_web_mutation.py
git commit -m "feat(v0.3): add local web mutation identity"
```

### Task 3: Signed Preview Token and Nonce State Machine

**Files:**
- Create: `src/research_os/services/mutation_gateway.py`
- Modify: `09_Automation/tests/test_web_mutation.py`

- [ ] **Step 1: Write failing canonical preview and lifecycle tests**

Cover exact payload binding, tampering, actor and operation mismatch, expiry, process restart, replay, concurrent `committing`, stale target, and transaction retry.

```python
def test_gateway_binds_preview_and_consumes_success_once(self) -> None:
    gateway = MutationGateway(b"s" * 64, now=self.clock)
    grant = gateway.issue(MutationPreviewInput(
        operation="candidate.dismiss", actor="max", target_type="candidate",
        target_id="CND-1", target_version="a" * 64,
        normalized_input={"reason": "out of scope"},
        summary={"status_before": "new", "status_after": "dismissed"},
    ))
    result = gateway.commit(
        grant.token,
        actor="max",
        operation="candidate.dismiss",
        current_target_version=lambda _: "a" * 64,
        execute=lambda preview: {"action_id": "CA-1"},
    )
    self.assertEqual("CA-1", result["action_id"])
    with self.assertRaises(MutationConflict):
        gateway.commit(grant.token, actor="max", operation="candidate.dismiss",
                       current_target_version=lambda _: "a" * 64,
                       execute=lambda _: {})

def test_transaction_failure_restores_only_unchanged_unexpired_nonce(self) -> None:
    gateway, grant = self._issued_gateway()
    with self.assertRaises(TransactionError):
        gateway.commit(
            grant.token, actor="max", operation="candidate.dismiss",
            current_target_version=lambda _: "a" * 64,
            execute=lambda _: (_ for _ in ()).throw(TransactionError("locked")),
        )
    self.assertEqual("issued", gateway.nonce_state(grant.preview.nonce))
```

- [ ] **Step 2: Run lifecycle tests and verify RED**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_web_mutation.py -q
```

Expected: FAIL because `MutationGateway` and its contracts are undefined.

- [ ] **Step 3: Implement opaque token issuance and validation**

Define immutable `MutationPreviewInput`, `MutationPreview`, and `PreviewGrant` dataclasses. Normalize strings before creating the preview, use UTC ISO timestamps, and canonicalize with sorted compact JSON. The browser token contains only a random nonce and an HMAC; the registry stores the preview and signature, never the raw token.

```python
def _token(nonce: str, signature: bytes) -> str:
    packed = nonce.encode("ascii") + b"." + signature
    return base64.urlsafe_b64encode(packed).decode("ascii").rstrip("=")

def _signature(secret: bytes, preview: MutationPreview) -> bytes:
    return hmac.digest(secret, preview.canonical_bytes(), "sha256")

class MutationGateway:
    def issue(self, value: MutationPreviewInput) -> PreviewGrant:
        now = self._now()
        preview = MutationPreview.from_input(
            value,
            mutation_id=f"MUT-{uuid.uuid4().hex[:16]}",
            nonce=secrets.token_urlsafe(24),
            issued_at=now,
            expires_at=now + self._ttl,
        )
        signature = _signature(self._secret, preview)
        with self._lock:
            self._nonces[preview.nonce] = _NonceRecord(
                preview=preview, signature=signature, state="issued"
            )
        return PreviewGrant(preview=preview, token=_token(preview.nonce, signature))
```

- [ ] **Step 4: Implement locked commit transitions and explicit failures**

Use `MutationForbidden` for bad signature/actor/operation (`403`), `MutationConflict` for missing/expired/consumed/in-flight/stale (`409`), and let `TransactionError` propagate (`500`). Under the lock, validate and change `issued -> committing`; after execute succeeds mark `consumed`. On `TransactionError`, recompute time and target version and restore `issued` only while both remain valid; otherwise consume the nonce.

```python
try:
    result = execute(record.preview)
except TransactionError:
    with self._lock:
        current = self._nonces.get(nonce)
        retryable = (
            current is record
            and self._now() < record.preview.expires_at
            and current_target_version(record.preview.target_id)
            == record.preview.target_version
        )
        record.state = "issued" if retryable else "consumed"
    raise
else:
    with self._lock:
        record.state = "consumed"
    return result
```

- [ ] **Step 5: Run focused tests, type checks, and commit**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_web_mutation.py -q
/Users/max/.venvs/ai-research-os/bin/python -m ruff check \
  src/research_os/services/mutation_gateway.py \
  09_Automation/tests/test_web_mutation.py
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m mypy \
  src/research_os/services/mutation_gateway.py
```

Expected: Gateway tests pass, Ruff and mypy report success.

```bash
git add src/research_os/services/mutation_gateway.py \
  09_Automation/tests/test_web_mutation.py
git commit -m "feat(v0.3): add signed mutation preview gateway"
```

### Task 4: Atomic Candidate Dismiss Adapter

**Files:**
- Modify: `src/research_os/services/triage.py`
- Modify: `src/research_os/services/mutation_audit.py`
- Modify: `src/research_os/ui/app.py`
- Modify: `09_Automation/tests/test_triage.py`
- Modify: `09_Automation/tests/test_web_mutation.py`

- [ ] **Step 1: Write failing connection and three-write atomicity tests**

```python
def test_dismiss_can_join_caller_transaction(self) -> None:
    root = self._root_with_candidate()
    connection = sqlite3.connect(candidate_db.candidate_db_path(root))
    try:
        connection.execute("BEGIN IMMEDIATE")
        result = dismiss_candidate(
            root, "CND-0000", actor="max", reason="noise", apply=True,
            connection=connection,
        )
        connection.rollback()
    finally:
        connection.close()
    self.assertEqual("new", self._status(root, "CND-0000"))
    self.assertIn("action_id", result)

def test_commit_audit_failure_rolls_back_candidate_and_action(self) -> None:
    client, root, token, csrf = self._previewed_client()
    with patch("research_os.ui.app.record_mutation_event",
               side_effect=sqlite3.OperationalError("injected")):
        response = client.post(
            "/pipeline/queue/CND-1/dismiss/commit",
            data={"preview_token": token, "csrf_token": csrf},
            headers={"Origin": "http://testserver"},
        )
    self.assertEqual(500, response.status_code)
    self.assertEqual("new", self._candidate_status(root))
    self.assertEqual(0, self._count(root, "candidate_actions"))
    self.assertEqual(0, self._audit_count(root, "committed"))
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_triage.py \
  09_Automation/tests/test_web_mutation.py -q
```

Expected: FAIL because `dismiss_candidate` cannot accept a caller connection and the Candidate mutation adapter does not exist.

- [ ] **Step 3: Refactor dismiss without changing CLI behavior**

Add optional keyword-only `connection: sqlite3.Connection | None = None`. When absent, preserve the current open/begin/commit/rollback/close behavior. When present, perform validation, update, and `_record_action` on that connection but leave transaction ownership to the caller. Add a compare-and-set status predicate so a target changed after preview cannot be overwritten.

```python
cursor = active.execute(
    "UPDATE candidates SET status = 'dismissed' "
    "WHERE candidate_id = ? AND status = ?",
    (candidate_id, status),
)
if cursor.rowcount != 1:
    raise ValueError(f"candidate {candidate_id} changed during dismiss")
```

- [ ] **Step 4: Add the Candidate commit adapter with one SQLite transaction**

In `app.py`, add a private adapter used only by the Gateway. It recomputes the target version after `BEGIN IMMEDIATE`, calls connection-scoped triage, appends `committed`, commits once, and rolls everything back on any exception.

```python
def _commit_candidate_dismiss(root: Path, preview: MutationPreview) -> dict[str, str]:
    db_path = candidate_db.candidate_db_path(root)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        current = candidate_db.candidate_version_on_connection(
            connection, preview.target_id
        )
        if current != preview.target_version:
            raise MutationConflict("target_changed", preview)
        result = dismiss_candidate(
            root,
            preview.target_id,
            actor=preview.actor,
            reason=str(preview.normalized_input["reason"]),
            apply=True,
            connection=connection,
        )
        audit_id = record_mutation_event(
            connection,
            MutationAuditEvent.from_preview(
                preview,
                event_status="committed",
                event_at=_utc_now(),
                domain_action_id=str(result["action_id"]),
            ),
        )
        connection.commit()
        return {"action_id": str(result["action_id"]), "audit_id": audit_id,
                "mutation_id": preview.mutation_id}
    except sqlite3.Error as exc:
        connection.rollback()
        raise TransactionError(f"candidate Web mutation failed: {exc}") from exc
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
```

- [ ] **Step 5: Run transaction tests and commit**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_triage.py \
  09_Automation/tests/test_web_mutation.py -q
```

Expected: all service and transaction-failure injection tests pass; preview audit remains present while no false committed event survives rollback.

```bash
git add src/research_os/services/triage.py \
  src/research_os/services/mutation_audit.py \
  src/research_os/ui/app.py \
  09_Automation/tests/test_triage.py \
  09_Automation/tests/test_web_mutation.py
git commit -m "feat(v0.3): commit candidate dismiss atomically"
```

### Task 5: Candidate Preview, Confirmation, and Result Web Flow

**Files:**
- Modify: `src/research_os/ui/app.py`
- Modify: `src/research_os/ui/styles.css`
- Modify: `09_Automation/tests/test_web_mutation.py`
- Modify: `09_Automation/tests/test_m5_dashboard_jobs.py`
- Modify: `09_Automation/tests/test_m6_security.py`

- [ ] **Step 1: Write failing end-to-end and security tests**

Cover GET behavior without config, secure cookie attributes, loopback Host, same-origin Origin, missing/wrong session and CSRF, no business write on preview, escaped confirmation, hidden-field contract, `422` reason validation, `409` status/stale/replay/restart, `403` tamper, `503` missing identity, `303` success, and refresh-safe GET result.

```python
def test_candidate_dismiss_preview_commit_and_refresh(self) -> None:
    client, root = self._configured_client()
    detail = client.get("/pipeline/queue/CND-1")
    csrf = self._hidden(detail.text, "csrf_token")
    preview = client.post(
        "/pipeline/queue/CND-1/dismiss/preview",
        data={"reason": "out of scope", "csrf_token": csrf},
        headers={"Origin": "http://testserver"},
    )
    self.assertEqual(200, preview.status_code)
    self.assertEqual("new", self._candidate_status(root))
    self.assertEqual(0, self._count(root, "candidate_actions"))
    self.assertEqual(1, self._audit_count(root, "previewed"))
    self.assertNotRegex(preview.text, r'name="(?:actor|target_id|reason)"')
    token = self._hidden(preview.text, "preview_token")
    csrf = self._hidden(preview.text, "csrf_token")
    committed = client.post(
        "/pipeline/queue/CND-1/dismiss/commit",
        data={"preview_token": token, "csrf_token": csrf},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )
    self.assertEqual(303, committed.status_code)
    result = client.get(committed.headers["location"])
    refreshed = client.get(committed.headers["location"])
    self.assertEqual(200, result.status_code)
    self.assertEqual(result.text, refreshed.text)
    self.assertEqual("dismissed", self._candidate_status(root))
    self.assertEqual(1, self._count(root, "candidate_actions"))
    self.assertEqual(1, self._audit_count(root, "committed"))
```

- [ ] **Step 2: Run HTTP tests and verify RED**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_web_mutation.py \
  09_Automation/tests/test_m5_dashboard_jobs.py \
  09_Automation/tests/test_m6_security.py -q
```

Expected: new Web tests fail because routes/forms are absent, and old read-only route allowlists fail once the intended POST routes are introduced.

- [ ] **Step 3: Add browser security helpers and session issuance**

At `create_app`, construct one `BrowserSessionRegistry`, load identity per mutation request, and construct a Gateway only when identity is valid. GET Candidate detail issues or reuses a session and sets:

```python
response.set_cookie(
    "research_os_session",
    session_id,
    httponly=True,
    samesite="strict",
    secure=request.url.scheme == "https",
    max_age=3600,
    path="/",
)
```

For both POST routes require loopback Host (`localhost`, `127.0.0.1`, `[::1]`, and TestClient's `testserver` only in tests), exact `Origin == f"{request.url.scheme}://{request.headers['host']}"`, an existing cookie, and session-bound form CSRF. Return the same generic `403` body for any failure.

- [ ] **Step 4: Add Candidate forms and three routes**

Use `Request` plus `await request.form()` so commit accepts only `preview_token` and `csrf_token`. Normalize reason with whitespace collapse and bound it to 1-500 characters. Render the dismiss form only for a dismissible Candidate and valid identity.

```python
@app.post("/pipeline/queue/{candidate_id}/dismiss/preview",
          response_class=HTMLResponse)
async def candidate_dismiss_preview(candidate_id: str, request: Request) -> HTMLResponse:
    identity, session_id, csrf = _require_mutation_request(request)
    form = await request.form()
    if set(form) != {"reason", "csrf_token"}:
        raise HTTPException(status_code=422, detail="invalid mutation input")
    reason = " ".join(str(form["reason"]).split())
    dry_run = dismiss_candidate(
        repo.root, candidate_id, actor=identity.researcher_id,
        reason=reason, apply=False,
    )
    target_version = candidate_db.candidate_version(repo.root, candidate_id)
    grant = gateway.issue(MutationPreviewInput(
        operation="candidate.dismiss", actor=identity.researcher_id,
        target_type="candidate", target_id=candidate_id,
        target_version=target_version, normalized_input={"reason": reason},
        summary={"status_before": dry_run["status_before"],
                 "status_after": dry_run["status_after"]},
    ))
    _record_preview_audit(repo.root, grant.preview)
    return HTMLResponse(_dismiss_confirmation(grant, csrf))
```

Add:

- `POST /pipeline/queue/{candidate_id}/dismiss/preview`
- `POST /pipeline/queue/{candidate_id}/dismiss/commit`
- `GET /pipeline/queue/{candidate_id}/mutations/{mutation_id}`

The commit route verifies the path Candidate equals the token-bound target, calls the Gateway and atomic adapter, stores only bounded result identifiers in a process-local result registry, then returns `RedirectResponse(location=..., status_code=303)`. The result GET reads Candidate status plus identifiers and performs no write.

When token parsing reaches a known registry record, Gateway exceptions carry that preview plus a bounded reason code. The route appends a separate `rejected` or `expired` event for `actor_mismatch`, `operation_mismatch`, `target_changed`, `replayed`, or `expired`; raw garbage, unknown nonces, bad CSRF, and bad Origin are not falsely attributed. This best-effort rejection audit uses a short independent SQLite transaction, suppresses only its own database error, and never changes the HTTP result or business state.

- [ ] **Step 5: Update styling and exact mutation allowlists**

Replace Candidate detail's CLI instruction with the Web form. Add labels, textarea, action row, destructive button variant, and focus styles without nesting cards or changing the global visual system.

```css
.mutation-form { display: grid; gap: 0.75rem; max-width: 42rem; }
.mutation-form textarea { min-height: 7rem; resize: vertical; }
.mutation-actions { display: flex; flex-wrap: wrap; gap: 0.65rem; align-items: center; }
.mutation-actions button { margin-left: 0; }
.button-danger { background: var(--danger); border-color: var(--danger); }
```

Update both exact route tests to allow only the three existing `/llm/*` routes plus the two Candidate POST route templates. Assert there is no POST under `/reviews`, `/theses`, `/analysis`, `/impact`, or `/decision`.

- [ ] **Step 6: Run Web, security, and regression tests and commit**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_candidate_db.py \
  09_Automation/tests/test_triage.py \
  09_Automation/tests/test_web_mutation.py \
  09_Automation/tests/test_m5_dashboard_jobs.py \
  09_Automation/tests/test_m6_security.py -q
/Users/max/.venvs/ai-research-os/bin/python -m ruff check \
  src/research_os/services/candidate_db.py \
  src/research_os/services/mutation_audit.py \
  src/research_os/services/web_identity.py \
  src/research_os/services/mutation_gateway.py \
  src/research_os/services/triage.py \
  src/research_os/ui/app.py \
  09_Automation/tests/test_candidate_db.py \
  09_Automation/tests/test_triage.py \
  09_Automation/tests/test_web_mutation.py \
  09_Automation/tests/test_m5_dashboard_jobs.py \
  09_Automation/tests/test_m6_security.py
```

Expected: focused suite passes. In the isolated worktree, only tests requiring real ignored `01_Inbox/_assets` may be deselected for this step; no raw assets are copied or committed.

```bash
git add src/research_os/ui/app.py src/research_os/ui/styles.css \
  09_Automation/tests/test_web_mutation.py \
  09_Automation/tests/test_m5_dashboard_jobs.py \
  09_Automation/tests/test_m6_security.py
git commit -m "feat(v0.3): add candidate dismiss web flow"
```

### Task 6: Integration Gate, Evidence, and F-026 Status

**Files:**
- Modify: `09_Automation/tests/test_backup.py`
- Modify: `09_Automation/tests/test_m6_release.py`
- Modify: `src/research_os/services/release.py`
- Modify: `00_System/v0.3_Performance_Benchmark.md`
- Modify: `00_System/v0.3_Recovery_Drill.md`
- Modify: `00_System/v0.3_Release_Gate_Verification_2026-08-12.md` or create a later dated replacement when the date changes
- Modify: `README.md`
- Modify: `00_System/v0.3_User_Runbook.md`
- Modify: `00_System/v0.3_Known_Limitations.md`
- Modify: `00_System/v0.3_AI_Industry_Intelligence_OS/07_Phase_6_Productization_and_Scale.md`
- Modify: `00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md`

- [ ] **Step 1: Update literal schema contracts test-first**

Change fixture assertions from Candidate schema 2 to 3 only where they describe the current operational schema. Keep historical v2 migration/rehearsal facts unchanged. Update the performance parser's exact requirement from `current version 2` to `current version 3`; do not loosen row counts, p95, SLO, pass status, date, or zero-authoritative-write requirements.

```python
re.fullmatch(r"current version 3", _plain_cell(values["Candidate schema"]))
```

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_backup.py \
  09_Automation/tests/test_m6_release.py \
  09_Automation/tests/test_operational_job_audit.py -q
```

Expected before evidence refresh: code-level schema tests pass; evidence-dependent release checks fail specifically because the committed benchmark/recovery/security provenance predates the final code tree.

- [ ] **Step 2: Run a disposable backup/restore and Candidate performance measurement**

Use the repository's existing documented benchmark and recovery commands discovered from these files:

```bash
rg -n "python -m|research-os|benchmark|backup|restore" \
  00_System/v0.3_Performance_Benchmark.md \
  00_System/v0.3_Recovery_Drill.md \
  09_Automation/tests/test_backup.py
```

Run the exact existing commands against a disposable location. Record measured schema v3, integrity, hashes, duration, Candidate row count, and audit-table preservation. Do not replace historical hashes or claim a remote backup run that was not performed.

- [ ] **Step 3: Run the final complete code Gate once**

From an integration checkout that can read the existing ignored source assets without modifying them, run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest -q
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  --cov=research_os --cov-branch --cov-report=term-missing -q
/Users/max/.venvs/ai-research-os/bin/python -m ruff check src 09_Automation/tests
/Users/max/.venvs/ai-research-os/bin/python -m ruff format --check src 09_Automation/tests
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m mypy src/research_os
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m compileall -q src
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os.cli validate --strict
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os.cli index --check
```

Expected: all tests pass with the repository's documented skip policy, branch coverage remains at least 80%, Ruff/mypy/compileall pass, strict validation reports 0 errors and 0 warnings, and indexes match.

- [ ] **Step 4: Run real loopback Dashboard mutation/security smoke**

Create `00_System/web.local.json` locally with a fresh high-entropy secret, chmod it `0600`, and keep it ignored. Start the existing UI server on loopback, then exercise Candidate detail GET, preview POST, confirmation, commit POST, redirected GET, replay rejection, cross-origin rejection, and the ten existing F-023 GET smoke routes using a disposable Candidate database snapshot. Remove only the disposable snapshot; retain or rotate the local config according to the runbook.

Expected: preview does not change Candidate state, successful commit returns 303, one action and one committed audit exist, replay returns 409, hostile Origin returns 403, and all required GET routes return 200.

- [ ] **Step 5: Record evidence and update governance without changing authority**

Update measured benchmark/recovery tables and the dated release verification with the exact commit, commands, counts, schema v3, smoke results, and provenance trees. The F-023 21-check contract remains unchanged; because its quality and Dashboard security trees changed, only mark its prior `16/21` state restored after the new evidence is committed and the release evaluator accepts it.

Update docs to state:

- Candidate dismiss is available through Website preview → confirmation → commit.
- Website is the sole user-facing product interface.
- CLI remains only an internal migration/scheduler/diagnostic/test/disaster-recovery adapter.
- Review approval, Thesis mutation, Candidate restore/promote, F-027/F-028, and CLI retirement remain incomplete.
- Generated Evidence or Thesis changes still require human review; F-026 does not grant an Agent or background job browser authority.

- [ ] **Step 6: Run final release checks and commit**

Run:

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m pytest \
  09_Automation/tests/test_m6_release.py \
  09_Automation/tests/test_m6_security.py \
  09_Automation/tests/test_web_mutation.py -q
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python -m research_os.cli validate --strict
git diff --check
git status --short
```

Expected: release/security/Web mutation tests pass; validation reports 0 errors and 0 warnings; diff check is clean; status contains only the intended F-026 implementation, tests, evidence, and documentation.

```bash
git add 09_Automation/tests/test_backup.py \
  09_Automation/tests/test_m6_release.py \
  src/research_os/services/release.py \
  00_System/v0.3_Performance_Benchmark.md \
  00_System/v0.3_Recovery_Drill.md \
  00_System/v0.3_Release_Gate_Verification_2026-08-12.md \
  README.md 00_System/v0.3_User_Runbook.md \
  00_System/v0.3_Known_Limitations.md \
  00_System/v0.3_AI_Industry_Intelligence_OS/07_Phase_6_Productization_and_Scale.md \
  00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md \
git commit -m "docs(v0.3): verify F-026 web mutation foundation"
```

Before updating or staging governance files, reconcile the worktree implementation with the main workspace's existing uncommitted RCP-v03-011 changes. Preserve those edits and never stage untracked operational Job records.

## Final Acceptance Review

- Candidate dismiss is fully usable through Website GET → preview POST → confirmation → commit POST → 303 → GET.
- Commit receives no editable actor, Candidate ID, reason, or desired status.
- Missing local identity leaves all GET routes usable and returns 503 for mutation routes.
- Host, Origin, session, CSRF, signature, actor, operation, expiry, nonce, replay, and target version checks are covered.
- Candidate update, `candidate_actions`, and committed `mutation_audit` event share one SQLite transaction.
- Retry is limited to transient transaction failure while token time and target version remain valid.
- No Review approval or Thesis confidence mutation adapter exists.
- Schema v3 migration and v3-to-v2 preservation rollback pass.
- Final quality, security, smoke, recovery, and performance evidence refers to the final integration commit.
- F-023 remains the same 21-check contract and returns to its evidence-supported `16/21` state; its five date/external blockers remain explicit.
