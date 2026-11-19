"""Date logic of the archive picker."""
from app.ui.archive_calendar import (
    ArchiveDates,
    month_grid,
    month_of,
    month_title,
    shift_month,
    short_weekday,
    weekday_columns,
)


def test_archive_dates_step_between_days():
    dates = ArchiveDates(["2026-10-20", "2026-10-05", "2026-09-30", "2026-10-20"])
    assert dates.newest() == "2026-10-20"
    assert dates.older("2026-10-20") == "2026-10-05"
    assert dates.older("2026-09-30") is None
    assert dates.newer("2026-10-05") == "2026-10-20"
    assert dates.newer("2026-10-20") is None
    assert dates.older("2026-10-10") == "2026-10-05"   # works for any date
    assert dates.contains("2026-10-05") and not dates.contains("2026-10-06")


def test_archive_dates_by_month():
    dates = ArchiveDates(["2026-10-20", "2026-10-05", "2026-09-30"])
    assert dates.days_in_month(2026, 10) == frozenset({5, 20})
    assert dates.has_before_month(2026, 10) is True       # 30 Sept exists
    assert dates.has_before_month(2026, 9) is False
    assert not ArchiveDates([])


def test_month_grid_respects_the_first_day_of_the_week():
    # 1 October 2026 is a Thursday.
    saturday_first = month_grid(2026, 10, 5)
    assert saturday_first[:5] == [None] * 5 and saturday_first[5] == 1
    monday_first = month_grid(2026, 10, 0)
    assert monday_first[:3] == [None] * 3 and monday_first[3] == 1
    assert month_grid(2026, 10, 5)[-1] == 31


def test_month_helpers():
    assert shift_month(2026, 1, -1) == (2025, 12)
    assert shift_month(2026, 12, 1) == (2027, 1)
    assert month_of("2026-10-25") == (2026, 10)
    assert month_title(2026, 10) == "أكتوبر 2026"
    assert weekday_columns(5) == [5, 6, 0, 1, 2, 3, 4]
    assert [short_weekday(w) for w in weekday_columns(5)] == [
        "سبت", "أحد", "اثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة",
    ]