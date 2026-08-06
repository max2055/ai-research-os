"""B-021 Channel schedule parsing.

Maps the natural-language ``schedule`` values on Source Channels
("every 6 hours", "daily 1x", "daily 2x", "hourly", "weekly") to a repeat
interval, so the scheduler can compute when a channel is next due. An
unparseable schedule is treated as *not due* (never auto-run a channel we
cannot schedule); ``discover check`` should surface those for a human.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

_SIMPLE = {
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
}
_INTERVAL_RE = re.compile(
    r"^every\s+(\d+)\s+(hour|hours|minute|minutes|day|days|week|weeks)$"
)
_DAILY_X_RE = re.compile(r"^daily\s+(\d+)x$")
_UNITS = {
    "hour": "hours",
    "hours": "hours",
    "minute": "minutes",
    "minutes": "minutes",
    "day": "days",
    "days": "days",
    "week": "weeks",
    "weeks": "weeks",
}
_UNIT_DURATIONS = {
    "hours": timedelta(hours=1),
    "minutes": timedelta(minutes=1),
    "days": timedelta(days=1),
    "weeks": timedelta(days=7),
}
_DAILY_LIMIT = 12


def interval_from_schedule(schedule: str) -> timedelta | None:
    """Repeat interval for a schedule string, or None if unparseable."""
    text = (schedule or "").strip().lower()
    if not text:
        return None
    simple = _SIMPLE.get(text)
    if simple is not None:
        return simple
    match = _INTERVAL_RE.fullmatch(text)
    if match:
        count = int(match.group(1))
        if not 1 <= count <= 1000:
            return None
        unit = _UNIT_DURATIONS[_UNITS[match.group(2)]]
        return unit * count
    match = _DAILY_X_RE.fullmatch(text)
    if match:
        per_day = int(match.group(1))
        if not 1 <= per_day <= _DAILY_LIMIT:
            return None
        return timedelta(hours=24 / per_day)
    return None


def next_run_at(previous: datetime, schedule: str) -> datetime | None:
    interval = interval_from_schedule(schedule)
    return previous + interval if interval is not None else None


def is_due(
    previous: datetime | None,
    schedule: str,
    as_of: datetime,
) -> bool:
    """Whether a channel is due for discovery at ``as_of``.

    Never run -> due. Unparseable schedule -> not due (needs human fix).
    """
    if previous is None:
        return True
    next_run = next_run_at(previous, schedule)
    return next_run is not None and next_run <= as_of
