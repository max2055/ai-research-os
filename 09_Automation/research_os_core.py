"""Compatibility imports for the packaged AI Research OS core."""

from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SOURCE_ROOT) in sys.path:
    sys.path.remove(str(SOURCE_ROOT))
sys.path.insert(0, str(SOURCE_ROOT))

from research_os.legacy_core import *  # noqa: F403
