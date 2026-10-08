"""Phase 7E: weekly/range reporting foundation tests.

Backend-only (stdlib + sqlite3, no Qt): the reporting service is Qt-free.
Covers semantics, ranges, categories (incl. inactive historical), daily
rows, rollover history, read-only behavior, and bounded query count.
"""
import dataclasses
import sqlite3

import pytest

from app.core.daily_reports import (
    CategoryReport,
    DateRangeReport,
    DailyReport,
    completion_percent,
    validate_range,
)
from app.core.services.daily_rollover_service import DailyRolloverService
from app.core.services.report_service import ReportService
from app.core.services.task_service import TaskService
from app.database.category_repository import CategoryRepository
from app.database.day_repository import DayRepository
from app.database.report_repository import ReportRepository
from app.database.task_repository import TaskRepository


class _CountingConn:
    """Proxy counting every execute() call (query-count audit)."""

    def __init__(self, conn):
        self._conn = conn
        self.count = 0

    def execute(self, *args, **kwargs):
        self.count += 1
        return self._conn.execute(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _service(db_connection, counter=None):
    conn = counter or db_connection
    return ReportService(ReportRepository(conn), CategoryRepository(conn))


def _seed_week(db_connection):
    """Mon 2026-10-05 .. Sun 2026-10-11 with mixed, known content."""
    day_repo = DayRepository(db_connection)
    service = TaskService(TaskRepository(db_connection), CategoryRepository(db_connection))
    plan = {
        # date: [(text, category, completed), ...]
        "2026-10-05": [("a1", "work", True), ("a2", "work", False), ("a3", "religion", False)],
        "2026-10-06": [],
        "2026-10-07": [("b1", "life", True), ("b2", "life", True)],
        "2026-10-08": [("c1", "general", False)],
        "2026-10-09": [("d1", "work", True)],
        "2026-10-10": [],
        "2026-10-11": [("e1", "religion", True), ("e2", "general", True), ("e3", "general", False)],
    }
    for day_iso, tasks in plan.items():
        day = day_repo.get_or_create(day_iso)
        for text, category, done in tasks:
            task = service.create_task(day.id, text, category_id=category)
            assert task is not None
            if done:
                service.toggle_task_completion(task.id, True)


# ------------------------------------------------------------ pure semantics

def test_completion_percent_edge_cases():
    assert completion_percent(0, 0) == 0
    assert completion_percent(0, 5) == 0
    assert completion_percent(5, 5) == 100
    assert completion_percent(1, 2) == 50
    assert completion_percent(1, 4) == 25


def test_validate_range_accepts_and_rejects():
    start, end = validate_range("2026-10-05", "2026-10-11")
    assert (start.isoformat(), end.isoformat()) == ("2026-10-05", "2026-10-11")
    start, end = validate_range("2026-10-05", "2026-10-05")  # same-day range
    assert start == end
    with pytest.raises(ValueError):
        validate_range("2026-10-11", "2026-10-05")
    with pytest.raises(ValueError):
        validate_range("not-a-date", "2026-10-05")
    with pytest.raises(ValueError):
        validate_range("2026-10-05", None)  # type: ignore


def test_result_models_are_immutable():
    report = DateRangeReport("2026-10-05", "2026-10-05", 0, 0, 0, 0, (), ())
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.total_tasks = 1  # type: ignore
    with pytest.raises(dataclasses.FrozenInstanceError):
        DailyReport("2026-10-05", 0, 0, 0, 0).total = 1  # type: ignore
    with pytest.raises(dataclasses.FrozenInstanceError):
        CategoryReport("work", "x", "x", 0, 0, 0, 0).total = 1  # type: ignore


# ------------------------------------------------------------ weekly content

def test_full_week_totals_and_percentage(db_connection):
    _seed_week(db_connection)
    report = _service(db_connection).get_range_report("2026-10-05", "2026-10-11")
    assert (report.start_date, report.end_date) == ("2026-10-05", "2026-10-11")
    # 3+0+2+1+1+0+3 = 10 total; completed a1,b1,b2,d1,e1,e2 = 6.
    assert (report.total_tasks, report.completed_tasks, report.incomplete_tasks) == (10, 6, 4)
    assert report.completion_percentage == 60


def test_category_breakdown_uses_stored_metadata(db_connection):
    _seed_week(db_connection)
    report = _service(db_connection).get_range_report("2026-10-05", "2026-10-11")
    by_id = {row.category_id: row for row in report.category_reports}
    assert set(by_id) == {"religion", "work", "life", "general"}
    assert [(r.total, r.completed, r.incomplete) for r in
            (by_id["work"], by_id["religion"], by_id["life"], by_id["general"])] == [
        (3, 2, 1), (2, 1, 1), (2, 2, 0), (3, 1, 2),
    ]
    assert by_id["work"].category_name_ar == "عمل"
    assert by_id["work"].icon_key == "work"
    assert by_id["work"].completion_percentage == 67  # round(2/3*100)
    assert [r.category_id for r in report.category_reports] == [
        "religion", "work", "life", "general"]  # sort_order, not alpha/query order


def test_daily_rows_chronological_with_zero_days(db_connection):
    _seed_week(db_connection)
    report = _service(db_connection).get_range_report("2026-10-05", "2026-10-11")
    assert [row.date for row in report.daily_reports] == [
        "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08",
        "2026-10-09", "2026-10-10", "2026-10-11",
    ]
    by_date = {row.date: row for row in report.daily_reports}
    assert (by_date["2026-10-06"].total, by_date["2026-10-06"].completion_percentage) == (0, 0)
    assert (by_date["2026-10-07"].total, by_date["2026-10-07"].completed) == (2, 2)
    assert by_date["2026-10-07"].completion_percentage == 100


def test_unrecorded_days_appear_with_zeros(db_connection):
    report = _service(db_connection).get_range_report("2026-01-01", "2026-01-03")
    assert (report.total_tasks, report.completion_percentage) == (0, 0)
    assert [row.date for row in report.daily_reports] == ["2026-01-01", "2026-01-02", "2026-01-03"]
    assert all(row.total == 0 for row in report.daily_reports)
    # Known categories still listed with zeros (stable dashboard shape).
    assert len(report.category_reports) == 4
    assert all(row.total == 0 for row in report.category_reports)


def test_same_day_and_boundary_ranges(db_connection):
    _seed_week(db_connection)
    service = _service(db_connection)
    single = service.get_range_report("2026-10-07", "2026-10-07")
    assert (single.total_tasks, single.completed_tasks) == (2, 2)
    assert single.completion_percentage == 100
    assert [row.date for row in single.daily_reports] == ["2026-10-07"]
    # Range starting/ending mid-data includes boundaries.
    partial = service.get_range_report("2026-10-07", "2026-10-08")
    assert (partial.total_tasks, partial.completed_tasks) == (3, 2)


def test_two_week_range(db_connection):
    _seed_week(db_connection)
    report = _service(db_connection).get_range_report("2026-09-28", "2026-10-11")
    assert len(report.daily_reports) == 14
    assert report.total_tasks == 10  # only the seeded week has tasks


def test_all_completed_and_all_incomplete_ranges(db_connection):
    day_repo = DayRepository(db_connection)
    service = TaskService(TaskRepository(db_connection), CategoryRepository(db_connection))
    day = day_repo.get_or_create("2026-10-05")
    t1 = service.create_task(day.id, "x", category_id="work")
    t2 = service.create_task(day.id, "y", category_id="work")
    assert t1 is not None and t2 is not None
    reports = _service(db_connection)
    bare = reports.get_range_report("2026-10-05", "2026-10-05")
    assert (bare.total_tasks, bare.completion_percentage) == (2, 0)
    service.toggle_task_completion(t1.id, True)
    service.toggle_task_completion(t2.id, True)
    done = reports.get_range_report("2026-10-05", "2026-10-05")
    assert (done.total_tasks, done.completion_percentage) == (2, 100)


def test_invalid_range_raises(db_connection):
    with pytest.raises(ValueError):
        _service(db_connection).get_range_report("2026-10-11", "2026-10-05")
    with pytest.raises(ValueError):
        _service(db_connection).get_range_report("garbage", "2026-10-05")


# ------------------------------------------------------------ categories

def test_zero_task_category_listed_with_zeros(db_connection):
    day_repo = DayRepository(db_connection)
    service = TaskService(TaskRepository(db_connection), CategoryRepository(db_connection))
    day = day_repo.get_or_create("2026-10-05")
    task = service.create_task(day.id, "solo", category_id="work")
    assert task is not None
    by_id = {r.category_id: r for r in
             _service(db_connection).get_range_report("2026-10-05", "2026-10-05").category_reports}
    assert by_id["life"].total == 0 and by_id["life"].completion_percentage == 0
    assert by_id["work"].total == 1


def test_inactive_historical_category_remains_reportable(db_connection):
    day_repo = DayRepository(db_connection)
    repos = (TaskRepository(db_connection), CategoryRepository(db_connection))
    service = TaskService(*repos)
    day = day_repo.get_or_create("2026-10-05")
    task = service.create_task(day.id, "قديمة", category_id="life")
    assert task is not None
    service.toggle_task_completion(task.id, True)
    repos[1].set_active("life", False)  # deactivated AFTER the work happened

    report = _service(db_connection).get_range_report("2026-10-05", "2026-10-05")
    by_id = {row.category_id: row for row in report.category_reports}
    assert by_id["life"].total == 1 and by_id["life"].completed == 1
    assert by_id["life"].category_name_ar == "حياة"


def test_unknown_category_falls_back_without_crashing(db_connection):
    # Forced orphan via FK-off connection (the API layer can never create one).
    raw = sqlite3.connect(str(db_connection.execute("PRAGMA database_list").fetchone()[2]))
    try:
        raw.execute("INSERT INTO days (date, created_at, updated_at) VALUES ('2026-10-05','t','t')")
        raw.execute(
            "INSERT INTO tasks (day_id, text, position, category_id, created_at, updated_at) "
            "VALUES (1, 'يتيمة', 0, 'ghost', 't', 't')"
        )
        raw.commit()
    finally:
        raw.close()
    by_id = {r.category_id: r for r in
             _service(db_connection).get_range_report("2026-10-05", "2026-10-05").category_reports}
    assert by_id["ghost"].total == 1
    assert by_id["ghost"].category_name_ar == "ghost"


# ------------------------------------------------------------ rollover history

def _rollover_wiring(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo, CategoryRepository(db_connection))
    rollover = DailyRolloverService(conn=db_connection, day_repo=day_repo, task_repo=task_repo)
    return day_repo, service, rollover


def test_rollover_days_report_historical_truth(db_connection):
    day_repo, service, rollover = _rollover_wiring(db_connection)
    source = day_repo.get_or_create("2026-10-05")
    done = service.create_task(source.id, "منجزة", category_id="work")
    todo = service.create_task(source.id, "مؤجلة", category_id="work")
    assert done is not None and todo is not None
    service.toggle_task_completion(done.id, True)
    assert len(rollover.rollover_tasks("2026-10-05", "2026-10-06")) == 1

    reports = _service(db_connection)
    day_a = reports.get_range_report("2026-10-05", "2026-10-05")
    assert (day_a.total_tasks, day_a.completed_tasks, day_a.incomplete_tasks) == (2, 1, 1)
    day_b = reports.get_range_report("2026-10-06", "2026-10-06")
    assert (day_b.total_tasks, day_b.completed_tasks, day_b.incomplete_tasks) == (1, 0, 1)
    both = reports.get_range_report("2026-10-05", "2026-10-06")
    # No dedup: source day keeps 2, target day has its own copy (3 total).
    assert (both.total_tasks, both.completed_tasks) == (3, 1)
    assert {r.category_id: r.total for r in both.category_reports}["work"] == 3


def test_multi_day_rollover_chain_counts(db_connection):
    day_repo, service, rollover = _rollover_wiring(db_connection)
    day = day_repo.get_or_create("2026-10-05")
    task = service.create_task(day.id, "سلسلة", category_id="religion")
    assert task is not None
    rollover.rollover_tasks("2026-10-05", "2026-10-06")
    rollover.rollover_tasks("2026-10-06", "2026-10-07")
    report = _service(db_connection).get_range_report("2026-10-05", "2026-10-07")
    assert report.total_tasks == 3
    assert [row.total for row in report.daily_reports] == [1, 1, 1]


# ------------------------------------------------------------ read-only + queries

def test_report_is_read_only(db_connection):
    _seed_week(db_connection)
    before_tasks = db_connection.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    before_days = db_connection.execute("SELECT * FROM days ORDER BY id").fetchall()
    before_cats = db_connection.execute("SELECT * FROM categories ORDER BY id").fetchall()
    _service(db_connection).get_range_report("2026-10-05", "2026-10-11")
    assert db_connection.execute("SELECT * FROM tasks ORDER BY id").fetchall() == before_tasks
    assert db_connection.execute("SELECT * FROM days ORDER BY id").fetchall() == before_days
    assert db_connection.execute("SELECT * FROM categories ORDER BY id").fetchall() == before_cats


def test_query_count_is_bounded(db_connection):
    _seed_week(db_connection)
    counter = _CountingConn(db_connection)
    service = ReportService(ReportRepository(counter), CategoryRepository(counter))
    service.get_range_report("2026-10-05", "2026-10-11")
    # Exactly: category aggregate + daily aggregate + category metadata.
    assert counter.count == 3
    counter.count = 0
    service.get_range_report("2026-09-01", "2026-12-31")  # 4x the days
    assert counter.count == 3  # independent of range length


def test_no_per_day_or_per_category_queries(db_connection):
    _seed_week(db_connection)
    counter = _CountingConn(db_connection)
    service = ReportService(ReportRepository(counter), CategoryRepository(counter))
    counter.count = 0
    service.get_range_report("2026-10-05", "2026-10-05")  # single day, 4 categories
    assert counter.count == 3
