"""Read-only weekly/range report domain models (Phase 7E).

Qt-free, SQL-free, immutable frozen dataclasses matching the existing domain
style. Semantics (the contract the future Dashboard relies on):

- A report covers an INCLUSIVE Gregorian date range ``[start_date, end_date]``.
- Tasks are counted exactly as stored: each task belongs to its own day
  (``day_id -> days.date``); rollover copies are independent rows on their
  own day and are never deduplicated or merged.
- Category identity comes from the stored ``category_id``; display
  metadata (Arabic name, icon key) comes from the categories table, with
  inactive-but-historical categories fully preserved.
- Days with no records appear with zeros (deterministic, never omitted).
- Percentages are integer percents, ``round(completed / total * 100)``,
  and 0 when there is nothing to divide by.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Tuple


def completion_percent(completed: int, total: int) -> int:
    """Integer completion percentage; 0 when ``total`` is 0."""
    if total <= 0 or completed <= 0:
        return 0
    return int(round((completed / total) * 100))


def validate_range(start_date: str, end_date: str) -> Tuple[date, date]:
    """Parse and validate an inclusive ``YYYY-MM-DD`` range.

    Raises ValueError for malformed dates or when start > end.
    Same-day ranges are valid one-day reports.
    """
    try:
        start = date.fromisoformat(start_date)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid start_date: {start_date!r}") from exc
    try:
        end = date.fromisoformat(end_date)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid end_date: {end_date!r}") from exc
    if start > end:
        raise ValueError(f"start_date ({start_date}) must not be after end_date ({end_date})")
    return start, end


def enumerate_dates(start: date, end: date) -> List[str]:
    """Every ISO date in the inclusive range, chronological."""
    from datetime import timedelta

    days = (end - start).days
    return [(start + timedelta(days=offset)).isoformat() for offset in range(days + 1)]


@dataclass(frozen=True)
class CategoryReport:
    """One category's activity inside the reported range."""

    category_id: str
    category_name_ar: str
    icon_key: str
    total: int
    completed: int
    incomplete: int
    completion_percentage: int


@dataclass(frozen=True)
class DailyReport:
    """One calendar day's activity inside the reported range."""

    date: str
    total: int
    completed: int
    incomplete: int
    completion_percentage: int


@dataclass(frozen=True)
class DateRangeReport:
    """Immutable aggregate for an inclusive date range."""

    start_date: str
    end_date: str
    total_tasks: int
    completed_tasks: int
    incomplete_tasks: int
    completion_percentage: int
    category_reports: Tuple[CategoryReport, ...] = field(default_factory=tuple)
    daily_reports: Tuple[DailyReport, ...] = field(default_factory=tuple)
