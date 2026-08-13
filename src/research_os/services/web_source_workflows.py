"""Website preparation adapters for bounded Source workflows."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from research_os.adapters.base import CaptureAdapter, CapturedAsset
from research_os.adapters.url import UrlCaptureAdapter, propose_html_published_date
from research_os.services.drafts import split_values
from research_os.services.ingestion import (
    prepare_existing_source_capture,
    prepare_new_source_capture,
    prepare_published_date_confirmation,
    prepare_source_processing,
)
from research_os.services.web_repository_mutations import (
    PreparedRepositoryMutation,
    prepare_repository_mutation,
)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@dataclass(frozen=True)
class UploadedCaptureAdapter:
    filename: str
    content: bytes
    captured_at: str | None = None

    def capture(self) -> CapturedAsset:
        if not self.filename or Path(self.filename).name != self.filename:
            raise ValueError("upload filename must be a basename")
        if not self.content:
            raise ValueError("uploaded Source file is empty")
        if len(self.content) > MAX_UPLOAD_BYTES:
            raise ValueError(f"uploaded Source exceeds {MAX_UPLOAD_BYTES} byte limit")
        media_type = (
            mimetypes.guess_type(self.filename)[0] or "application/octet-stream"
        )
        proposal = (
            propose_html_published_date(self.content)
            if media_type in {"text/html", "application/xhtml+xml"}
            else None
        )
        captured_at = self.captured_at or datetime.now(UTC).isoformat()
        locator = f"web-upload://{self.filename}"
        return CapturedAsset(
            content=self.content,
            media_type=media_type,
            original_locator=locator,
            final_locator=locator,
            captured_at=captured_at,
            published_date_proposal=proposal,
            metadata={"filename": self.filename, "source_size": str(len(self.content))},
        )


def capture_adapter(
    *,
    capture_mode: str,
    locator: str,
    upload_filename: str | None = None,
    upload_content: bytes | None = None,
) -> CaptureAdapter:
    if capture_mode == "url":
        if upload_content:
            raise ValueError("URL capture cannot include an uploaded file")
        return UrlCaptureAdapter(locator)
    if capture_mode == "upload":
        if locator.strip():
            raise ValueError("upload capture cannot include a URL")
        return UploadedCaptureAdapter(upload_filename or "", upload_content or b"")
    raise ValueError("capture_mode must be url or upload")


def prepare_source_create(
    root: Path,
    *,
    actor: str,
    adapter: CaptureAdapter,
    fields: dict[str, str],
) -> PreparedRepositoryMutation:
    plan = prepare_new_source_capture(
        root,
        adapter,
        title=fields["title"],
        slug=fields["slug"],
        created_at=fields["created_at"],
        source_type=fields["source_type"],
        publisher=fields["publisher"],
        published_at=fields["published_at"],
        source_grade=fields["source_grade"],
        companies=split_values(fields.get("companies")),
        technologies=split_values(fields.get("technologies")),
        products=split_values(fields.get("products")),
        tags=split_values(fields.get("tags")),
        project_ids=split_values(fields.get("project_ids")) or ["PRJ-001"],
        allow_duplicate=fields.get("allow_duplicate") == "true",
    )
    source_id = plan.source_path.name.split("-")[:3]
    target_id = "-".join(source_id)
    writes = {
        plan.source_path: plan.source_content.encode("utf-8"),
        **plan.assets,
    }
    return prepare_repository_mutation(
        root,
        operation="source.create",
        actor=actor,
        target_type="source",
        target_id=target_id,
        writes=writes,
        normalized_input={
            "title": fields["title"],
            "publisher": fields["publisher"],
            "source_type": fields["source_type"],
            "source_grade": fields["source_grade"],
            "content_sha256": plan.content_sha256,
            "canonical_url": plan.canonical_url,
            "published_date_proposal": plan.published_date_proposal,
            "duplicate_matches": [
                f"{item.source_id}:{item.reason}" for item in plan.duplicate_matches
            ],
        },
        summary={"status_after": "pending", "asset_count": len(plan.assets)},
    )


def prepare_source_fetch(
    root: Path,
    source_id: str,
    *,
    actor: str,
    adapter: CaptureAdapter,
    allow_duplicate: bool = False,
) -> PreparedRepositoryMutation:
    plan = prepare_existing_source_capture(
        root, source_id, adapter, allow_duplicate=allow_duplicate
    )
    return prepare_repository_mutation(
        root,
        operation="source.fetch",
        actor=actor,
        target_type="source",
        target_id=source_id,
        writes=plan.writes,
        normalized_input=plan.summary,
        summary={"status_after": "captured", **plan.summary},
    )


def prepare_source_process(
    root: Path,
    source_id: str,
    *,
    actor: str,
) -> PreparedRepositoryMutation:
    plan = prepare_source_processing(root, source_id)
    return prepare_repository_mutation(
        root,
        operation="source.process",
        actor=actor,
        target_type="source",
        target_id=source_id,
        writes=plan.writes,
        normalized_input=plan.summary,
        summary=plan.summary,
    )


def prepare_source_date_confirmation(
    root: Path,
    source_id: str,
    *,
    actor: str,
    confirmed_date: str,
    allow_proposal_override: bool,
) -> PreparedRepositoryMutation:
    plan = prepare_published_date_confirmation(
        root,
        source_id,
        confirmed_date,
        allow_proposal_override=allow_proposal_override,
    )
    return prepare_repository_mutation(
        root,
        operation="source.confirm_date",
        actor=actor,
        target_type="source",
        target_id=source_id,
        writes=plan.writes,
        normalized_input=plan.summary,
        summary=plan.summary,
    )
