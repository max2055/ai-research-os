from __future__ import annotations

import hashlib
import io
import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from research_os.adapters.backup_remote import (
    DURABLE_BACKUP_RELEASE_TAG,
    GitHubReleaseBackend,
)
from research_os.services import durable_backup
from research_os.services.candidate_db import apply_migrations, candidate_db_path
from research_os.services.durable_backup import (
    BackupBackend,
    DurableBackupError,
    DurableBackupReceipt,
    DurableBackupRequest,
    EncryptedAsset,
    RemoteAsset,
    build_source_asset_inventory,
    create_durable_backup,
    restore_durable_backup,
)


class FakeBackupBackend(BackupBackend):
    repository = "example/private-research"
    release_tag = DURABLE_BACKUP_RELEASE_TAG

    def __init__(self, *, fail_upload_number: int | None = None) -> None:
        self.assets: dict[str, bytes] = {}
        self.preflight_calls: list[tuple[str, ...]] = []
        self.upload_calls = 0
        self.fail_upload_number = fail_upload_number
        self.temp_modes: list[int] = []

    def preflight(self, asset_names: tuple[str, ...]) -> None:
        self.preflight_calls.append(asset_names)
        collisions = sorted(set(asset_names).intersection(self.assets))
        if collisions:
            raise FileExistsError(f"remote backup assets already exist: {collisions}")

    def upload(self, path: Path, *, name: str) -> RemoteAsset:
        self.upload_calls += 1
        self.temp_modes.append(path.parent.stat().st_mode & 0o777)
        if self.upload_calls == self.fail_upload_number:
            raise RuntimeError("simulated partial upload")
        if name in self.assets:
            raise FileExistsError(name)
        self.assets[name] = path.read_bytes()
        return self.inspect(name=name)

    def inspect(self, *, name: str) -> RemoteAsset:
        payload = self.assets[name]
        return RemoteAsset(
            name=name,
            asset_id=f"asset-{name}",
            size_bytes=len(payload),
        )

    def download(self, *, name: str, destination: Path) -> None:
        if destination.exists():
            raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.assets[name])


