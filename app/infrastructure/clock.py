"""Centralized time and calendar formatting utilities.

All timestamp/date generation goes through this module so it is not
duplicated across repositories, and so a future test can monkeypatch
one place if it ever needs to control "now".
"""
from __future__ import annotations

import math
from datetime import date, datetime, timezone
from typing import Tuple

ARABIC_GREGORIAN_MONTHS = (
    "يناير",
    "فبراير",
    "مارس",
    "أبريل",
    "مايو",
    "يونيو",
    "يوليو",
    "أغسطس",
    "سبتمبر",
    "أكتوبر",
    "نوفمبر",
    "ديسمبر",
)

HIJRI_MONTHS = (
    "محرم",
    "صفر",
    "ربيع الأول",
    "ربيع الآخر",
    "جمادى الأولى",
    "جمادى الآخرة",
    "رجب",
    "شعبان",
    "رمضان",
    "شوال",
    "ذو القعدة",
    "ذو الحجة",
)


def utc_now_iso() -> str:
    """Current UTC instant as an ISO-8601 string. Used for created_at/updated_at."""
    return datetime.now(timezone.utc).isoformat()


def local_today_iso() -> str:
    """Current local calendar date as YYYY-MM-DD.

    Deliberately separate from utc_now_iso: a Day's date must reflect
    the user's local calendar day. Near midnight, the local date and
    the UTC date can legitimately differ, and mixing the two would
    assign tasks to the wrong day.
    """
    return date.today().isoformat()


def ms_until_next_local_midnight(current_dt: Optional[datetime] = None) -> int:
    """Calculate the milliseconds remaining until the next local Gregorian midnight.

    Adds a small 500ms safety buffer so the timer fires safely inside the new day.
    """
    from datetime import time, timedelta

    now = current_dt if current_dt is not None else datetime.now()
    tomorrow = now.date() + timedelta(days=1)
    next_midnight = datetime.combine(tomorrow, time.min)
    remaining_seconds = (next_midnight - now).total_seconds()
    # Ensure non-negative and add 500ms buffer
    return max(1000, int(remaining_seconds * 1000) + 500)


def gregorian_to_hijri(year: int, month: int, day: int) -> Tuple[int, int, int]:
    """Convert a Gregorian calendar date (year, month, day) to Islamic Hijri (year, month, day).

    Uses the established algorithmic approximation (civil Islamic calendar / Kuwaiti algorithm).
    No external dependencies required.
    """
    # If month is Jan/Feb, treat as months 13/14 of previous year
    if month < 3:
        year -= 1
        month += 12

    a = math.floor(year / 100.0)
    b = 2 - a + math.floor(a / 4.0)

    # Julian Day calculation
    jd = (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        + b
        - 1524
    )

    epoch_astro = 1948084
    shift1 = 8.01 / 60.0
    iyear = 10631.0 / 30.0

    z = jd - epoch_astro
    cyc = math.floor(z / 10631.0)
    z = z - 10631.0 * cyc
    j = math.floor((z - shift1) / iyear)
    iy = 30 * cyc + j
    z = z - math.floor(j * iyear + shift1)
    im = math.floor((z + 28.5001) / 29.5)
    if im == 13:
        im = 12
    id_h = int(z - math.floor(29.5001 * im - 29))
    im_h = int(im)
    iy_h = int(iy)

    return iy_h, im_h, id_h


def format_dual_calendar_date(iso_date: str) -> str:
    """Format an ISO date string (YYYY-MM-DD) into a dual Gregorian & Hijri Arabic date line.

    Example:
        '2026-09-22' -> '22 سبتمبر 2026 • 10 ربيع الآخر 1448 هـ'
    """
    try:
        parts = [int(p) for p in iso_date.split("-")]
        if len(parts) != 3:
            return iso_date
        g_year, g_month, g_day = parts[0], parts[1], parts[2]
    except Exception:
        return iso_date

    # Gregorian formatted string
    g_month_name = (
        ARABIC_GREGORIAN_MONTHS[g_month - 1]
        if 1 <= g_month <= 12
        else str(g_month)
    )
    gregorian_str = f"{g_day} {g_month_name} {g_year}"

    # Hijri formatted string
    # First attempt Qt's QCalendar if PySide6 is installed and available
    hijri_year, hijri_month, hijri_day = None, None, None
    try:
        from PySide6.QtCore import QCalendar, QDate

        qdate = QDate(g_year, g_month, g_day)
        if qdate.isValid():
            cal = QCalendar(QCalendar.System.IslamicCivil)
            if cal.isDateValid(cal.year(qdate), cal.month(qdate), cal.day(qdate)):
                hijri_year = cal.year(qdate)
                hijri_month = cal.month(qdate)
                hijri_day = cal.day(qdate)
    except Exception:
        pass

    # Fallback to pure algorithmic converter if Qt is unavailable
    if hijri_year is None or hijri_month is None or hijri_day is None:
        hijri_year, hijri_month, hijri_day = gregorian_to_hijri(g_year, g_month, g_day)

    h_month_name = (
        HIJRI_MONTHS[hijri_month - 1]
        if 1 <= hijri_month <= 12
        else str(hijri_month)
    )
    hijri_str = f"{hijri_day} {h_month_name} {hijri_year} هـ"

    return f"{gregorian_str}  •  {hijri_str}"
