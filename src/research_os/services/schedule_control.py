"""Runtime schedule policy.

Only typed interval values are used by the worker.  Natural-language schedule
strings remain in :mod:`schedule_migration` for one-time compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.triggers.interval import (  # type: ignore[import-untyped]
    IntervalTrigger,
)

MIN_INTERVAL_SECONDS = 1
MAX_INTERVAL_SECONDS = 31_536_000


@dataclass(frozen=True)
class SchedulePolicy:
    interval_seconds: int
    timezone: str

    def __post_init__(self) -> None:
        if not MIN_INTERVAL_SECONDS <= self.interval_seconds <= MAX_INTERVAL_SECONDS:
            raise ValueError("interval_seconds is outside the supported range")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"invalid IANA timezone: {self.timezone}") from exc


@dataclass(frozen=True)
class DueDecision:
    action: Literal["run_once", "advance_only", "not_due"]
    next_run_at: str


def _parse(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return result.astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def next_fire_time(policy: SchedulePolicy, previous: str) -> str:
    """Return the next UTC fire time after ``previous``."""
    previous_dt = _parse(previous)
    trigger = IntervalTrigger(
        seconds=policy.interval_seconds,
        start_date=previous_dt.astimezone(ZoneInfo(policy.timezone)),
        timezone=ZoneInfo(policy.timezone),
    )
    local_previous = previous_dt.astimezone(ZoneInfo(policy.timezone))
    value = trigger.get_next_fire_time(local_previous, local_previous)
    if value is None:
        raise ValueError("interval trigger produced no next fire time")
    return _iso(value)


def due_decision(
    *,
    next_run_at: str,
    now: str,
    policy: Literal["catch_up_once", "skip_missed"],
    schedule: SchedulePolicy | None = None,
    interval_seconds: int | None = None,
    timezone: str = "UTC",
) -> DueDecision:
    """Choose at most one execution for a missed schedule.

    ``schedule`` is preferred; the scalar arguments keep the function pleasant
    to use from small adapters and tests.
    """
    if policy not in {"catch_up_once", "skip_missed"}:
        raise ValueError("invalid missed-run policy")
    current = schedule or SchedulePolicy(interval_seconds or 1, timezone)
    due = _parse(next_run_at)
    observed = _parse(now)
    if due > observed:
        return DueDecision("not_due", _iso(due))
    interval = timedelta(seconds=current.interval_seconds)
    elapsed_intervals = (observed - due) // interval
    last_due = due + elapsed_intervals * interval
    following = next_fire_time(current, _iso(last_due))
    return DueDecision(
        "run_once" if policy == "catch_up_once" else "advance_only",
        following,
    )


__all__ = [
    "DueDecision",
    "MAX_INTERVAL_SECONDS",
    "MIN_INTERVAL_SECONDS",
    "SchedulePolicy",
    "due_decision",
    "next_fire_time",
]
