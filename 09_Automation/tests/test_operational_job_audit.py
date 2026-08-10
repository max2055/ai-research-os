from __future__ import annotations

import re
import sqlite3
import unittest
from collections import Counter
from contextlib import closing
from datetime import datetime
from pathlib import Path

from research_os.repositories.markdown import MarkdownDocument

ROOT = Path(__file__).resolve().parents[2]
JOBS_DIR = ROOT / "05_Research" / "Operations" / "Jobs"
AUDIT_PATH = ROOT / "00_System" / "v0.3_Discovery_Job_Audit_2026-08-10.md"

EXPECTED_JOB_FILES = (
    "JOB-20260809154712-001-discover.md",
    "JOB-20260809154743-001-discover.md",
    "JOB-20260809154815-001-discover.md",
    "JOB-20260809154845-001-discover.md",
    "JOB-20260809154909-001-discover.md",
    "JOB-20260809154931-001-discover.md",
    "JOB-20260809154957-001-discover.md",
    "JOB-20260809155024-001-discover.md",
    "JOB-20260809155051-001-discover.md",
    "JOB-20260809155116-001-discover.md",
    "JOB-20260809155138-001-discover.md",
    "JOB-20260809155203-001-discover.md",
    "JOB-20260809155225-001-discover.md",
    "JOB-20260809155249-001-discover.md",
    "JOB-20260809155314-001-discover.md",
    "JOB-20260809155340-001-expire.md",
    "JOB-20260809215408-001-discover.md",
    "JOB-20260809215443-001-discover.md",
    "JOB-20260809215517-001-discover.md",
    "JOB-20260809215550-001-discover.md",
    "JOB-20260809215623-001-discover.md",
    "JOB-20260809215656-001-discover.md",
    "JOB-20260809215730-001-discover.md",
    "JOB-20260809215803-001-discover.md",
    "JOB-20260809215837-001-discover.md",
    "JOB-20260809215910-001-discover.md",
    "JOB-20260809215945-001-discover.md",
    "JOB-20260809220020-001-discover.md",
    "JOB-20260809220054-001-discover.md",
    "JOB-20260809220127-001-expire.md",
)
EXPECTED_JOB_IDS = frozenset(
    name.removesuffix("-discover.md").removesuffix("-expire.md")
    for name in EXPECTED_JOB_FILES
)
EXPIRE_MESSAGE = "retention sweep: 0 expired, 0 purged"
FAILED_RUNS = {
    "JOB-20260809154712-001": ("CHN-arxiv", "RUN-5103a52bd05d4b1c"),
    "JOB-20260809154743-001": ("CHN-arxiv-agents", "RUN-7aa75664f4d74282"),
}
SUCCESS_MESSAGE = re.compile(
    r"^discovery run (?P<run_id>RUN-[0-9a-f]{16}) "
    r"for (?P<channel>CHN-[a-z0-9-]+): (?P<count>\d+) candidates, "
    r"(?P<inserted>\d+) inserted"
    r"(?:, (?P<skipped>\d+) skipped \(already sourced\))?$"
)


