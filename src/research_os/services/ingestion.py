"""Atomic Source capture, versioning, deduplication and processing."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_os.adapters.base import CaptureAdapter, CapturedAsset
from research_os.adapters.url import canonicalize_url
from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.repositories.markdown import MarkdownDocument
from research_os.repositories.transaction import FileTransaction
from research_os.services.drafts import (
    prepare_source_draft,
    yaml_list,
)
from research_os.services.extraction import extract_text
from research_os.services.validation import validate_repository


@dataclass(frozen=True)
class DuplicateMatch:
    source_id: str
    reason: str


@dataclass(frozen=True)
class CapturePlan:
    source_path: Path
    source_content: str
    assets: dict[Path, bytes]
    content_sha256: str
    canonical_url: str | None
    published_date_proposal: str | None
    duplicate_matches: tuple[DuplicateMatch, ...]


@dataclass(frozen=True)
class AssetVerification:
    source_id: str
    status: str
    message: str


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _source_id_from_path(path: Path) -> str:
    match = re.match(r"^(SRC-\d{8}-\d{3})", path.name)
    if not match:
        raise ValueError(f"cannot derive Source ID from {path}")
    return match.group(1)


def _extension(asset: CapturedAsset) -> str:
    known = {
        "text/html": ".html",
        "application/xhtml+xml": ".html",
        "application/pdf": ".pdf",
        "text/plain": ".txt",
        "application/json": ".json",
    }
    media_type = asset.media_type.split(";", 1)[0].lower()
    guessed = mimetypes.guess_extension(media_type) or ".bin"
    return known.get(media_type, guessed)


def _version_stem(asset: CapturedAsset, digest: str) -> str:
    timestamp = re.sub(r"[^0-9]", "", asset.captured_at)[:14]
    if len(timestamp) < 8:
        raise ValueError("captured_at must be an ISO date-time")
    return f"{timestamp}-{digest[:12]}"


def _asset_records(
    source_id: str,
    asset: CapturedAsset,
    digest: str,
) -> tuple[Path, Path, dict[Path, bytes]]:
    base = Path("01_Inbox/_assets") / source_id
    stem = _version_stem(asset, digest)
    raw_path = base / f"{stem}{_extension(asset)}"
    metadata_path = base / f"{stem}.metadata.json"
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "source_id": source_id,
        "captured_at": asset.captured_at,
        "original_locator": asset.original_locator,
        "final_locator": asset.final_locator,
        "media_type": asset.media_type,
        "content_sha256": digest,
        "byte_count": len(asset.content),
        "published_date_proposal": asset.published_date_proposal,
        "raw_asset_path": str(raw_path),
        "capture_metadata": asset.metadata,
    }
    return (
        raw_path,
        metadata_path,
        {
            raw_path: asset.content,
            metadata_path: (
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8"),
        },
    )


def duplicate_matches(
    objects: list[ResearchObject],
    *,
    canonical_url: str | None,
    content_sha256: str,
    exclude_source_id: str | None = None,
) -> tuple[DuplicateMatch, ...]:
    matches: list[DuplicateMatch] = []
    for obj in objects:
        if obj.object_type != "source" or obj.object_id == exclude_source_id:
            continue
        if canonical_url and obj.metadata.get("canonical_url") == canonical_url:
            matches.append(DuplicateMatch(obj.object_id, "canonical_url"))
        if obj.metadata.get("content_sha256") == content_sha256:
            matches.append(DuplicateMatch(obj.object_id, "content_sha256"))
    return tuple(
        sorted(
            set(matches),
            key=lambda match: (match.source_id, match.reason),
        )
    )


def _canonical_locator(asset: CapturedAsset) -> str | None:
    if asset.final_locator.startswith(("http://", "https://")):
        return canonicalize_url(asset.final_locator)
    return None


def _populate_capture_metadata(
    content: str,
    *,
    canonical_url: str | None,
    asset_paths: list[Path],
    digest: str,
    asset: CapturedAsset,
    upstream_source_ids: list[str],
) -> str:
    replacements = {
        r"(?m)^canonical_url:.*$": (f"canonical_url: {canonical_url or ''}"),
        r"(?m)^asset_paths:.*$": (
            f"asset_paths: {yaml_list([str(path) for path in asset_paths])}"
        ),
        r"(?m)^content_sha256:.*$": f"content_sha256: {digest}",
        r"(?m)^fetched_at:.*$": f"fetched_at: {asset.captured_at}",
        r"(?m)^upstream_source_ids:.*$": (
            f"upstream_source_ids: {yaml_list(upstream_source_ids)}"
        ),
        r"(?m)^processing_status:.*$": "processing_status: captured",
        r"(?m)^processing_error:.*$": "processing_error:",
        r"(?m)^published_date_proposal:.*$": (
            f"published_date_proposal: {asset.published_date_proposal or ''}"
        ),
    }
    updated = content
    for pattern, replacement in replacements.items():
        updated, count = re.subn(pattern, replacement, updated, count=1)
        if count != 1:
            raise ValueError(f"generated Source is missing capture field {pattern}")
    return updated


def prepare_new_source_capture(
    root: Path,
    adapter: CaptureAdapter,
    *,
    title: str,
    slug: str,
    created_at: str,
    source_type: str,
    publisher: str,
    published_at: str,
    source_grade: str,
    companies: list[str],
    technologies: list[str],
    products: list[str],
    tags: list[str],
    project_ids: list[str],
    allow_duplicate: bool = False,
) -> CapturePlan:
    root = root.resolve()
    asset = adapter.capture()
    digest = sha256_bytes(asset.content)
    canonical_url = _canonical_locator(asset)
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before Source capture")
    duplicates = duplicate_matches(
        objects,
        canonical_url=canonical_url,
        content_sha256=digest,
    )
    if duplicates and not allow_duplicate:
        detail = ", ".join(f"{match.source_id}:{match.reason}" for match in duplicates)
        raise ValueError(f"duplicate Source candidate: {detail}")
    url = canonical_url or ""
    local_path = "" if canonical_url else asset.final_locator
    source_path, source_content = prepare_source_draft(
        root,
        title=title,
        slug=slug,
        created_at=created_at,
        source_type=source_type,
        publisher=publisher,
        published_at=published_at,
        url=url,
        local_path=local_path,
        source_grade=source_grade,
        companies=companies,
        technologies=technologies,
        products=products,
        tags=tags,
        project_ids=project_ids,
    )
    source_id = _source_id_from_path(source_path)
    raw_path, metadata_path, assets = _asset_records(
        source_id,
        asset,
        digest,
    )
    upstream = sorted({match.source_id for match in duplicates})
    source_content = _populate_capture_metadata(
        source_content,
        canonical_url=canonical_url,
        asset_paths=[raw_path, metadata_path],
        digest=digest,
        asset=asset,
        upstream_source_ids=upstream,
    )
    return CapturePlan(
        source_path=source_path,
        source_content=source_content,
        assets=assets,
        content_sha256=digest,
        canonical_url=canonical_url,
        published_date_proposal=asset.published_date_proposal,
        duplicate_matches=duplicates,
    )


def commit_new_source_capture(
    root: Path,
    plan: CapturePlan,
) -> list[Path]:
    transaction = FileTransaction(root)
    transaction.stage_create(plan.source_path, plan.source_content)
    for path, content in plan.assets.items():
        transaction.stage_create_bytes(path, content)
    return transaction.commit()


def _source_by_id(
    root: Path,
    source_id: str,
) -> tuple[ResearchObject, list[ResearchObject]]:
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before Source operation")
    source = next(
        (
            obj
            for obj in objects
            if obj.object_id == source_id and obj.object_type == "source"
        ),
        None,
    )
    if source is None:
        raise ValueError(f"unknown Source {source_id}")
    return source, objects


def capture_existing_source(
    root: Path,
    source_id: str,
    adapter: CaptureAdapter,
    *,
    allow_duplicate: bool = False,
) -> list[Path]:
    root = root.resolve()
    source, objects = _source_by_id(root, source_id)
    asset = adapter.capture()
    digest = sha256_bytes(asset.content)
    canonical_url = _canonical_locator(asset)
    if source.metadata.get("content_sha256") == digest:
        raise ValueError(f"Source {source_id} content is unchanged")
    duplicates = duplicate_matches(
        objects,
        canonical_url=canonical_url,
        content_sha256=digest,
        exclude_source_id=source_id,
    )
    if duplicates and not allow_duplicate:
        detail = ", ".join(f"{match.source_id}:{match.reason}" for match in duplicates)
        raise ValueError(f"captured content duplicates another Source: {detail}")
    raw_path, metadata_path, assets = _asset_records(
        source_id,
        asset,
        digest,
    )
    document = MarkdownDocument.read(source.path)
    prior_paths = [str(path) for path in source.metadata.get("asset_paths", [])]
    document.set_metadata(
        "asset_paths",
        [*prior_paths, str(raw_path), str(metadata_path)],
    )
    document.set_metadata("content_sha256", digest)
    document.set_metadata("fetched_at", asset.captured_at)
    document.set_metadata("processing_status", "captured")
    document.set_metadata("processing_error", None)
    if canonical_url:
        document.set_metadata("canonical_url", canonical_url)
    document.set_metadata(
        "published_date_proposal",
        asset.published_date_proposal,
    )
    if duplicates:
        upstream = {
            str(value) for value in source.metadata.get("upstream_source_ids", [])
        }
        upstream.update(match.source_id for match in duplicates)
        document.set_metadata("upstream_source_ids", sorted(upstream))
    transaction = FileTransaction(root)
    transaction.stage_replace(source.path, document.render())
    for path, content in assets.items():
        transaction.stage_create_bytes(path, content)
    return transaction.commit()


def _record_processing_failure(
    root: Path,
    source: ResearchObject,
    error: Exception,
) -> None:
    document = MarkdownDocument.read(source.path)
    document.set_metadata("processing_status", "failed")
    document.set_metadata(
        "processing_error",
        f"{type(error).__name__}: {error}"[:500],
    )
    transaction = FileTransaction(root)
    transaction.stage_replace(source.path, document.render())
    transaction.commit()


def _process_source_asset(
    root: Path,
    source: ResearchObject,
    source_id: str,
) -> list[Path]:
    manifests = [
        root / str(path)
        for path in source.metadata.get("asset_paths", [])
        if str(path).endswith(".metadata.json")
    ]
    if not manifests:
        raise ValueError(f"Source {source_id} has no captured asset manifest")
    manifest_path = manifests[-1]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_relative = Path(str(manifest["raw_asset_path"]))
    raw_path = root / raw_relative
    content = raw_path.read_bytes()
    digest = sha256_bytes(content)
    if digest != manifest["content_sha256"]:
        raise ValueError(f"asset hash mismatch for {raw_relative}")
    result = extract_text(content, str(manifest["media_type"]))
    extracted_relative = raw_relative.with_suffix(
        raw_relative.suffix + ".extracted.txt"
    )
    extraction_metadata = raw_relative.with_suffix(
        raw_relative.suffix + ".extraction.json"
    )
    extracted_exists = (root / extracted_relative).exists()
    metadata_exists = (root / extraction_metadata).exists()
    if extracted_exists and metadata_exists:
        prior_record = json.loads(
            (root / extraction_metadata).read_text(encoding="utf-8")
        )
        if (
            source.metadata.get("processing_status") == "processed"
            and prior_record.get("raw_content_sha256") == digest
        ):
            return []
    if extracted_exists or metadata_exists:
        raise FileExistsError(f"refusing to overwrite extraction: {extracted_relative}")
    extraction_record = {
        "schema_version": 1,
        "source_id": source_id,
        "raw_asset_path": str(raw_relative),
        "raw_content_sha256": digest,
        "extraction_method": result.method,
        "warnings": list(result.warnings),
        "text_sha256": sha256_bytes(result.text.encode("utf-8")),
    }
    document = MarkdownDocument.read(source.path)
    paths = [str(path) for path in source.metadata.get("asset_paths", [])]
    paths.extend([str(extracted_relative), str(extraction_metadata)])
    document.set_metadata("asset_paths", paths)
    document.set_metadata("processing_status", "processed")
    document.set_metadata("processing_error", None)
    transaction = FileTransaction(root)
    transaction.stage_replace(source.path, document.render())
    transaction.stage_create(extracted_relative, result.text)
    transaction.stage_create(
        extraction_metadata,
        json.dumps(
            extraction_record,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    return transaction.commit()


def process_source_asset(root: Path, source_id: str) -> list[Path]:
    root = root.resolve()
    source, _ = _source_by_id(root, source_id)
    try:
        return _process_source_asset(root, source, source_id)
    except Exception as error:
        _record_processing_failure(root, source, error)
        raise


def confirm_published_date(
    root: Path,
    source_id: str,
    confirmed_date: str,
    *,
    allow_proposal_override: bool = False,
) -> Path:
    if not is_iso_date(confirmed_date):
        raise ValueError("confirmed date must be YYYY-MM-DD")
    source, _ = _source_by_id(root, source_id)
    proposal = source.metadata.get("published_date_proposal")
    if proposal and proposal != confirmed_date and not allow_proposal_override:
        raise ValueError(
            f"confirmed date differs from proposal {proposal}; "
            "explicit override required"
        )
    document = MarkdownDocument.read(source.path)
    document.set_metadata("published_at", confirmed_date)
    document.set_metadata("published_date_proposal", None)
    transaction = FileTransaction(root)
    transaction.stage_replace(source.path, document.render())
    return transaction.commit()[0]


def verify_source_assets(root: Path) -> list[AssetVerification]:
    root = root.resolve()
    objects, _ = validate_repository(root)
    results: list[AssetVerification] = []
    for source in sorted(
        (obj for obj in objects if obj.object_type == "source"),
        key=lambda obj: obj.object_id,
    ):
        paths = [Path(str(value)) for value in source.metadata.get("asset_paths", [])]
        if not paths:
            results.append(
                AssetVerification(
                    source.object_id,
                    "registered",
                    "no archived assets",
                )
            )
            continue
        missing = [str(path) for path in paths if not (root / path).is_file()]
        if missing:
            results.append(
                AssetVerification(
                    source.object_id,
                    "missing",
                    ", ".join(missing),
                )
            )
            continue
        manifests = [
            root / path for path in paths if str(path).endswith(".metadata.json")
        ]
        if not manifests:
            results.append(
                AssetVerification(
                    source.object_id,
                    "invalid",
                    "asset manifest missing",
                )
            )
            continue
        manifest = json.loads(manifests[-1].read_text(encoding="utf-8"))
        raw_path = root / str(manifest["raw_asset_path"])
        actual = sha256_bytes(raw_path.read_bytes())
        expected = str(source.metadata.get("content_sha256"))
        status = "ok" if actual == expected else "hash_mismatch"
        results.append(
            AssetVerification(
                source.object_id,
                status,
                f"expected={expected} actual={actual}",
            )
        )
    return results
