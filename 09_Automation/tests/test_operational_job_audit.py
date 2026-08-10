from __future__ import annotations

import re
import sqlite3
import tempfile
import unittest
from collections import Counter
from contextlib import closing
from datetime import datetime
from hashlib import sha256
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
EXPECTED_SHA256_BY_ID = {
    "JOB-20260809154712-001": (
        "90ae445514b473474f6b19086e0b2bb7b1309dd5e4190d72c30cfa47691859db"
    ),
    "JOB-20260809154743-001": (
        "67fa3bb87b003becfcae99616ffa0a67999b3126e282803b6b80804605f7b72d"
    ),
    "JOB-20260809154815-001": (
        "897fd9cc3d13700255ca014df5b0b5731cb8aa95a77f57e3342f015ebfdfa321"
    ),
    "JOB-20260809154845-001": (
        "bdb15bb1c9e32812aa0534b8673f6f6acc849654fd43565e4f3e56c6879325b2"
    ),
    "JOB-20260809154909-001": (
        "e708d9fa7c719e7de3218cb20b3a591b4657323908432242c4936a9d667d76c0"
    ),
    "JOB-20260809154931-001": (
        "b550a82e2a1e95379c7a5c601ee8db36b3c99e40a0c3caff9ccf674d4887dc2e"
    ),
    "JOB-20260809154957-001": (
        "fcaff27077511bd374950db023c630a3deae16332ab8d9b29fd46da59a527291"
    ),
    "JOB-20260809155024-001": (
        "da693266824b1e6632b7e9843f6e6a486d91be080ce50e9fc299aeaf76fe012e"
    ),
    "JOB-20260809155051-001": (
        "5884dda480e989155ee66c5a2710822552d18c4ddcfcc9ea74b68d33a0337da7"
    ),
    "JOB-20260809155116-001": (
        "33bcf6228581e8b386a18964eaf974bbc7cbab2a60b2fe6ce805c4daa0683d81"
    ),
    "JOB-20260809155138-001": (
        "9d2dda48355e8e7e09aa855c675ffda1dfe66001e417f022d7b8b2c171c88bf9"
    ),
    "JOB-20260809155203-001": (
        "48e35dbfff0ba0996f5004aa196d6837f005c9d68ccef4fd474867a7f2b7601d"
    ),
    "JOB-20260809155225-001": (
        "4aa42a8dc478bbc68e06b5142a2a254be9417f7694fc50f92009b04e7853a246"
    ),
    "JOB-20260809155249-001": (
        "5b63154d4cc5df6a2fa9efc23557e6e625084a1bef5b0a7684f21461abc8702b"
    ),
    "JOB-20260809155314-001": (
        "2701446cf2cb7526fc48d0a0dfd37a4ada9499396ba601942641dd8dc2bb4893"
    ),
    "JOB-20260809155340-001": (
        "ffb83d0612008143fe2cc2e9d5ccd57096f2c7aa410b7128ba3cf3f23c8a0fb6"
    ),
    "JOB-20260809215408-001": (
        "3691347894cb0cad0fcf4cbec7667822656d5ff89d74a2fea910bfedf8ee3026"
    ),
    "JOB-20260809215443-001": (
        "33afbb0bbfb60f0d6f2f7e920c036941b26796198fe9bf92dc16588b671bcd53"
    ),
    "JOB-20260809215517-001": (
        "c2f541249c8321edb7394f672c2476202f410e1d0ba563bff8317d3d85674022"
    ),
    "JOB-20260809215550-001": (
        "5e533c71a9ccd5570ca0dd6e71155b097e92309535c84e64fed7a3721f25f054"
    ),
    "JOB-20260809215623-001": (
        "d73585514efc0dd127508c9443346255fe0f17f9d0cac48239504fc54b4cf843"
    ),
    "JOB-20260809215656-001": (
        "5de0494b7622bf6990f329535fb3a97536c3b2a7d0fad91643f0c01085cc54ff"
    ),
    "JOB-20260809215730-001": (
        "f20408ee462a6b0388aadfb7b7a0ca397c15c91dc67380036475841d8dc7b121"
    ),
    "JOB-20260809215803-001": (
        "cbd131e180845dac9a6260953441eddf38558e9db166f36a013dc7a4163fdc19"
    ),
    "JOB-20260809215837-001": (
        "e5d37f66d95c98c808cb0d34489c71b55be83866724c1f706b45af334a157ea5"
    ),
    "JOB-20260809215910-001": (
        "2cbfacb185cd55036b131be4df22f417ea2932b16f830f6068de0076de00b52a"
    ),
    "JOB-20260809215945-001": (
        "b8e0dfaaf08ad44dbcac8b07c20679f112014ca59a7f12bde5d8365debfd50a4"
    ),
    "JOB-20260809220020-001": (
        "1b83028a4955ff3b68d8cd44743f6f883290a7673dede887dd8a9d13dc1a454f"
    ),
    "JOB-20260809220054-001": (
        "60c24111486397ad1ff79414271e0a0556003df63f73c326df1205b4583761c1"
    ),
    "JOB-20260809220127-001": (
        "c23bb948e5a1a98e62d0cf2b5cf35150d465ad20c0456c2e8c37c23061bf434c"
    ),
}

