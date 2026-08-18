from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from research_os.services.operations_db import operations_db_path
from research_os.services.runtime_identity import (
    RuntimeIdentity,
    RuntimePreflightError,
    preflight_product_runtime,
    repository_root_from_package,
)
from research_os.ui.app import create_app
from test_m5_dashboard_jobs import prepared_root


def _repository_markers(root: Path) -> None:
    (root / "00_System").mkdir(parents=True)
    (root / "09_Automation" / "operational").mkdir(parents=True)
    (root / "src" / "research_os" / "ui").mkdir(parents=True)
    (root / "README.md").write_text("# test\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (root / "00_System" / "Research_Rules.md").write_text("# rules\n", encoding="utf-8")


def test_repository_root_is_derived_from_imported_package_not_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "canonical"
    _repository_markers(root)
    package_file = root / "src" / "research_os" / "ui" / "__main__.py"
    package_file.write_text("", encoding="utf-8")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    assert repository_root_from_package(package_file) == root.resolve()


def test_preflight_rejects_linked_worktree_before_creating_runtime_db(
    tmp_path: Path,
) -> None:
    root = tmp_path / "linked-worktree"
    _repository_markers(root)
    (root / ".git").write_text("gitdir: ../.git/worktrees/test\n", encoding="utf-8")
    package_file = root / "src" / "research_os" / "__init__.py"
    package_file.write_text("", encoding="utf-8")

    with pytest.raises(RuntimePreflightError, match="linked Git worktree"):
        preflight_product_runtime(root, package_file=package_file)

    assert not operations_db_path(root).exists()


def test_preflight_rejects_code_and_data_root_mismatch_before_writes(
    tmp_path: Path,
) -> None:
    code_root = tmp_path / "code"
    data_root = tmp_path / "data"
    _repository_markers(code_root)
    _repository_markers(data_root)
    (data_root / ".git").mkdir()
    package_file = code_root / "src" / "research_os" / "__init__.py"
    package_file.write_text("", encoding="utf-8")

    with pytest.raises(RuntimePreflightError, match="code root does not match"):
        preflight_product_runtime(data_root, package_file=package_file)

    assert not operations_db_path(data_root).exists()


def test_health_displays_verified_runtime_fingerprint(tmp_path: Path) -> None:
    root = prepared_root(str(tmp_path))
    identity = RuntimeIdentity(
        status="verified",
        root=str(root),
        branch="codex/web-only-parity",
        commit="abc123",
        dirty=False,
        interpreter="/runtime/python",
        package_path=str(root / "src" / "research_os" / "__init__.py"),
        candidate_db={"path": str(root / "candidates.db"), "status": "ok"},
        operations_db={"path": str(root / "operations.db"), "status": "present"},
        config_paths={"llm": str(root / "00_System" / "llm.local.json")},
    )

    response = TestClient(create_app(root, runtime_identity=identity)).get("/health")

    assert response.status_code == 200
    assert "codex/web-only-parity" in response.text
    assert "abc123" in response.text
    assert str(root) in response.text


def test_preflight_rejects_corrupt_operations_db(tmp_path: Path) -> None:
    root = tmp_path / "canonical"
    _repository_markers(root)
    (root / ".git").mkdir()
    package_file = root / "src" / "research_os" / "__init__.py"
    package_file.write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    candidate_db_path = root / "09_Automation" / "operational" / "candidates.db"
    from research_os.services.candidate_db import apply_migrations

    apply_migrations(candidate_db_path)
    operations_db_path(root).write_bytes(b"not a sqlite database")

    with pytest.raises(RuntimePreflightError, match="Operations DB is not ready"):
        preflight_product_runtime(root, package_file=package_file)
