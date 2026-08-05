#!/usr/bin/env python3
"""Validate and apply explicit human decisions from the Stage 3 review packet."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from research_os.services.reviews import apply_review

EVENT_ID_RE = re.compile(r"^EVT-\d{8}-\d{3}$")
FIELD_RE_TEMPLATE = r"(?m)^{field}:\s*(.*?)\s*$"


@dataclass(frozen=True)
class Decision:
    event_id: str
    checked: bool
    action: str
    detail: str


class ReviewError(ValueError):
    pass


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Validate Stage 3 Event decisions; modify files only with --apply."
    )
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--reviewer",
        help="Required with --apply; recorded in each Event review record.",
    )
    parser.add_argument(
        "--review-date",
        default=date.today().isoformat(),
        help="ISO date recorded on apply (default: today).",
    )
    return parser.parse_args()


def parse_decision(raw: str) -> tuple[str, str]:
    value = raw.strip()
    if not value:
        return "pending", ""
    if value == "approve":
        return "approve", ""
    for action in ("edit", "reject"):
        prefix = f"{action}:"
        if value.startswith(prefix) and value[len(prefix) :].strip():
            return action, value[len(prefix) :].strip()
    raise ReviewError(
        f"invalid decision {value!r}; use approve, edit: <instruction>, "
        "reject: <reason>, or leave blank"
    )


def parse_packet(packet: Path) -> list[Decision]:
    decisions: list[Decision] = []
    for line_number, line in enumerate(
        packet.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.startswith("| ["):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6 or not EVENT_ID_RE.fullmatch(cells[1]):
            continue
        marker = cells[0].lower()
        if marker not in {"[ ]", "[x]"}:
            raise ReviewError(f"{packet}:{line_number}: invalid checkbox {cells[0]!r}")
        try:
            action, detail = parse_decision(cells[5])
        except ReviewError as exc:
            raise ReviewError(f"{packet}:{line_number}: {exc}") from exc
        checked = marker == "[x]"
        if checked != (action != "pending"):
            raise ReviewError(
                f"{packet}:{line_number}: checkbox and decision must be filled together"
            )
        decisions.append(Decision(cells[1], checked, action, detail))
    if not decisions:
        raise ReviewError(f"no Event review rows found in {packet}")
    ids = [decision.event_id for decision in decisions]
    duplicates = sorted({event_id for event_id in ids if ids.count(event_id) > 1})
    if duplicates:
        raise ReviewError(f"duplicate Event rows: {', '.join(duplicates)}")
    return decisions


def read_field(text: str, field: str, path: Path) -> str:
    match = re.search(FIELD_RE_TEMPLATE.format(field=re.escape(field)), text)
    if not match:
        raise ReviewError(f"{path}: missing front-matter field {field}")
    return match.group(1)


def event_files(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    events_dir = root / "04_Evidence" / "Events"
    for path in sorted(events_dir.glob("EVT-*.md")):
        event_id = path.name.split("-", 4)
        if len(event_id) < 4:
            continue
        text = path.read_text(encoding="utf-8")
        object_id = read_field(text, "id", path)
        if object_id in result:
            raise ReviewError(f"duplicate Event id {object_id}")
        result[object_id] = path
    return result


def validate(
    decisions: list[Decision], files: dict[str, Path], *, applying: bool
) -> list[str]:
    messages: list[str] = []
    packet_ids = {decision.event_id for decision in decisions}
    file_ids = set(files)
    if packet_ids != file_ids:
        missing_rows = sorted(file_ids - packet_ids)
        missing_files = sorted(packet_ids - file_ids)
        if missing_rows:
            messages.append("packet missing Event rows: " + ", ".join(missing_rows))
        if missing_files:
            messages.append("Event files missing: " + ", ".join(missing_files))

    for decision in decisions:
        if decision.event_id not in files:
            continue
        text = files[decision.event_id].read_text(encoding="utf-8")
        current = read_field(text, "review_status", files[decision.event_id])
        if current not in {"pending", "reviewed", "rejected", "superseded"}:
            messages.append(f"{decision.event_id}: invalid review_status {current!r}")
        if applying:
            if decision.action == "pending":
                messages.append(f"{decision.event_id}: decision is blank")
            elif decision.action == "edit":
                messages.append(
                    f"{decision.event_id}: edit requested and must be resolved first"
                )
            elif current != "pending":
                target = "reviewed" if decision.action == "approve" else "rejected"
                if current != target:
                    messages.append(
                        f"{decision.event_id}: current status {current!r} "
                        f"conflicts with decision {decision.action!r}"
                    )
    return messages


def apply_decision(
    path: Path, decision: Decision, reviewer: str, review_date: str
) -> bool:
    text = path.read_text(encoding="utf-8")
    target = "reviewed" if decision.action == "approve" else "rejected"
    current = read_field(text, "review_status", path)
    if current == target:
        return False
    updated = re.sub(
        FIELD_RE_TEMPLATE.format(field="review_status"),
        f"review_status: {target}",
        text,
        count=1,
    )
    updated = re.sub(
        FIELD_RE_TEMPLATE.format(field="updated_at"),
        f"updated_at: {review_date}",
        updated,
        count=1,
    )
    reason = decision.detail if decision.detail else "批准"
    record = (
        "\n\n## Review record\n\n"
        f"- Review date: {review_date}\n"
        f"- Reviewer: {reviewer}\n"
        f"- Decision: {decision.action}\n"
        f"- Note: {reason}\n"
    )
    path.write_text(updated.rstrip() + record, encoding="utf-8")
    return True


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    packet = (
        args.packet.resolve()
        if args.packet
        else root
        / "05_Research"
        / "AI-Enterprise-Software"
        / "Stage_3_Review_Packet.md"
    )
    if args.apply and not (args.reviewer and args.reviewer.strip()):
        print("ERROR: --reviewer is required with --apply", file=sys.stderr)
        return 2
    try:
        date.fromisoformat(args.review_date)
        decisions = parse_packet(packet)
        files = event_files(root)
        errors = validate(decisions, files, applying=args.apply)
    except (OSError, ReviewError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    counts = {
        action: sum(decision.action == action for decision in decisions)
        for action in ("approve", "edit", "reject", "pending")
    }
    print(
        "Review decisions: "
        + ", ".join(f"{key}={value}" for key, value in counts.items())
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if not args.apply:
        print("PASS: packet structure and Event coverage are valid; no files changed")
        return 0

    changed = 0
    for decision in decisions:
        note = decision.detail or "Imported from Stage 3 review packet."
        try:
            paths = apply_review(
                root,
                target_ids=[decision.event_id],
                decision=decision.action,
                reviewer=args.reviewer.strip(),
                reviewed_at=args.review_date,
                notes=note,
            )
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        changed += sum(path == files[decision.event_id] for path in paths)
    print(f"APPLIED: {changed} Event files updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
