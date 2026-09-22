"""Pure unit tests for date and calendar formatting helpers in clock.py."""
from app.infrastructure.clock import (
    format_dual_calendar_date,
    gregorian_to_hijri,
)


def test_gregorian_to_hijri_conversion():
    # 2023-04-21 was 1 Shawwal 1444 AH (Eid al-Fitr)
    h_year, h_month, h_day = gregorian_to_hijri(2023, 4, 21)
    assert h_year == 1444
    assert h_month == 10
    assert h_day == 1

    # 2026-09-22 is 1448 AH
    hy, hm, hd = gregorian_to_hijri(2026, 9, 22)
    assert hy == 1448
    assert 1 <= hm <= 12
    assert 1 <= hd <= 30


def test_format_dual_calendar_date():
    result = format_dual_calendar_date("2026-09-22")
    assert "سبتمبر" in result
    assert "2026" in result
    assert "1448" in result
    assert "هـ" in result
    assert "•" in result


def test_format_dual_calendar_date_invalid_fallback():
    # If date string is malformed, returns the raw input safely without crashing
    assert format_dual_calendar_date("invalid-date") == "invalid-date"
    assert format_dual_calendar_date("") == ""
