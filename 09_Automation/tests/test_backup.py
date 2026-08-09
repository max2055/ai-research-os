from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import test_research_os_core as fixtures
from research_os.services.backup import (
    backup_age_status,
    create_candidate_snapshot,
    verify_candidate_snapshot,
)
from research_os.services.candidate_db import apply_migrations, candidate_db_path
from test_cli import run_cli


class CandidateBackupTests(unittest.TestCase):
    def test_snapshot_is_immutable_integral_and_hash_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            apply_migrations(candidate_db_path(root))
            destination = root / "snapshots" / "candidates.db"

            manifest = create_candidate_snapshot(
                root,
                destination,
                now="2026-08-09T12:00:00Z",
            )
            manifest_path = destination.with_suffix(".db.manifest.json")
            self.assertTrue(destination.is_file())
            self.assertTrue(manifest_path.is_file())
            verified = verify_candidate_snapshot(destination, manifest_path)
            self.assertEqual("ok", verified["status"])
            self.assertEqual(64, len(manifest["sha256"]))
            self.assertEqual(2, manifest["schema_version"])
            self.assertNotIn("candidate_rows", manifest)
            with self.assertRaises(FileExistsError):
                create_candidate_snapshot(root, destination)

            destination.write_bytes(destination.read_bytes() + b"tamper")
            self.assertEqual(
                "hash_mismatch",
                verify_candidate_snapshot(destination, manifest_path)["status"],
            )

    def test_backup_age_status_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "snapshot.db.manifest.json"
            self.assertEqual("missing", backup_age_status(path)["status"])
            path.write_text(
                json.dumps({"created_at": "2026-08-09T00:00:00Z"}),
                encoding="utf-8",
            )
            self.assertEqual(
                "fresh",
                backup_age_status(path, now="2026-08-09T23:00:00Z")["status"],
            )
            self.assertEqual(
                "stale",
                backup_age_status(path, now="2026-08-10T01:00:00Z")["status"],
            )

    def test_cli_dry_run_and_apply_record_a_job(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            apply_migrations(candidate_db_path(root))
            destination = root / "snapshots" / "candidate.db"

            dry_run = run_cli(
                root,
                "backup",
                "candidate",
                "--destination",
                str(destination),
                "--dry-run",
            )
            self.assertEqual(0, dry_run.returncode, dry_run.stdout)
            self.assertFalse(destination.exists())
            job_folder = root / "05_Research" / "Operations" / "Jobs"
            self.assertEqual([], list(job_folder.glob("*backup*")))

            applied = run_cli(
                root,
                "backup",
                "candidate",
                "--destination",
                str(destination),
                "--apply",
            )
            self.assertEqual(0, applied.returncode, applied.stdout)
            self.assertTrue(destination.is_file())
            self.assertIn("SUCCESS", applied.stdout)
            self.assertEqual(
                1,
                len(list(job_folder.glob("*backup-candidate*"))),
            )


if __name__ == "__main__":
    unittest.main()