# run_id, channel, candidate_count, inserted, skipped
EXPECTED_SUCCESS_RUNS = {
    "JOB-20260809154815-001": (
        "RUN-d4682351aa114d6f",
        "CHN-arxiv-datacenter",
        17,
        17,
        3,
    ),
    "JOB-20260809154845-001": (
        "RUN-5f67966d93d94f17",
        "CHN-arxiv-econ",
        20,
        20,
        0,
    ),
    "JOB-20260809154909-001": (
        "RUN-b3c46f54774e4fd0",
        "CHN-arxiv-hardware",
        10,
        10,
        10,
    ),
    "JOB-20260809154931-001": (
        "RUN-5e7e958c1af84cc7",
        "CHN-arxiv-llm",
        20,
        20,
        0,
    ),
    "JOB-20260809154957-001": (
        "RUN-e4736d5c337c4b6e",
        "CHN-arxiv-vision",
        20,
        20,
        0,
    ),
    "JOB-20260809155024-001": (
        "RUN-7722ea2af14e41f2",
        "CHN-sec-amazon",
        7,
        7,
        13,
    ),
    "JOB-20260809155051-001": (
        "RUN-83c42d82a77f4218",
        "CHN-sec-coreweave",
        19,
        19,
        1,
    ),
    "JOB-20260809155116-001": (
        "RUN-108488cd531d482a",
        "CHN-sec-meta",
        6,
        6,
        14,
    ),
    "JOB-20260809155138-001": (
        "RUN-9ea46551dc674933",
        "CHN-sec-micron",
        6,
        6,
        14,
    ),
    "JOB-20260809155203-001": (
        "RUN-2c06d25c54ee431b",
        "CHN-sec-microsoft",
        4,
        4,
        16,
    ),
    "JOB-20260809155225-001": (
        "RUN-0871a079067c4a96",
        "CHN-sec-nvidia",
        6,
        6,
        14,
    ),
    "JOB-20260809155249-001": (
        "RUN-8311faeec470473e",
        "CHN-sec-tsmc",
        19,
        19,
        1,
    ),
    "JOB-20260809155314-001": (
        "RUN-5d07a9a471684649",
        "CHN-skhynix-ir",
        10,
        10,
        0,
    ),
    "JOB-20260809215408-001": (
        "RUN-2b83da0300944187",
        "CHN-github-anthropic",
        20,
        20,
        0,
    ),
    "JOB-20260809215443-001": (
        "RUN-87a400af10c04c1e",
        "CHN-github-deepseek",
        1,
        1,
        0,
    ),
    "JOB-20260809215517-001": (
        "RUN-24167766b6ca446b",
        "CHN-github-meta",
        3,
        3,
        1,
    ),
    "JOB-20260809215550-001": (
        "RUN-ef9ba2d2a12c462a",
        "CHN-github-microsoft",
        20,
        20,
        0,
    ),
    "JOB-20260809215623-001": (
        "RUN-3e2ae0b32c984f1a",
        "CHN-github-openai",
        19,
        19,
        1,
    ),
    "JOB-20260809215656-001": (
        "RUN-db6e10a31b0a4a88",
        "CHN-sec-amazon",
        7,
        7,
        13,
    ),
    "JOB-20260809215730-001": (
        "RUN-2b13fb8d72c5447f",
        "CHN-sec-coreweave",
        19,
        19,
        1,
    ),
    "JOB-20260809215803-001": (
        "RUN-746b99a0e8e14c65",
        "CHN-sec-meta",
        6,
        6,
        14,
    ),
    "JOB-20260809215837-001": (
        "RUN-c1bcb10a141241d9",
        "CHN-sec-micron",
        6,
        6,
        14,
    ),
    "JOB-20260809215910-001": (
        "RUN-8290d9caee1b4a0a",
        "CHN-sec-microsoft",
        4,
        4,
        16,
    ),
    "JOB-20260809215945-001": (
        "RUN-98c0485cd6b744af",
        "CHN-sec-nvidia",
        6,
        6,
        14,
    ),
    "JOB-20260809220020-001": (
        "RUN-c3317bb4627f4699",
        "CHN-sec-tsmc",
        19,
        19,
        1,
    ),
    "JOB-20260809220054-001": (
        "RUN-1ffb2bd142844eac",
        "CHN-skhynix-ir",
        10,
        10,
        0,
    ),
}

