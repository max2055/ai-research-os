from __future__ import annotations

import pytest

from research_os.services.schedule_control import (
    SchedulePolicy,
    due_decision,
    next_fire_time,
)


def test_next_fire_uses_timezone_and_interval() -> None:
    policy = SchedulePolicy(interval_seconds=21600, timezone="Asia/Shanghai")
    assert next_fire_time(policy, "2026-08-17T00:00:00Z") == ("2026-08-17T06:00:00Z")


def test_catch_up_once_and_skip_missed() -> None:
    policy = SchedulePolicy(21600, "UTC")
    caught = due_decision(
        next_run_at="2026-08-16T00:00:00Z",
        now="2026-08-17T00:00:00Z",
        policy="catch_up_once",
        schedule=policy,
    )
    skipped = due_decision(
        next_run_at="2026-08-16T00:00:00Z",
        now="2026-08-17T00:00:00Z",
        policy="skip_missed",
        schedule=policy,
    )
    assert caught.action == "run_once"
    assert caught.next_run_at == "2026-08-17T06:00:00Z"
    assert skipped.action == "advance_only"
    assert skipped.next_run_at == "2026-08-17T06:00:00Z"
    assert (
        due_decision(
            next_run_at=caught.next_run_at,
            now="2026-08-17T00:00:00Z",
            policy="catch_up_once",
            schedule=policy,
        ).action
        == "not_due"
    )


def test_long_outage_advances_directly_to_the_first_future_fire() -> None:
    decision = due_decision(
        next_run_at="2020-01-01T00:00:00Z",
        now="2026-08-17T06:00:00Z",
        policy="catch_up_once",
        interval_seconds=1,
    )

    assert decision.action == "run_once"
    assert decision.next_run_at == "2026-08-17T06:00:01Z"


def test_dst_boundary_and_invalid_timezone() -> None:
    policy = SchedulePolicy(86400, "America/New_York")
    assert next_fire_time(policy, "2026-03-07T17:00:00Z") == ("2026-03-08T17:00:00Z")
    with pytest.raises(ValueError):
        SchedulePolicy(3600, "Mars/Olympus")
    with pytest.raises(ValueError):
        SchedulePolicy(0, "UTC")
