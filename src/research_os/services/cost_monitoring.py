"""Natural-month Discovery cost health derived from the Candidate store."""

from __future__ import annotations

import sqlite3
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal

CostStatus = Literal["unconfigured", "no_data", "ok", "warning", "exceeded", "invalid"]


@dataclass(frozen=True)
class MonthlyCostReport:
    status: CostStatus
    period_start: str
    period_end: str
    currency: str
    known_total: Decimal | None
    budget: Decimal | None
    utilization: Decimal | None
    record_count: int
    unknown_record_count: int
    invalid_record_count: int


def monthly_cost_report(
    db_path: Path,
    *,
    as_of: str | None = None,
    budget: str | None = None,
    currency: str = "USD",
) -> MonthlyCostReport:
    report_date = date.fromisoformat(as_of) if as_of is not None else date.today()
    period_start_date = report_date.replace(day=1)
    period_end_date = report_date.replace(
        day=monthrange(report_date.year, report_date.month)[1]
    )
    if report_date.month == 12:
        next_period = date(report_date.year + 1, 1, 1)
    else:
        next_period = date(report_date.year, report_date.month + 1, 1)

    rows: list[object] = []
    database_invalid = False
    if db_path.is_file():
        connection: sqlite3.Connection | None = None
        try:
            uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
            connection = sqlite3.connect(uri, uri=True)
            rows = [
                row[0]
                for row in connection.execute(
                    "SELECT cost_estimate FROM discovery_runs "
                    "WHERE started_at >= ? AND started_at < ?",
                    (period_start_date.isoformat(), next_period.isoformat()),
                ).fetchall()
            ]
        except sqlite3.DatabaseError:
            database_invalid = True
        finally:
            if connection is not None:
                connection.close()

    known: list[Decimal] = []
    unknown_count = 0
    invalid_count = 0
    for raw_value in rows:
        if raw_value is None or not str(raw_value).strip():
            unknown_count += 1
            continue
        try:
            value = Decimal(str(raw_value).strip())
        except ArithmeticError:
            invalid_count += 1
            continue
        if not value.is_finite() or value < 0:
            invalid_count += 1
            continue
        known.append(value)

    parsed_budget: Decimal | None = None
    budget_invalid = False
    if budget is not None and budget.strip():
        try:
            parsed_budget = Decimal(budget.strip())
        except ArithmeticError:
            budget_invalid = True
        else:
            if not parsed_budget.is_finite() or parsed_budget <= 0:
                parsed_budget = None
                budget_invalid = True

    known_total = sum(known, start=Decimal(0)) if known else None
    utilization = (
        known_total / parsed_budget
        if known_total is not None and parsed_budget is not None
        else None
    )
    if database_invalid or budget_invalid or invalid_count:
        status: CostStatus = "invalid"
    elif parsed_budget is None:
        status = "unconfigured"
    elif known_total is None:
        status = "no_data"
    elif utilization is not None and utilization >= Decimal(1):
        status = "exceeded"
    elif utilization is not None and utilization >= Decimal("0.8"):
        status = "warning"
    else:
        status = "ok"

    return MonthlyCostReport(
        status=status,
        period_start=period_start_date.isoformat(),
        period_end=period_end_date.isoformat(),
        currency=currency,
        known_total=known_total,
        budget=parsed_budget,
        utilization=utilization,
        record_count=len(rows),
        unknown_record_count=unknown_count,
        invalid_record_count=invalid_count,
    )