EXPIRE_MESSAGE = "retention sweep: 0 expired, 0 purged"
EXPECTED_FAILURES = {
    "JOB-20260809154712-001": (
        "CHN-arxiv",
        "RUN-5103a52bd05d4b1c",
        "ValueError: discovery failed for CHN-arxiv: <urlopen error "
        "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of "
        "protocol (_ssl.c:1032)>",
        "2026-08-09T15:47:12.309566+00:00",
        "2026-08-09T15:47:36.471828+00:00",
        "2026-08-09T15:47:31Z",
        "2026-08-09T15:47:36Z",
    ),
    "JOB-20260809154743-001": (
        "CHN-arxiv-agents",
        "RUN-7aa75664f4d74282",
        "ValueError: discovery failed for CHN-arxiv-agents: <urlopen error "
        "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of "
        "protocol (_ssl.c:1032)>",
        "2026-08-09T15:47:43.861532+00:00",
        "2026-08-09T15:48:07.949918+00:00",
        "2026-08-09T15:48:02Z",
        "2026-08-09T15:48:07Z",
    ),
}
EXPECTED_BATCH_WINDOWS = (
    (
        "2026-08-09T15:47:12.309566+00:00",
        "2026-08-09T15:53:55.649335+00:00",
        frozenset(
            {
                "JOB-20260809154712-001",
                "JOB-20260809154743-001",
                "JOB-20260809154815-001",
                "JOB-20260809154845-001",
                "JOB-20260809154909-001",
                "JOB-20260809154931-001",
                "JOB-20260809154957-001",
                "JOB-20260809155024-001",
                "JOB-20260809155051-001",
                "JOB-20260809155116-001",
                "JOB-20260809155138-001",
                "JOB-20260809155203-001",
                "JOB-20260809155225-001",
                "JOB-20260809155249-001",
                "JOB-20260809155314-001",
                "JOB-20260809155340-001",
            }
        ),
    ),
    (
        "2026-08-09T21:54:08.571939+00:00",
        "2026-08-09T22:01:46.290815+00:00",
        frozenset(
            {
                "JOB-20260809215408-001",
                "JOB-20260809215443-001",
                "JOB-20260809215517-001",
                "JOB-20260809215550-001",
                "JOB-20260809215623-001",
                "JOB-20260809215656-001",
                "JOB-20260809215730-001",
                "JOB-20260809215803-001",
                "JOB-20260809215837-001",
                "JOB-20260809215910-001",
                "JOB-20260809215945-001",
                "JOB-20260809220020-001",
                "JOB-20260809220054-001",
                "JOB-20260809220127-001",
            }
        ),
    ),
)
RESEARCH_AUTHORITY_DISCLAIMER = (
    "This audit describes operational evidence. It does not approve research "
    "objects,\nchange a Thesis, or establish an investment conclusion. Human "
    "review is required\nbefore treating the operational judgment as authoritative."
)
EXPECTED_FACT_ASSERTIONS = (
    "- The fixed manifest contains exactly 30 Job Runs: 28 `discover` and two "
    "`expire`.",
    "- The Job outcomes are 28 `success` and two `failed`.",
    "- The 26 successful discovery Jobs each contain one unique",
    "- Both expire messages are exactly `retention sweep: 0 expired, 0 purged`.",
)
EXPECTED_INCIDENT_LINES = (
    "| JOB-20260809154712-001 | CHN-arxiv | RUN-5103a52bd05d4b1c | failed | "
    "Job message contains `SSL: UNEXPECTED_EOF_WHILE_READING`. |",
    "| JOB-20260809154743-001 | CHN-arxiv-agents | RUN-7aa75664f4d74282 | "
    "failed | Job message contains `SSL: UNEXPECTED_EOF_WHILE_READING`. |",
)
EXPECTED_RECONCILIATION_LINES = (
    "| JOB-20260809154712-001 | 15:47:12.309566-15:47:36.471828 | "
    "RUN-5103a52bd05d4b1c: 15:47:31-15:47:36 | CHN-arxiv | failed |",
    "| JOB-20260809154743-001 | 15:47:43.861532-15:48:07.949918 | "
    "RUN-7aa75664f4d74282: 15:48:02-15:48:07 | CHN-arxiv-agents | failed |",
)
SUCCESS_MESSAGE = re.compile(
    r"^discovery run (?P<run_id>RUN-[0-9a-f]{16}) "
    r"for (?P<channel>CHN-[a-z0-9-]+): (?P<count>\d+) candidates, "
    r"(?P<inserted>\d+) inserted"
    r"(?:, (?P<skipped>\d+) skipped \(already sourced\))?$"
)


