#!/usr/bin/env python3
"""Validate and render the pending Impact Assertion agent audit packet."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from pydantic import ValidationError

_REPOSITORY_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_REPOSITORY_SRC))

from research_os.services.impact_audit import (  # noqa: E402
    check_rendered_packet,
    load_audit_spec,
    render_audit_packet,
    validate_audit_spec,
)

PACKET_PATH = Path("05_Research/Reviews/Impact_Assertion_Agent_Audit_Packet.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a structured pending Impact audit and deterministically render "
            "its non-authoritative human-review packet."
        )
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--spec", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    spec = args.spec if args.spec.is_absolute() else root / args.spec
    packet_path = root / PACKET_PATH
    if args.check:
        errors = check_rendered_packet(root, spec, packet_path)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"PASS: {packet_path}")
        return 0

    try:
        packet = load_audit_spec(spec)
        errors = validate_audit_spec(root, packet)
    except (OSError, ValueError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(packet_path, render_audit_packet(packet))
    print(f"WROTE: {packet_path}")
    return 0


def _atomic_write(path: Path, content: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
