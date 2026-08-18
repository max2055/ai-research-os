"""Private GitHub prerelease backend for immutable durable backup assets."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Protocol, cast

from research_os.services.durable_backup import RemoteAsset, canonical_github_repository

DURABLE_BACKUP_RELEASE_TAG = "research-os-durable-backups-v1"
_ASSET_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}")


class CommandRunner(Protocol):
    def __call__(
        self, argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]: ...


class GitHubReleaseBackend:
    """Store immutable ciphertext on one private GitHub prerelease."""

    release_tag = DURABLE_BACKUP_RELEASE_TAG

    def __init__(
        self,
        repository: str,
        *,
        runner: CommandRunner | None = None,
        gh_binary: str = "gh",
    ) -> None:
        if not gh_binary or any(character.isspace() for character in gh_binary):
            raise ValueError("gh binary name is invalid")
        self.repository = canonical_github_repository(repository)
        self._runner = (
            runner if runner is not None else cast(CommandRunner, subprocess.run)
        )
        self._gh_binary = gh_binary

    def _run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        result = self._runner(
            [self._gh_binary, *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError("GitHub backup backend command failed")
        return result

    def _release(self) -> dict[str, Any]:
        result = self._run(
            [
                "release",
                "view",
                self.release_tag,
                "--repo",
                self.repository,
                "--json",
                "tagName,isPrerelease,assets",
            ]
        )
        try:
            payload: object = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GitHub backup release metadata is invalid") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("GitHub backup release metadata is invalid")
        return cast(dict[str, Any], payload)

    def _verify_private_repository(self) -> None:
        result = self._run(["repo", "view", self.repository, "--json", "isPrivate"])
        try:
            payload: object = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GitHub repository metadata is invalid") from exc
        if not isinstance(payload, dict) or payload.get("isPrivate") is not True:
            raise ValueError("durable backup repository must be private")

    def _assets(self) -> dict[str, RemoteAsset]:
        payload = self._release()
        if (
            payload.get("tagName") != self.release_tag
            or payload.get("isPrerelease") is not True
        ):
            raise ValueError("GitHub backup release must be the fixed prerelease")
        raw_assets = payload.get("assets")
        if not isinstance(raw_assets, list):
            raise RuntimeError("GitHub backup release assets are invalid")
        assets: dict[str, RemoteAsset] = {}
        for item in raw_assets:
            if not isinstance(item, dict):
                raise RuntimeError("GitHub backup release asset is invalid")
            name = item.get("name")
            asset_id = item.get("id")
            size = item.get("size")
            if (
                not isinstance(name, str)
                or not isinstance(size, int)
                or isinstance(size, bool)
                or size < 0
                or not isinstance(asset_id, str | int)
            ):
                raise RuntimeError("GitHub backup release asset is invalid")
            if name in assets:
                raise RuntimeError("GitHub backup release contains duplicate assets")
            assets[name] = RemoteAsset(name, str(asset_id), size)
        return assets

    @staticmethod
    def _validate_asset_name(name: str) -> str:
        if (
            not name
            or Path(name).name != name
            or _ASSET_NAME_PATTERN.fullmatch(name) is None
            or any(character in name for character in "\r\n\x00")
        ):
            raise ValueError("remote backup asset name is invalid")
        return name

    def preflight(self, asset_names: tuple[str, ...]) -> None:
        if len(asset_names) != len(set(asset_names)):
            raise ValueError("remote backup asset names must be unique")
        for name in asset_names:
            self._validate_asset_name(name)
        self._verify_private_repository()
        collisions = sorted(set(asset_names).intersection(self._assets()))
        if collisions:
            raise FileExistsError(
                "remote durable backup asset already exists: " + ", ".join(collisions)
            )

    def upload(self, path: Path, *, name: str) -> RemoteAsset:
        name = self._validate_asset_name(name)
        if path.name != name or not path.is_file():
            raise ValueError("upload path must be an existing matching asset name")
        self._verify_private_repository()
        if name in self._assets():
            raise FileExistsError(f"remote durable backup asset already exists: {name}")
        self._run(
            [
                "release",
                "upload",
                self.release_tag,
                str(path),
                "--repo",
                self.repository,
            ]
        )
        return self.inspect(name=name)

    def inspect(self, *, name: str) -> RemoteAsset:
        name = self._validate_asset_name(name)
        self._verify_private_repository()
        try:
            return self._assets()[name]
        except KeyError as exc:
            raise FileNotFoundError(
                f"remote durable backup asset is missing: {name}"
            ) from exc

    def download(self, *, name: str, destination: Path) -> None:
        name = self._validate_asset_name(name)
        if destination.exists():
            raise FileExistsError(destination)
        self._verify_private_repository()
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._run(
            [
                "release",
                "download",
                self.release_tag,
                "--repo",
                self.repository,
                "--pattern",
                name,
                "--output",
                str(destination),
            ]
        )
        if not destination.is_file():
            raise RuntimeError("GitHub backup asset download did not produce a file")


GitHubPrivateReleaseBackend = GitHubReleaseBackend