def _parse_time(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _primary_checkout(root: Path) -> Path:
    marker = root / ".git"
    if marker.is_dir():
        return root
    match = re.fullmatch(r"gitdir:\s*(.+)\s*", marker.read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError(f"cannot resolve worktree gitdir from {marker}")
    git_dir = Path(match.group(1))
    if not git_dir.is_absolute():
        git_dir = (root / git_dir).resolve()
    common_dir = (
        git_dir / (git_dir / "commondir").read_text(encoding="utf-8").strip()
    ).resolve()
    return common_dir.parent


def _candidate_connection() -> sqlite3.Connection:
    db_path = (
        _primary_checkout(ROOT) / "09_Automation" / "operational" / "candidates.db"
    )
    connection = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


class OperationalJobAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if len(EXPECTED_JOB_IDS) != 30:
            raise AssertionError(
                "the retained Job manifest must contain exactly 30 IDs"
            )

    def _documents(self) -> dict[str, MarkdownDocument]:
        missing = [
            name for name in EXPECTED_JOB_FILES if not (JOBS_DIR / name).is_file()
        ]
        self.assertEqual([], missing, "retained operational Job evidence is missing")
        return {
            name: MarkdownDocument.read(JOBS_DIR / name) for name in EXPECTED_JOB_FILES
        }

    def _by_id(self) -> dict[str, MarkdownDocument]:
        return {
            str(document.metadata["id"]): document
            for document in self._documents().values()
        }

    def test_exact_retained_manifest_and_outcomes(self) -> None:
        documents = self._documents()
        by_id = {
            str(document.metadata["id"]): document for document in documents.values()
        }
        self.assertEqual(EXPECTED_JOB_IDS, frozenset(by_id))
        self.assertEqual(
            Counter({"success": 28, "failed": 2}),
            Counter(
                str(document.metadata["status"]) for document in documents.values()
            ),
        )
        self.assertEqual(
            Counter({"discover": 28, "expire": 2}),
            Counter(
                str(document.metadata["job_name"]) for document in documents.values()
            ),
        )
        for document in documents.values():
            self.assertLessEqual(
                _parse_time(document.metadata["started_at"]),
                _parse_time(document.metadata["finished_at"]),
                str(document.metadata["id"]),
            )

    def test_expire_messages_are_exact(self) -> None:
        documents = self._documents()
        expires = [
            document
            for document in documents.values()
            if document.metadata["job_name"] == "expire"
        ]
        self.assertEqual(2, len(expires))
        self.assertEqual(
            [EXPIRE_MESSAGE, EXPIRE_MESSAGE],
            [document.metadata["message"] for document in expires],
        )

    def test_successful_discovery_messages_match_read_only_candidate_runs(self) -> None:
        documents = self._documents()
        expected_rows: dict[str, tuple[str, int]] = {}
        for document in documents.values():
            metadata = document.metadata
            if metadata["job_name"] != "discover" or metadata["status"] != "success":
                continue
            match = SUCCESS_MESSAGE.fullmatch(str(metadata["message"]))
            self.assertIsNotNone(match, str(metadata["id"]))
            assert match is not None
            self.assertEqual(
                metadata["target"], match.group("channel"), str(metadata["id"])
            )
            run_id = match.group("run_id")
            self.assertNotIn(run_id, expected_rows, f"duplicate discovery run {run_id}")
            expected_rows[run_id] = (str(metadata["target"]), int(match.group("count")))

        self.assertEqual(26, len(expected_rows))
        placeholders = ",".join("?" for _ in expected_rows)
        with closing(_candidate_connection()) as connection:
            rows = connection.execute(
                "SELECT run_id, channel_id, candidate_count, status "
                f"FROM discovery_runs WHERE run_id IN ({placeholders})",
                tuple(expected_rows),
            ).fetchall()
        self.assertEqual(set(expected_rows), {str(row["run_id"]) for row in rows})
        for row in rows:
            channel, candidate_count = expected_rows[str(row["run_id"])]
            self.assertEqual("succeeded", row["status"])
            self.assertEqual(channel, row["channel_id"])
            self.assertEqual(candidate_count, row["candidate_count"])

    def test_failed_jobs_are_retained_and_match_failed_candidate_runs(self) -> None:
        by_id = self._by_id()
        with closing(_candidate_connection()) as connection:
            for job_id, (channel, run_id) in FAILED_RUNS.items():
                document = by_id[job_id]
                metadata = document.metadata
                self.assertEqual("failed", metadata["status"])
                self.assertEqual("discover", metadata["job_name"])
                self.assertEqual(channel, metadata["target"])
                self.assertIn("SSL: UNEXPECTED_EOF_WHILE_READING", metadata["message"])
                row = connection.execute(
                    "SELECT run_id, channel_id, started_at, finished_at, status "
                    "FROM discovery_runs WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
                self.assertIsNotNone(row, run_id)
                assert row is not None
                self.assertEqual(channel, row["channel_id"])
                self.assertEqual("failed", row["status"])
                self.assertLessEqual(
                    _parse_time(metadata["started_at"]), _parse_time(row["started_at"])
                )
                self.assertLessEqual(
                    _parse_time(row["finished_at"]),
                    _parse_time(metadata["finished_at"]),
                )

    def test_audit_document_separates_claim_types_and_retains_incidents(self) -> None:
        self.assertTrue(AUDIT_PATH.is_file(), "operational audit document is missing")
        text = AUDIT_PATH.read_text(encoding="utf-8")
        sections = (
            "## Scope and method",
            "## Facts",
            "## Retained incidents",
            "## Candidate run reconciliation",
            "## Inference",
            "## Operational judgment",
            "## Post-fix verification",
        )
        positions = [text.index(section) for section in sections]
        self.assertEqual(sorted(positions), positions)
        for job_id, (channel, run_id) in FAILED_RUNS.items():
            self.assertRegex(
                text,
                rf"\|\s*{job_id}\s*\|\s*{channel}\s*\|\s*{run_id}\s*\|\s*failed\s*\|",
            )
        self.assertIn("pending until transport fix", text)


if __name__ == "__main__":
    unittest.main()
