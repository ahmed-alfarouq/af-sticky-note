"""How a date is worded in the date header -- with no Qt dependency at all.

The user picks which calendar leads: with Hijri first, the big number is the
Hijri day and the Gregorian date follows; with Gregorian first, the other way
round. All the calendar data comes from :class:`DateDisplay`.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.infrastructure.clock import DateDisplay

__all__ = [
    "ArchiveDateText",
    "CalendarKind",
    "DateHeaderText",
    "archive_date_text",
    "date_header_text",
]


class CalendarKind(str, Enum):
    """The calendar shown first (the persisted value is the enum value)."""

    HIJRI = "hijri"
    GREGORIAN = "gregorian"


@dataclass(frozen=True)
class DateHeaderText:
    """The three texts of the date header."""

    day_number: str
    primary_line: str    # month and year in the leading calendar
    secondary_line: str  # weekday and the other calendar's date


def date_header_text(display: DateDisplay, calendar: CalendarKind) -> DateHeaderText:
    """Word ``display`` for the date header with ``calendar`` leading."""
    hijri_month_year = f"{display.hijri_month_name} {display.hijri_year} هـ"
    gregorian_month_year = f"{display.gregorian_month_name} {display.gregorian_year}"

    if calendar is CalendarKind.GREGORIAN:
        return DateHeaderText(
            day_number=str(display.gregorian_day),
            primary_line=gregorian_month_year,
            secondary_line=f"{display.weekday_ar} · {display.hijri_day} {hijri_month_year}",
        )

    return DateHeaderText(
        day_number=str(display.hijri_day),
        primary_line=hijri_month_year,
        secondary_line=f"{display.weekday_ar} · {display.gregorian_day} {gregorian_month_year}",
    )


@dataclass(frozen=True)
class ArchiveDateText:
    """The two lines naming a day in the archive."""

    primary: str    # the full date in the leading calendar
    secondary: str  # weekday and the full date in the other calendar


def archive_date_text(display: DateDisplay, calendar: CalendarKind) -> ArchiveDateText:
    """Word a whole day for the archive with ``calendar`` leading."""
    hijri = f"{display.hijri_day} {display.hijri_month_name} {display.hijri_year} هـ"
    gregorian = (
        f"{display.gregorian_day} {display.gregorian_month_name} {display.gregorian_year}"
    )
    if calendar is CalendarKind.GREGORIAN:
        return ArchiveDateText(primary=gregorian, secondary=f"{display.weekday_ar} · {hijri}")
    return ArchiveDateText(primary=hijri, secondary=f"{display.weekday_ar} · {gregorian}")