def _assert_file_sha256(path: Path, expected: str) -> None:
    actual = sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise AssertionError(
            f"SHA-256 mismatch for {path.name}: expected {expected}, got {actual}"
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
        if frozenset(EXPECTED_SHA256_BY_ID) != EXPECTED_JOB_IDS:
            raise AssertionError("the SHA-256 manifest must cover the exact 30 Job IDs")
        if len(EXPECTED_SUCCESS_RUNS) != 26:
            raise AssertionError("the success manifest must contain exactly 26 Jobs")
        batch_ids = frozenset(
            job_id
            for _started_at, _finished_at, job_ids in EXPECTED_BATCH_WINDOWS
            for job_id in job_ids
        )
        if batch_ids != EXPECTED_JOB_IDS:
            raise AssertionError(
                "the two batch windows must cover the exact 30 Job IDs"
            )

    def _documents(self) -> dict[str, MarkdownDocument]:
        missing = [
            name for name in EXPECTED_JOB_FILES if not (JOBS_DIR / name).is_file()
        ]
        self.assertEqual([], missing, "retained operational Job evidence is missing")
        documents: dict[str, MarkdownDocument] = {}
        for name in EXPECTED_JOB_FILES:
            job_id = name.removesuffix("-discover.md").removesuffix("-expire.md")
            path = JOBS_DIR / name
            _assert_file_sha256(path, EXPECTED_SHA256_BY_ID[job_id])
            document = MarkdownDocument.read(path)
            self.assertEqual(job_id, str(document.metadata["id"]), name)
            self.assertNotIn(job_id, documents)
            documents[job_id] = document
        return documents

    def test_sha256_guard_rejects_tampered_fixture(self) -> None:
        source = JOBS_DIR / EXPECTED_JOB_FILES[0]
        original = source.read_bytes()
        expected = sha256(original).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            tampered = Path(temp) / source.name
            tampered.write_bytes(original + b"\n# tampered\n")
            with self.assertRaisesRegex(AssertionError, "SHA-256"):
                _assert_file_sha256(tampered, expected)

    def test_exact_retained_manifest_and_outcomes(self) -> None:
        documents = self._documents()
        self.assertEqual(EXPECTED_JOB_IDS, frozenset(documents))
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
        for job_id, document in documents.items():
            metadata = document.metadata
            started_at = _parse_time(metadata["started_at"])
            finished_at = _parse_time(metadata["finished_at"])
            self.assertEqual("job", metadata["type"], job_id)
            self.assertEqual(1, metadata["schema_version"], job_id)
            expected_projects = (
                ["PRJ-001", "PRJ-002"] if metadata["job_name"] == "expire" else []
            )
            self.assertEqual(expected_projects, metadata["project_ids"], job_id)
            self.assertEqual([], metadata["tags"], job_id)
            self.assertEqual(
                f"Job {metadata['job_name']}", str(metadata["title"]), job_id
            )
            self.assertEqual("2026-08-09", str(metadata["created_at"]), job_id)
            self.assertEqual("2026-08-09", str(metadata["updated_at"]), job_id)
            self.assertEqual(job_id[4:18], started_at.strftime("%Y%m%d%H%M%S"))
            self.assertEqual(0, started_at.utcoffset().total_seconds(), job_id)
            self.assertEqual(0, finished_at.utcoffset().total_seconds(), job_id)
            self.assertLessEqual(
                started_at,
                finished_at,
                job_id,
            )
            self.assertIn("## Job", document.body, job_id)
            self.assertIn("## Result", document.body, job_id)

    def test_no_extra_jobs_overlap_the_two_retained_batch_windows(self) -> None:
        observed = [set(), set()]
        windows = [
            (_parse_time(started_at), _parse_time(finished_at), expected_ids)
            for started_at, finished_at, expected_ids in EXPECTED_BATCH_WINDOWS
        ]
        for path in JOBS_DIR.glob("JOB-*.md"):
            document = MarkdownDocument.read(path)
            job_started_at = _parse_time(document.metadata["started_at"])
            job_finished_at = _parse_time(document.metadata["finished_at"])
            for index, (window_start, window_finish, _expected_ids) in enumerate(
                windows
            ):
                if job_started_at <= window_finish and job_finished_at >= window_start:
                    observed[index].add(str(document.metadata["id"]))

        for index, (_window_start, _window_finish, expected_ids) in enumerate(windows):
            self.assertEqual(expected_ids, frozenset(observed[index]))

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
        actual_success_ids = {
            job_id
            for job_id, document in documents.items()
            if document.metadata["job_name"] == "discover"
            and document.metadata["status"] == "success"
        }
        self.assertEqual(frozenset(EXPECTED_SUCCESS_RUNS), actual_success_ids)
        expected_rows: dict[str, tuple[str, int]] = {}
        for job_id, expected in EXPECTED_SUCCESS_RUNS.items():
            document = documents[job_id]
            metadata = document.metadata
            match = SUCCESS_MESSAGE.fullmatch(str(metadata["message"]))
            self.assertIsNotNone(match, job_id)
            assert match is not None
            actual = (
                match.group("run_id"),
                match.group("channel"),
                int(match.group("count")),
                int(match.group("inserted")),
                int(match.group("skipped") or 0),
            )
            self.assertEqual(expected, actual, job_id)
            run_id, channel, candidate_count, _inserted, _skipped = expected
            self.assertRegex(run_id, r"^RUN-[0-9a-f]{16}$")
            self.assertEqual(channel, metadata["target"], job_id)
            self.assertNotIn(run_id, expected_rows, f"duplicate discovery run {run_id}")
            expected_rows[run_id] = (channel, candidate_count)

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
        documents = self._documents()
        with closing(_candidate_connection()) as connection:
            for job_id, expected in EXPECTED_FAILURES.items():
                (
                    channel,
                    run_id,
                    message,
                    job_started_at,
                    job_finished_at,
                    run_started_at,
                    run_finished_at,
                ) = expected
                document = documents[job_id]
                metadata = document.metadata
                self.assertEqual("failed", metadata["status"])
                self.assertEqual("discover", metadata["job_name"])
                self.assertEqual(channel, metadata["target"])
                self.assertEqual(message, metadata["message"])
                self.assertEqual(job_started_at, str(metadata["started_at"]))
                self.assertEqual(job_finished_at, str(metadata["finished_at"]))
                row = connection.execute(
                    "SELECT * FROM discovery_runs WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
                self.assertIsNotNone(row, run_id)
                assert row is not None
                self.assertEqual(run_id, row["run_id"])
                self.assertEqual(channel, row["channel_id"])
                self.assertEqual(run_started_at, row["started_at"])
                self.assertEqual(run_finished_at, row["finished_at"])
                self.assertIsNone(row["candidate_count"])
                self.assertEqual(0, row["http_errors"])
                self.assertEqual(0, row["parse_errors"])
                self.assertEqual(0, row["retries"])
                self.assertIsNone(row["cost_estimate"])
                self.assertEqual("0.3", row["software_version"])
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
        self.assertIn(RESEARCH_AUTHORITY_DISCLAIMER, text)
        for fact in EXPECTED_FACT_ASSERTIONS:
            self.assertIn(fact, text)
        for line in EXPECTED_INCIDENT_LINES + EXPECTED_RECONCILIATION_LINES:
            self.assertEqual(1, text.count(line), line)

        post_fix = text[text.index("## Post-fix verification") :]
        self.assertIn("Status: **pending until transport fix**.", post_fix)
        self.assertNotRegex(
            post_fix,
            r"(?i)\b(?:completed|passed)\b",
        )
        self.assertNotRegex(
            post_fix,
            r"(?i)\btransport\b[^.\n]{0,80}\b(?:fixed|verified)\b",
        )


if __name__ == "__main__":
    unittest.main()
