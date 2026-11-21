"""Date logic of the archive -- with no Qt dependency at all.

Which past days can be opened, how to step between them, and how a month is
laid out in a calendar grid. Dates travel as ISO strings (``YYYY-MM-DD``),
the same form the database stores.
"""
from __future__ import annotations

import calendar
from bisect import bisect_left, bisect_right
from datetime import date
from typing import FrozenSet, Iterable, List, Optional, Tuple

from app.infrastructure.clock import ARABIC_GREGORIAN_MONTHS, ARABIC_WEEKDAYS

__all__ = [
    "ArchiveDates",
    "iso_date",
    "month_grid",
    "month_of",
    "month_title",
    "shift_month",
    "short_weekday",
    "weekday_columns",
]


class ArchiveDates:
    """The past dates that can be opened."""

    def __init__(self, iso_dates: Iterable[str]) -> None:
        self._dates: List[str] = sorted(set(iso_dates))  # ISO strings sort by date

    def __bool__(self) -> bool:
        return bool(self._dates)

    def contains(self, iso: str) -> bool:
        index = bisect_left(self._dates, iso)
        return index < len(self._dates) and self._dates[index] == iso

    def newest(self) -> Optional[str]:
        return self._dates[-1] if self._dates else None

    def older(self, iso: str) -> Optional[str]:
        """The closest openable date before ``iso``."""
        index = bisect_left(self._dates, iso)
        return self._dates[index - 1] if index > 0 else None

    def newer(self, iso: str) -> Optional[str]:
        """The closest openable date after ``iso``."""
        index = bisect_right(self._dates, iso)
        return self._dates[index] if index < len(self._dates) else None

    def has_before_month(self, year: int, month: int) -> bool:
        """Whether any openable date lies before the first day of the month."""
        return bool(self._dates) and self._dates[0] < iso_date(year, month, 1)

    def days_in_month(self, year: int, month: int) -> FrozenSet[int]:
        """Day numbers of the month that can be opened."""
        prefix = f"{year:04d}-{month:02d}-"
        return frozenset(int(d[8:10]) for d in self._dates if d.startswith(prefix))


def iso_date(year: int, month: int, day: int) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}"


def month_of(iso: str) -> Tuple[int, int]:
    """``(year, month)`` of an ISO date."""
    return int(iso[0:4]), int(iso[5:7])


def shift_month(year: int, month: int, delta: int) -> Tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def weekday_columns(week_start: int) -> List[int]:
    """The weekday (Monday = 0) of each grid column, first column first."""
    return [(week_start + offset) % 7 for offset in range(7)]


def month_grid(year: int, month: int, week_start: int) -> List[Optional[int]]:
    """Cells of a month: empty slots (None) before day 1, then every day number."""
    blanks = (date(year, month, 1).weekday() - week_start) % 7
    return [None] * blanks + list(range(1, calendar.monthrange(year, month)[1] + 1))


def month_title(year: int, month: int) -> str:
    return f"{ARABIC_GREGORIAN_MONTHS[month - 1]} {year}"


def short_weekday(weekday: int) -> str:
    """The weekday name without the leading article ("السبت" -> "سبت")."""
    name = ARABIC_WEEKDAYS[weekday]
    return name[2:] if name.startswith("ال") else name