class DurableBackupTests(unittest.TestCase):
    def assert_signal_cleans_owned_workspace(
        self,
        base: Path,
        *,
        operation: str,
        termination_signal: signal.Signals,
    ) -> None:
        temp_parent = base / f"temporary-{operation}-{termination_signal.name}"
        temp_parent.mkdir()
        ready = base / f"ready-{operation}-{termination_signal.name}"
        repository = Path(__file__).resolve().parents[2]
        script = textwrap.dedent(
            """
            import sys
            import time
            from pathlib import Path

            from research_os.services import durable_backup
            from research_os.services.durable_backup import (
                DurableBackupReceipt,
                DurableBackupRequest,
                EncryptedAsset,
                RemoteAsset,
                SourceAssetInventoryEntry,
            )

            operation = sys.argv[1]
            base = Path(sys.argv[2])
            temp_parent = Path(sys.argv[3])
            ready = Path(sys.argv[4])
            root = base / "repo"
            root.mkdir()


            class Backend:
                repository = "github.com/example/private-research"
                release_tag = "research-os-durable-backups-v1"

                def preflight(self, asset_names):
                    del asset_names

                def upload(self, path, *, name):
                    raise AssertionError((path, name))

                def inspect(self, *, name):
                    raise AssertionError(name)

                def download(self, *, name, destination):
                    raise AssertionError((name, destination))


            backend = Backend()


            def leave_plaintext_and_wait(work):
                (work / "candidates.db").write_bytes(b"candidate plaintext")
                (work / "candidates.db-wal").write_bytes(b"wal plaintext")
                (work / "source-asset.bin").write_bytes(b"source plaintext")
                ready.write_text("ready", encoding="utf-8")
                while True:
                    time.sleep(1)


            if operation == "create":
                durable_backup.build_source_asset_inventory = lambda root: (
                    SourceAssetInventoryEntry(
                        "SRC-20260810-001",
                        "01_Inbox/_assets/SRC-20260810-001/source.bin",
                        1,
                        "a" * 64,
                    ),
                )
                durable_backup.candidate_db_health = lambda path: {"status": "ok"}
                durable_backup._preflight_age = lambda recipients: None

                def block_create(root, work, **kwargs):
                    del root, kwargs
                    leave_plaintext_and_wait(work)

                durable_backup._write_candidate_archive = block_create
                request = DurableBackupRequest(
                    root=root,
                    recipients=("age1test",),
                    backend=backend,
                    apply=True,
                )
                durable_backup.create_durable_backup(
                    request,
                    now="2026-08-10T01:02:03Z",
                    backup_id="BKP-20260810T010203Z-aaaaaaaaaaaa",
                    temp_parent=temp_parent,
                )
            else:
                identity = base / "identity.txt"
                identity.write_text("test identity", encoding="utf-8")
                candidate = EncryptedAsset(
                    "candidate",
                    "candidate.tar.age",
                    "a" * 64,
                    1,
                    RemoteAsset("candidate.tar.age", "candidate", 1),
                )
                source_assets = EncryptedAsset(
                    "source_assets",
                    "source_assets.tar.age",
                    "b" * 64,
                    1,
                    RemoteAsset("source_assets.tar.age", "source", 1),
                )
                receipt = DurableBackupReceipt(
                    "BKP-20260810T010203Z-bbbbbbbbbbbb",
                    "2026-08-10T01:02:03Z",
                    "verified",
                    (candidate, source_assets),
                    backend.repository,
                    backend.release_tag,
                )
                durable_backup._verified_assets = lambda receipt, backend: {
                    "candidate": candidate,
                    "source_assets": source_assets,
                }

                def fake_download(receipt, encrypted, backend, work):
                    del receipt, encrypted, backend
                    ciphertext = work / "ciphertext.age"
                    ciphertext.write_bytes(b"ciphertext")
                    return ciphertext

                def block_decrypt(source, destination, identity):
                    del source, identity
                    leave_plaintext_and_wait(destination.parent)

                durable_backup._download_verified_ciphertext = fake_download
                durable_backup._decrypt_age = block_decrypt
                durable_backup.restore_durable_backup(
                    root,
                    receipt,
                    backend=backend,
                    identity=identity,
                    destination=base / "restore",
                    temp_parent=temp_parent,
                )
            """
        )
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(repository / "src")
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                script,
                operation,
                str(base),
                str(temp_parent),
                str(ready),
            ],
            cwd=repository,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 10
        while (
            not ready.is_file()
            and process.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        if not ready.is_file():
            stdout, stderr = process.communicate(timeout=2)
            self.fail(
                f"signal fixture did not become ready: "
                f"returncode={process.returncode}; stdout={stdout}; stderr={stderr}"
            )

        process.send_signal(termination_signal)
        stdout, stderr = process.communicate(timeout=10)

        self.assertEqual(
            -int(termination_signal),
            process.returncode,
            f"stdout={stdout}; stderr={stderr}",
        )
        self.assertEqual([], list(temp_parent.iterdir()))

    def make_root(self, base: Path) -> tuple[Path, bytes]:
        root = base / "repo"
        root.mkdir()
        apply_migrations(candidate_db_path(root))
        connection = sqlite3.connect(candidate_db_path(root))
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                "INSERT INTO candidates (candidate_id, channel_id, discovered_at, "
                "title, fetch_status, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "CND-aaaaaaaaaaaaaaaaaaaa",
                    "CHN-test",
                    "2026-08-10T00:00:00Z",
                    "WAL-backed candidate",
                    "fetched",
                    "new",
                    "2026-08-10T00:00:00Z",
                ),
            )
            connection.commit()
        finally:
            connection.close()

        raw = b"private source payload\x00\xff"
        asset = root / "01_Inbox" / "_assets" / "SRC-20260810-001" / "captured.bin"
        asset.parent.mkdir(parents=True)
        asset.write_bytes(raw)
        return root, raw

    def age_identity(self, base: Path) -> tuple[Path, str]:
        identity = base / "age-identity.txt"
        generated = subprocess.run(
            ["age-keygen", "-o", str(identity)],
            check=True,
            capture_output=True,
            text=True,
        )
        match = re.search(r"Public key:\s*(age1\S+)", generated.stderr)
        self.assertIsNotNone(match)
        return identity, str(match.group(1))

    def request(
        self, root: Path, recipient: str, backend: FakeBackupBackend, *, apply: bool
    ) -> DurableBackupRequest:
        return DurableBackupRequest(
            root=root,
            recipients=(recipient,),
            backend=backend,
            apply=apply,
        )

    def install_archive(
        self,
        base: Path,
        backend: FakeBackupBackend,
        receipt: DurableBackupReceipt,
        recipient: str,
        archive: Path,
        backup_set: str = "candidate",
    ) -> DurableBackupReceipt:
        original = next(item for item in receipt.sets if item.backup_set == backup_set)
        ciphertext = base / f"unsafe-{backup_set}.age"
        subprocess.run(
            [
                "age",
                "--encrypt",
                "--recipient",
                recipient,
                "--output",
                str(ciphertext),
                str(archive),
            ],
            check=True,
            capture_output=True,
        )
        payload = ciphertext.read_bytes()
        backend.assets[original.name] = payload
        remote = backend.inspect(name=original.name)
        replacement = EncryptedAsset(
            backup_set=original.backup_set,
            name=original.name,
            sha256=hashlib.sha256(payload).hexdigest(),
            size_bytes=len(payload),
            remote=remote,
        )
        updated_sets = tuple(
            replacement if item.backup_set == backup_set else item
            for item in receipt.sets
        )
        updated = replace(receipt, sets=updated_sets)
        outer_name = f"{receipt.backup_id}-{backup_set}.manifest.json"
        outer = json.loads(backend.assets[outer_name])
        outer.update(
            {
                "ciphertext_sha256": replacement.sha256,
                "ciphertext_size_bytes": replacement.size_bytes,
                "remote_asset_id": replacement.remote.asset_id,
            }
        )
        backend.assets[outer_name] = (
            json.dumps(outer, sort_keys=True, indent=2) + "\n"
        ).encode()
        return updated

    def test_source_inventory_rejects_symlinks_and_unsafe_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, _raw = self.make_root(base)
            inventory = build_source_asset_inventory(root)
            self.assertEqual(1, len(inventory))
            self.assertEqual("SRC-20260810-001", inventory[0].source_id)
            self.assertEqual(
                "01_Inbox/_assets/SRC-20260810-001/captured.bin",
                inventory[0].path,
            )

            outside = base / "outside.bin"
            outside.write_bytes(b"outside")
            link = root / "01_Inbox/_assets/SRC-20260810-001/escape.bin"
            link.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symlink"):
                build_source_asset_inventory(root)

    def test_receipt_path_rejects_invalid_backup_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "backup_id"):
                durable_backup.durable_receipt_path(root, "../../outside")

    def test_dry_run_preflights_without_local_or_remote_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, _raw = self.make_root(base)
            _identity, recipient = self.age_identity(base)
            backend = FakeBackupBackend()
            temp_parent = base / "temporary"
            temp_parent.mkdir()

            receipt = create_durable_backup(
                self.request(root, recipient, backend, apply=False),
                now="2026-08-10T01:02:03Z",
                backup_id="BKP-20260810T010203Z-aaaaaaaaaaaa",
                temp_parent=temp_parent,
            )

            self.assertEqual("dry_run", receipt.status)
            self.assertEqual(1, len(backend.preflight_calls))
            self.assertEqual({}, backend.assets)
            self.assertEqual([], list(temp_parent.iterdir()))
            self.assertFalse(
                (root / "09_Automation/operational/backups/durable").exists()
            )

    def test_apply_encrypts_both_sets_and_writes_only_safe_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, raw = self.make_root(base)
            identity, recipient = self.age_identity(base)
            backend = FakeBackupBackend()
            temp_parent = base / "temporary"
            temp_parent.mkdir()
            backup_id = "BKP-20260810T010203Z-bbbbbbbbbbbb"

            receipt = create_durable_backup(
                self.request(root, recipient, backend, apply=True),
                now="2026-08-10T01:02:03Z",
                backup_id=backup_id,
                temp_parent=temp_parent,
            )

            self.assertEqual("verified", receipt.status)
            self.assertEqual(
                {"candidate", "source_assets"}, {s.backup_set for s in receipt.sets}
            )
            self.assertEqual(4, len(backend.assets))
            self.assertEqual({0o700}, set(backend.temp_modes))
            self.assertEqual([], list(temp_parent.iterdir()))
            receipt_path = (
                root / "09_Automation/operational/backups/durable" / f"{backup_id}.json"
            )
            latest = receipt_path.with_name("latest-success.json")
            self.assertEqual(backup_id, json.loads(latest.read_text())["backup_id"])

            safe_metadata = receipt_path.read_bytes() + latest.read_bytes()
            for name, payload in backend.assets.items():
                if name.endswith(".manifest.json"):
                    safe_metadata += payload
            for sensitive in (
                recipient.encode(),
                str(identity).encode(),
                b"SRC-20260810-001",
                b"01_Inbox/_assets",
                raw,
            ):
                self.assertNotIn(sensitive, safe_metadata)

    def test_collision_and_partial_upload_never_advance_latest_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, _raw = self.make_root(base)
            _identity, recipient = self.age_identity(base)
            backup_id = "BKP-20260810T010203Z-cccccccccccc"
            temp_parent = base / "temporary"
            temp_parent.mkdir()
            durable = root / "09_Automation/operational/backups/durable"
            durable.mkdir(parents=True)
            latest = durable / "latest-success.json"
            latest.write_bytes(b'{"backup_id":"older"}\n')
            previous = latest.read_bytes()

            colliding = FakeBackupBackend()
            colliding.assets[f"{backup_id}-candidate.tar.age"] = b"existing"
            with self.assertRaises(FileExistsError):
                create_durable_backup(
                    self.request(root, recipient, colliding, apply=True),
                    now="2026-08-10T01:02:03Z",
                    backup_id=backup_id,
                    temp_parent=temp_parent,
                )
            self.assertEqual(previous, latest.read_bytes())

            failing = FakeBackupBackend(fail_upload_number=2)
            with self.assertRaisesRegex(RuntimeError, "partial upload"):
                create_durable_backup(
                    self.request(root, recipient, failing, apply=True),
                    now="2026-08-10T01:02:03Z",
                    backup_id=backup_id,
                    temp_parent=temp_parent,
                )
            self.assertGreaterEqual(len(failing.assets), 1)
            self.assertEqual(previous, latest.read_bytes())
            self.assertFalse((durable / f"{backup_id}.json").exists())
            self.assertEqual([], list(temp_parent.iterdir()))

    def test_age_failure_removes_all_plaintext_and_does_not_write_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, _raw = self.make_root(base)
            _identity, recipient = self.age_identity(base)
            backend = FakeBackupBackend()
            backup_id = "BKP-20260810T010203Z-ffffffffffff"
            temp_parent = base / "temporary"
            temp_parent.mkdir()

            def failing_age(
                argv: list[str], **_kwargs: object
            ) -> subprocess.CompletedProcess[bytes]:
                return subprocess.CompletedProcess(
                    argv,
                    1 if "--output" in argv else 0,
                    b"",
                    b"recipient details must not escape",
                )

            with (
                mock.patch(
                    "research_os.services.durable_backup.subprocess.run",
                    side_effect=failing_age,
                ),
                self.assertRaisesRegex(RuntimeError, "age encryption failed") as raised,
            ):
                create_durable_backup(
                    self.request(root, recipient, backend, apply=True),
                    now="2026-08-10T01:02:03Z",
                    backup_id=backup_id,
                    temp_parent=temp_parent,
                )

            self.assertNotIn(recipient, str(raised.exception))
            self.assertEqual([], list(temp_parent.iterdir()))
            self.assertEqual({}, backend.assets)
            self.assertFalse(
                (
                    root
                    / "09_Automation/operational/backups/durable"
                    / f"{backup_id}.json"
                ).exists()
            )

    def test_default_termination_signals_cleanup_owned_plaintext_workspaces(
        self,
    ) -> None:
        for operation in ("create", "restore"):
            for termination_signal in (signal.SIGTERM, signal.SIGHUP):
                with (
                    self.subTest(
                        operation=operation,
                        termination_signal=termination_signal.name,
                    ),
                    tempfile.TemporaryDirectory() as temp,
                ):
                    self.assert_signal_cleans_owned_workspace(
                        Path(temp),
                        operation=operation,
                        termination_signal=termination_signal,
                    )

    def test_plaintext_archive_integrity_is_verified_before_upload(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, _raw = self.make_root(base)
            _identity, recipient = self.age_identity(base)
            backend = FakeBackupBackend()
            backup_id = "BKP-20260810T010203Z-131313131313"
            source_asset = (
                root / "01_Inbox" / "_assets" / "SRC-20260810-001" / "captured.bin"
            )
            original_writer = durable_backup._write_candidate_archive

            def mutate_after_inventory(
                repository_root: Path,
                work: Path,
                *,
                backup_id: str,
                created_at: str,
                timestamp: int,
            ) -> Path:
                archive = original_writer(
                    repository_root,
                    work,
                    backup_id=backup_id,
                    created_at=created_at,
                    timestamp=timestamp,
                )
                source_asset.write_bytes(b"changed after inventory")
                return archive

            with (
                mock.patch(
                    "research_os.services.durable_backup._write_candidate_archive",
                    side_effect=mutate_after_inventory,
                ),
                self.assertRaisesRegex(DurableBackupError, "plaintext archive"),
            ):
                create_durable_backup(
                    self.request(root, recipient, backend, apply=True),
                    now="2026-08-10T01:02:03Z",
                    backup_id=backup_id,
                    temp_parent=base,
                )

            self.assertEqual({}, backend.assets)
            self.assertFalse(
                (
                    root
                    / "09_Automation/operational/backups/durable"
                    / f"{backup_id}.json"
                ).exists()
            )

    def test_cleanup_failure_is_reported_before_receipt_is_advanced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, _raw = self.make_root(base)
            _identity, recipient = self.age_identity(base)
            backend = FakeBackupBackend()
            backup_id = "BKP-20260810T010203Z-141414141414"
            durable = root / "09_Automation/operational/backups/durable"

            def fail_unless_ignored(
                _path: str | Path, *, ignore_errors: bool = False
            ) -> None:
                if not ignore_errors:
                    raise OSError("simulated cleanup failure")

            with (
                mock.patch(
                    "research_os.services.durable_backup.shutil.rmtree",
                    side_effect=fail_unless_ignored,
                ),
                self.assertRaisesRegex(DurableBackupError, "cleanup"),
            ):
                create_durable_backup(
                    self.request(root, recipient, backend, apply=True),
                    now="2026-08-10T01:02:03Z",
                    backup_id=backup_id,
                    temp_parent=base,
                )

            self.assertFalse((durable / f"{backup_id}.json").exists())
            self.assertFalse((durable / "latest-success.json").exists())

    def test_restore_verifies_candidate_and_source_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, raw = self.make_root(base)
            identity, recipient = self.age_identity(base)
            backend = FakeBackupBackend()
            backup_id = "BKP-20260810T010203Z-dddddddddddd"
            receipt = create_durable_backup(
                self.request(root, recipient, backend, apply=True),
                now="2026-08-10T01:02:03Z",
                backup_id=backup_id,
                temp_parent=base,
            )
            destination = base / "restore"

            restored = restore_durable_backup(
                root,
                receipt,
                backend=backend,
                identity=identity,
                destination=destination,
                temp_parent=base,
            )

            self.assertEqual("verified", restored.status)
            restored_db = destination / "09_Automation/operational/candidates.db"
            connection = sqlite3.connect(restored_db)
            try:
                count = connection.execute("SELECT COUNT(*) FROM candidates").fetchone()
            finally:
                connection.close()
            self.assertEqual((1,), count)
            self.assertEqual(
                raw,
                (
                    destination / "01_Inbox/_assets/SRC-20260810-001/captured.bin"
                ).read_bytes(),
            )

    def test_restore_rejects_backend_that_does_not_match_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, _raw = self.make_root(base)
            identity, recipient = self.age_identity(base)
            backend = FakeBackupBackend()
            receipt = create_durable_backup(
                self.request(root, recipient, backend, apply=True),
                now="2026-08-10T01:02:03Z",
                backup_id="BKP-20260810T010203Z-151515151515",
                temp_parent=base,
            )
            backend.repository = "other/private-research"
            destination = base / "wrong-backend-restore"

            with self.assertRaisesRegex(ValueError, "backend"):
                restore_durable_backup(
                    root,
                    receipt,
                    backend=backend,
                    identity=identity,
                    destination=destination,
                    temp_parent=base,
                )

            self.assertFalse(destination.exists())

    def test_restore_rejects_tamper_nonempty_and_live_destinations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, _raw = self.make_root(base)
            identity, recipient = self.age_identity(base)
            backend = FakeBackupBackend()
            backup_id = "BKP-20260810T010203Z-eeeeeeeeeeee"
            receipt = create_durable_backup(
                self.request(root, recipient, backend, apply=True),
                now="2026-08-10T01:02:03Z",
                backup_id=backup_id,
                temp_parent=base,
            )

            nonempty = base / "nonempty"
            nonempty.mkdir()
            (nonempty / "keep.txt").write_text("keep")
            with self.assertRaisesRegex(ValueError, "empty"):
                restore_durable_backup(
                    root,
                    receipt,
                    backend=backend,
                    identity=identity,
                    destination=nonempty,
                    temp_parent=base,
                )
            with self.assertRaisesRegex(ValueError, "authoritative"):
                restore_durable_backup(
                    root,
                    receipt,
                    backend=backend,
                    identity=identity,
                    destination=root / "01_Inbox/_assets/restore",
                    temp_parent=base,
                )

            ciphertext = next(
                name for name in backend.assets if name.endswith("candidate.tar.age")
            )
            backend.assets[ciphertext] += b"tamper"
            tampered_destination = base / "tampered"
            with self.assertRaisesRegex(ValueError, "ciphertext"):
                restore_durable_backup(
                    root,
                    receipt,
                    backend=backend,
                    identity=identity,
                    destination=tampered_destination,
                    temp_parent=base,
                )
            self.assertFalse(tampered_destination.exists())

    def test_restore_rejects_unsafe_tar_members_before_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, _raw = self.make_root(base)
            identity, recipient = self.age_identity(base)
            backend = FakeBackupBackend()
            receipt = create_durable_backup(
                self.request(root, recipient, backend, apply=True),
                now="2026-08-10T01:02:03Z",
                backup_id="BKP-20260810T010203Z-121212121212",
                temp_parent=base,
            )
            outside = base / "outside-restore"

            def regular(info: tarfile.TarInfo) -> tuple[tarfile.TarInfo, io.BytesIO]:
                payload = b"escape"
                info.size = len(payload)
                return info, io.BytesIO(payload)

            cases: dict[str, list[tuple[tarfile.TarInfo, io.BytesIO | None]]] = {}
            absolute, absolute_stream = regular(tarfile.TarInfo(str(outside)))
            cases["absolute"] = [(absolute, absolute_stream)]
            traversal, traversal_stream = regular(tarfile.TarInfo("../outside-restore"))
            cases["traversal"] = [(traversal, traversal_stream)]
            symbolic = tarfile.TarInfo("link")
            symbolic.type = tarfile.SYMTYPE
            symbolic.linkname = str(outside)
            cases["symlink"] = [(symbolic, None)]
            hard = tarfile.TarInfo("hard")
            hard.type = tarfile.LNKTYPE
            hard.linkname = "target"
            cases["hardlink"] = [(hard, None)]
            device = tarfile.TarInfo("device")
            device.type = tarfile.CHRTYPE
            device.devmajor = 1
            device.devminor = 3
            cases["device"] = [(device, None)]
            first, first_stream = regular(tarfile.TarInfo("duplicate"))
            second, second_stream = regular(tarfile.TarInfo("duplicate"))
            cases["duplicate"] = [(first, first_stream), (second, second_stream)]

            for label, members in cases.items():
                with self.subTest(label=label):
                    archive_path = base / f"unsafe-{label}.tar"
                    with tarfile.open(archive_path, "w") as archive:
                        for member, stream in members:
                            archive.addfile(member, stream)
                    unsafe_receipt = self.install_archive(
                        base,
                        backend,
                        receipt,
                        recipient,
                        archive_path,
                    )
                    destination = base / f"restore-{label}"
                    with self.assertRaisesRegex(
                        ValueError, "archive|member|link|device|duplicate"
                    ):
                        restore_durable_backup(
                            root,
                            unsafe_receipt,
                            backend=backend,
                            identity=identity,
                            destination=destination,
                            temp_parent=base,
                        )
                    self.assertFalse(destination.exists())
                    self.assertFalse(outside.exists())


class GitHubReleaseBackendTests(unittest.TestCase):
    def test_preflight_requires_private_prerelease_and_refuses_collisions(self) -> None:
        calls: list[list[str]] = []

        def runner(
            argv: list[str], **_kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            calls.append(argv)
            if argv[1:3] == ["repo", "view"]:
                return subprocess.CompletedProcess(argv, 0, '{"isPrivate":true}', "")
            return subprocess.CompletedProcess(
                argv,
                0,
                json.dumps(
                    {
                        "tagName": DURABLE_BACKUP_RELEASE_TAG,
                        "isPrerelease": True,
                        "assets": [{"name": "collision.age", "id": "1", "size": 3}],
                    }
                ),
                "",
            )

        backend = GitHubReleaseBackend("owner/repo", runner=runner)
        with self.assertRaises(FileExistsError):
            backend.preflight(("collision.age",))
        with self.assertRaisesRegex(ValueError, "name"):
            backend.preflight(("*.age",))
        self.assertTrue(all("--clobber" not in call for call in calls))

        def public_runner(
            argv: list[str], **_kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(argv, 0, '{"isPrivate":false}', "")

        public_backend = GitHubReleaseBackend("owner/repo", runner=public_runner)
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "new.age"
            source.write_bytes(b"ciphertext")
            operations = (
                lambda: public_backend.preflight(("new.age",)),
                lambda: public_backend.upload(source, name=source.name),
                lambda: public_backend.inspect(name=source.name),
                lambda: public_backend.download(
                    name=source.name,
                    destination=Path(temp) / "download.age",
                ),
            )
            for operation in operations:
                with (
                    self.subTest(operation=operation),
                    self.assertRaisesRegex(ValueError, "private"),
                ):
                    operation()

    def test_upload_inspect_and_download_use_immutable_fixed_release(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "backup.age"
            source.write_bytes(b"encrypted backup")
            calls: list[list[str]] = []
            assets: dict[str, bytes] = {}

            def runner(
                argv: list[str], **_kwargs: object
            ) -> subprocess.CompletedProcess[str]:
                calls.append(argv)
                command = argv[1:3]
                if command == ["repo", "view"]:
                    return subprocess.CompletedProcess(
                        argv, 0, '{"isPrivate":true}', ""
                    )
                if command == ["release", "view"]:
                    metadata = [
                        {
                            "name": name,
                            "id": f"asset-{name}",
                            "size": len(payload),
                        }
                        for name, payload in assets.items()
                    ]
                    return subprocess.CompletedProcess(
                        argv,
                        0,
                        json.dumps(
                            {
                                "tagName": DURABLE_BACKUP_RELEASE_TAG,
                                "isPrerelease": True,
                                "assets": metadata,
                            }
                        ),
                        "",
                    )
                if command == ["release", "upload"]:
                    uploaded = Path(argv[4])
                    assets[uploaded.name] = uploaded.read_bytes()
                    return subprocess.CompletedProcess(argv, 0, "", "")
                if command == ["release", "download"]:
                    name = argv[argv.index("--pattern") + 1]
                    destination = Path(argv[argv.index("--output") + 1])
                    destination.write_bytes(assets[name])
                    return subprocess.CompletedProcess(argv, 0, "", "")
                raise AssertionError(f"unexpected command: {argv}")

            backend = GitHubReleaseBackend("owner/repo", runner=runner)
            uploaded = backend.upload(source, name=source.name)
            self.assertEqual(uploaded, backend.inspect(name=source.name))

            destination = base / "downloaded.age"
            backend.download(name=source.name, destination=destination)
            self.assertEqual(source.read_bytes(), destination.read_bytes())
            with self.assertRaises(FileExistsError):
                backend.upload(source, name=source.name)

            release_calls = [call for call in calls if call[1] == "release"]
            self.assertTrue(
                all(DURABLE_BACKUP_RELEASE_TAG in call for call in release_calls)
            )
            self.assertTrue(all("--clobber" not in call for call in calls))


if __name__ == "__main__":
    unittest.main()
