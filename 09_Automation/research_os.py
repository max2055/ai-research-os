#!/usr/bin/env python3
"""Compatibility entry point for the packaged AI Research OS CLI."""

from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SOURCE_ROOT) in sys.path:
    sys.path.remove(str(SOURCE_ROOT))
sys.path.insert(0, str(SOURCE_ROOT))

from research_os.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
