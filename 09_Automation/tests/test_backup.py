from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest

import test_research_os_core as fixtures
from research_os.services.backup import (
    backup_age_status,
    create_candidate_snapshot,
    verify_candidate_snapshot,
)
from research_os.services.candidate_db import (
    SCHEMA_VERSION,
    apply_migrations,
    candidate_db_path,
)
from research_os.services.operations_db import list_runs, operations_db_path
from test_cli import run_cli


class CandidateBackupTests(unittest.TestCase):
    def make_durable_root(self, base: Path) -> Path:
        root = fixtures.RepositoryValidationTests().make_root(str(base / "repo"))
        fixtures.add_generated_event_with_asset(
            root,
            quote="Different line contents",
            write_asset=True,
        )
        apply_migrations(candidate_db_path(root))
        return root

    def age_identity(self, root: Path) -> tuple[Path, str]:
        identity = root / "09_Automation" / "operational" / "test-age-identity.txt"
        identity.parent.mkdir(parents=True, exist_ok=True)
        generated = subprocess.run(
            ["age-keygen", "-o", str(identity)],
            check=True,
            capture_output=True,
            text=True,
        )
        match = re.search(r"Public key:\s*(age1\S+)", generated.stderr)
        self.assertIsNotNone(match)
        return identity, str(match.group(1))

    def write_backup_config(
        self,
        root: Path,
        recipient: str,
        *,
        relative: Path = Path("09_Automation/operational/backup.local.json"),
        extra: dict[str, object] | None = None,
    ) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {
            "repository": "owner/private-research",
            "recipients": [recipient],
        }
        if extra:
            payload.update(extra)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return relative

    @contextmanager
    def fake_gh(
        self,
        base: Path,
        *,
        fail_upload_secret: str | None = None,
    ) -> Iterator[Path]:
        binary_dir = base / "fake-bin"
        binary_dir.mkdir()
        state = base / "fake-gh-assets"
        executable = binary_dir / "gh"
        executable.write_text(
            """#!/usr/bin/env python3
import json
import os
import shutil
import sys
from pathlib import Path

args = sys.argv[1:]
state = Path(os.environ["FAKE_GH_STATE"])
if args[:2] == ["repo", "view"]:
    print(json.dumps({"isPrivate": True}))
    raise SystemExit(0)
if args[:2] == ["release", "view"]:
    assets = []
    if state.exists():
        assets = [
            {"name": path.name, "id": f"asset-{path.name}", "size": path.stat().st_size}
            for path in sorted(state.iterdir())
            if path.is_file()
        ]
    print(json.dumps({
        "tagName": "research-os-durable-backups-v1",
        "isPrerelease": True,
        "assets": assets,
    }))
    raise SystemExit(0)
if args[:2] == ["release", "upload"]:
    if os.environ.get("FAKE_GH_FAIL_UPLOAD_SECRET"):
        print(os.environ["FAKE_GH_FAIL_UPLOAD_SECRET"], file=sys.stderr)
        raise SystemExit(1)
    source = Path(args[3])
    state.mkdir(parents=True, exist_ok=True)
    destination = state / source.name
    if destination.exists():
        raise SystemExit(1)
    shutil.copyfile(source, destination)
    raise SystemExit(0)
if args[:2] == ["release", "download"]:
    name = args[args.index("--pattern") + 1]
    destination = Path(args[args.index("--output") + 1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(state / name, destination)
    raise SystemExit(0)
raise SystemExit(2)
""",
            encoding="utf-8",
        )
        executable.chmod(0o700)
        environment = {
            "PATH": f"{binary_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_STATE": str(state),
        }
        if fail_upload_secret is not None:
            environment["FAKE_GH_FAIL_UPLOAD_SECRET"] = fail_upload_secret
        with mock.patch.dict(os.environ, environment):
            yield state

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
            self.assertEqual(SCHEMA_VERSION, manifest["schema_version"])
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
            legacy_jobs = sorted(job_folder.glob("*.md"))
            self.assertFalse(operations_db_path(root).exists())

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
            self.assertEqual(legacy_jobs, sorted(job_folder.glob("*.md")))
            runs = list_runs(operations_db_path(root))
            self.assertEqual(1, len(runs))
            self.assertEqual("backup-candidate", runs[0].job_name)
            self.assertEqual("success", runs[0].status)

    @pytest.mark.local_integration
    def test_durable_create_dry_run_preflights_without_writes_or_job(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = self.make_durable_root(base)
            _identity, recipient = self.age_identity(root)
            config = self.write_backup_config(root, recipient)

            with self.fake_gh(base) as remote:
                result = run_cli(
                    root,
                    "backup",
                    "durable",
                    "create",
                    "--config",
                    str(config),
                )

            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("DRY-RUN", result.stdout)
            self.assertNotIn(recipient, result.stdout)
            self.assertNotIn(str(config), result.stdout)
            self.assertEqual([], list(remote.glob("*")))
            self.assertEqual(
                [],
                list(
                    (root / "05_Research" / "Operations" / "Jobs").glob(
                        "*backup-durable*"
                    )
                ),
            )
            self.assertFalse(
                (
                    root / "09_Automation" / "operational" / "backups" / "durable"
                ).exists()
            )

    @pytest.mark.local_integration
    def test_durable_apply_verify_and_restore_are_safe_and_audited(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = self.make_durable_root(base)
            identity, recipient = self.age_identity(root)
            config = self.write_backup_config(root, recipient)
            identity_relative = identity.relative_to(root)

            with self.fake_gh(base) as remote:
                created = run_cli(
                    root,
                    "backup",
                    "durable",
                    "create",
                    "--config",
                    str(config),
                    "--apply",
                )
                self.assertEqual(0, created.returncode, created.stdout)
                latest = (
                    root
                    / "09_Automation"
                    / "operational"
                    / "backups"
                    / "durable"
                    / "latest-success.json"
                )
                receipt = json.loads(latest.read_text(encoding="utf-8"))
                backup_id = str(receipt["backup_id"])

                verified = run_cli(
                    root,
                    "backup",
                    "durable",
                    "verify-remote",
                    "--backup-id",
                    backup_id,
                )
                self.assertEqual(0, verified.returncode, verified.stdout)
                self.assertIn("VERIFIED", verified.stdout)

                destination_relative = (
                    Path("09_Automation") / "operational" / "restores" / backup_id
                )
                dry_restore = run_cli(
                    root,
                    "backup",
                    "durable",
                    "restore",
                    "--backup-id",
                    backup_id,
                    "--identity",
                    str(identity_relative),
                    "--destination",
                    str(destination_relative),
                )
                self.assertEqual(0, dry_restore.returncode, dry_restore.stdout)
                self.assertIn("DRY-RUN", dry_restore.stdout)
                self.assertFalse((root / destination_relative).exists())

                restored = run_cli(
                    root,
                    "backup",
                    "durable",
                    "restore",
                    "--backup-id",
                    backup_id,
                    "--identity",
                    str(identity_relative),
                    "--destination",
                    str(destination_relative),
                    "--apply",
                )

            self.assertEqual(0, restored.returncode, restored.stdout)
            self.assertIn("RESTORED", restored.stdout)
            self.assertEqual(4, len(list(remote.glob("*"))))
            restored_root = root / destination_relative
            restored_db = (
                restored_root / "09_Automation" / "operational" / "candidates.db"
            )
            connection = sqlite3.connect(restored_db)
            try:
                self.assertEqual(
                    ("ok",),
                    connection.execute("PRAGMA integrity_check").fetchone(),
                )
            finally:
                connection.close()
            self.assertEqual(
                "Different line contents",
                (
                    restored_root
                    / "01_Inbox"
                    / "_assets"
                    / "SRC-20260729-001"
                    / "source.html.extracted.txt"
                ).read_text(encoding="utf-8"),
            )

            runs = [
                run
                for run in list_runs(operations_db_path(root))
                if run.job_name == "backup-durable"
            ]
            self.assertEqual(1, len(runs))
            persisted = runs[0].message or ""
            self.assertEqual("success", runs[0].status)
            outputs = (
                created.stdout + verified.stdout + dry_restore.stdout + restored.stdout
            )
            private_key = identity.read_text(encoding="utf-8")
            for sensitive in (
                recipient,
                str(config),
                str(identity_relative),
                private_key,
            ):
                self.assertNotIn(sensitive, outputs)
                self.assertNotIn(sensitive, persisted)
            self.assertIn(backup_id, persisted)

    @pytest.mark.local_integration
    def test_durable_restore_dry_run_rejects_nonempty_and_live_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = self.make_durable_root(base)
            identity, recipient = self.age_identity(root)
            config = self.write_backup_config(root, recipient)
            identity_relative = identity.relative_to(root)

            with self.fake_gh(base):
                created = run_cli(
                    root,
                    "backup",
                    "durable",
                    "create",
                    "--config",
                    str(config),
                    "--apply",
                )
                self.assertEqual(0, created.returncode, created.stdout)
                latest = (
                    root
                    / "09_Automation"
                    / "operational"
                    / "backups"
                    / "durable"
                    / "latest-success.json"
                )
                backup_id = str(
                    json.loads(latest.read_text(encoding="utf-8"))["backup_id"]
                )

                nonempty = root / "09_Automation" / "operational" / "nonempty-restore"
                nonempty.mkdir(parents=True)
                marker = nonempty / "keep.txt"
                marker.write_text("keep", encoding="utf-8")
                refused_nonempty = run_cli(
                    root,
                    "backup",
                    "durable",
                    "restore",
                    "--backup-id",
                    backup_id,
                    "--identity",
                    str(identity_relative),
                    "--destination",
                    str(nonempty.relative_to(root)),
                )
                refused_live = run_cli(
                    root,
                    "backup",
                    "durable",
                    "restore",
                    "--backup-id",
                    backup_id,
                    "--identity",
                    str(identity_relative),
                    "--destination",
                    "09_Automation/operational/candidates.db",
                )

            self.assertEqual(2, refused_nonempty.returncode, refused_nonempty.stdout)
            self.assertEqual(2, refused_live.returncode, refused_live.stdout)
            self.assertEqual("keep", marker.read_text(encoding="utf-8"))
            self.assertNotIn(str(identity_relative), refused_nonempty.stdout)
            self.assertNotIn(str(identity_relative), refused_live.stdout)

    @pytest.mark.local_integration
    def test_durable_apply_failure_writes_redacted_job(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = self.make_durable_root(base)
            _identity, recipient = self.age_identity(root)
            config = Path("private") / "sensitive-backup-config.json"
            identity_secret = "AGE-SECRET-KEY-DO-NOT-PERSIST"
            query_secret = "QUERY-SECRET-DO-NOT-PERSIST"
            self.write_backup_config(
                root,
                recipient,
                relative=config,
                extra={
                    "identity": identity_secret,
                    "token": f"https://example.test/?token={query_secret}",
                },
            )

            with self.fake_gh(base):
                failed = run_cli(
                    root,
                    "backup",
                    "durable",
                    "create",
                    "--config",
                    str(config),
                    "--apply",
                )

            self.assertEqual(1, failed.returncode, failed.stdout)
            self.assertIn("FAILED", failed.stdout)
            runs = [
                run
                for run in list_runs(operations_db_path(root))
                if run.job_name == "backup-durable"
            ]
            self.assertEqual(1, len(runs))
            persisted = runs[0].message or ""
            self.assertEqual("failed", runs[0].status)
            for sensitive in (
                recipient,
                str(config),
                identity_secret,
                query_secret,
            ):
                self.assertNotIn(sensitive, failed.stdout)
                self.assertNotIn(sensitive, persisted)
            self.assertFalse(
                (
                    root
                    / "09_Automation"
                    / "operational"
                    / "backups"
                    / "durable"
                    / "latest-success.json"
                ).exists()
            )

    def test_durable_backup_operator_docs_pin_commands_and_key_custody(self) -> None:
        root = Path(__file__).resolve().parents[2]
        recovery = (root / "00_System/Recovery_Runbook.md").read_text(encoding="utf-8")
        user = (root / "00_System/v0.3_User_Runbook.md").read_text(encoding="utf-8")
        launchd = (root / "09_Automation/launchd/RUNBOOK.md").read_text(
            encoding="utf-8"
        )
        readme = (root / "README.md").read_text(encoding="utf-8")

        for text in (
            "当前平台的包管理器",
            "age-keygen",
            "gh auth status",
            "research-os-durable-backups-v1",
            '"repository"',
            '"recipients"',
            "A recipient is a public encryption identity",
            "An identity is a private decryption key",
            "second independent identity",
            "offline",
            "09_Automation/operational/durable_backup.json",
            "09_Automation/operational/backups/durable/latest-success.json",
            "/operations/backups",
            "Candidate + operations snapshots",
            'backup durable verify-remote --backup-id "$BACKUP_ID"',
            'backup durable restore --backup-id "$BACKUP_ID"',
            '--identity "$AGE_IDENTITY"',
            '--destination "$RESTORE_DESTINATION"',
        ):
            with self.subTest(document="recovery", text=text):
                self.assertIn(text, recovery)

        for text in (
            "/operations/backups",
            "09_Automation/operational/durable_backup.json",
            'backup durable verify-remote --backup-id "$BACKUP_ID"',
            'backup durable restore --backup-id "$BACKUP_ID"',
            "BKP_DURABLE_MISSING",
            "BKP_DURABLE_FAILED",
            "BKP_DURABLE_INVALID",
            "BKP_DURABLE_STALE",
            "24-hour RPO",
            "P1",
        ):
            with self.subTest(document="user", text=text):
                self.assertIn(text, user)

        for text in ("Legacy launchd Rollback Artifact", "网站 Worker", "禁止"):
            with self.subTest(document="launchd", text=text):
                self.assertIn(text, launchd)

        self.assertIn("/operations/backups", readme)
        self.assertIn("operations.db", readme)
        self.assertIn("00_System/Recovery_Runbook.md", readme)
        self.assertNotIn("brew install", recovery)


if __name__ == "__main__":
    unittest.main()
