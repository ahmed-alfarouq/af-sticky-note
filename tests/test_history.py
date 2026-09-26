"""Tests for Phase 5J — Read-only History UI, HistoryService, and DailyStats."""
import sqlite3
import pytest

from app.core.daily_stats import compute_daily_stats
from app.core.models import TaskPriority
from app.core.services.daily_rollover_service import DailyRolloverService
from app.core.services.history_service import HistoryService
from app.core.services.task_service import TaskService
from app.database.day_repository import DayRepository
from app.database.task_repository import TaskRepository


def test_daily_stats_calculations():
    """Verify daily stats computation with various task ratios and 0 tasks."""
    # 0 tasks: 0% without division error
    s0 = compute_daily_stats([])
    assert s0.total == 0
    assert s0.completed == 0
    assert s0.incomplete == 0
    assert s0.completion_percentage == 0.0

    # Mock Task objects
    from unittest.mock import MagicMock
    def mock_task(completed: bool):
        t = MagicMock()
        t.is_completed = completed
        return t

    # 1/1 completed
    s1 = compute_daily_stats([mock_task(True)])
    assert s1.total == 1
    assert s1.completed == 1
    assert s1.completion_percentage == 100.0

    # 0/1 completed
    s2 = compute_daily_stats([mock_task(False)])
    assert s2.total == 1
    assert s2.completed == 0
    assert s2.completion_percentage == 0.0

    # 3/5 completed -> 60.0%
    s3 = compute_daily_stats([
        mock_task(True),
        mock_task(True),
        mock_task(True),
        mock_task(False),
        mock_task(False),
    ])
    assert s3.total == 5
    assert s3.completed == 3
    assert s3.incomplete == 2
    assert s3.completion_percentage == 60.0


def test_history_service_retrieval_and_order(db_connection):
    """Verify historical retrieval of recorded days and tasks in correct order."""
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    task_service = TaskService(task_repo)
    history_service = HistoryService(day_repo=day_repo, task_repo=task_repo)

    day1 = day_repo.create("2026-09-24")
    day2 = day_repo.create("2026-09-25")

    t1 = task_service.create_task(day1.id, "T1", priority=TaskPriority.LOW)
    t2 = task_service.create_task(day1.id, "T2", priority=TaskPriority.HIGH)
    task_service.toggle_task_completion(t2.id, True)

    # Verify available dates list (descending order)
    dates = history_service.get_available_dates()
    assert dates == ["2026-09-25", "2026-09-24"]

    # Retrieve snapshot for day 1
    view1 = history_service.get_day_history("2026-09-24")
    assert view1.date == "2026-09-24"
    assert view1.day is not None
    assert len(view1.tasks) == 2
    assert view1.tasks[0].id == t1.id
    assert view1.tasks[0].text == "T1"
    assert view1.tasks[0].is_completed is False
    assert view1.tasks[1].id == t2.id
    assert view1.tasks[1].text == "T2"
    assert view1.tasks[1].is_completed is True
    assert view1.stats.total == 2
    assert view1.stats.completed == 1
    assert view1.stats.completion_percentage == 50.0


def test_history_empty_day_and_nonexistent_date(db_connection):
    """Verify empty day produces valid stats and does not mutate database."""
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    history_service = HistoryService(day_repo=day_repo, task_repo=task_repo)

    # Empty existing day
    day = day_repo.create("2026-09-20")
    view = history_service.get_day_history("2026-09-20")
    assert view.tasks == []
    assert view.stats.total == 0
    assert view.stats.completion_percentage == 0.0

    # Non-existent date
    non_view = history_service.get_day_history("2099-01-01")
    assert non_view.day is None
    assert non_view.tasks == []
    assert non_view.stats.total == 0
    # Confirm it did NOT create a record in the database
    assert day_repo.get_by_date("2099-01-01") is None


def test_historical_isolation_and_rollover_records(db_connection):
    """Verify rollover source and target tasks remain distinct and accurately presented."""
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    task_service = TaskService(task_repo)
    rollover = DailyRolloverService(conn=db_connection, day_repo=day_repo, task_repo=task_repo)
    history = HistoryService(day_repo=day_repo, task_repo=task_repo)

    day_a = day_repo.create("2026-09-21")
    t_a = task_service.create_task(day_a.id, "Incomplete Rollover Task", priority=TaskPriority.HIGH)

    day_b = day_repo.create("2026-09-22")
    rolled = rollover.rollover_tasks(source_date="2026-09-21", target_date="2026-09-22")
    assert len(rolled) == 1
    t_b = rolled[0]

    # Complete task on Day B only
    task_service.toggle_task_completion(t_b.id, True)

    # Check Day A history
    view_a = history.get_day_history("2026-09-21")
    assert len(view_a.tasks) == 1
    assert view_a.tasks[0].id == t_a.id
    assert view_a.tasks[0].is_completed is False
    assert view_a.stats.completed == 0

    # Check Day B history
    view_b = history.get_day_history("2026-09-22")
    assert len(view_b.tasks) == 1
    assert view_b.tasks[0].id == t_b.id
    assert view_b.tasks[0].source_task_id == t_a.id
    assert view_b.tasks[0].is_completed is True
    assert view_b.stats.completed == 1


def test_historical_immutability_on_query(db_connection):
    """Verify querying history performs zero writes, updates, or deletes."""
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    task_service = TaskService(task_repo)
    history = HistoryService(day_repo=day_repo, task_repo=task_repo)

    day = day_repo.create("2026-09-23")
    t = task_service.create_task(day.id, "Static Task")

    initial_t = task_repo.get_by_id(t.id)

    # Perform repeated history queries
    for _ in range(5):
        _ = history.get_day_history("2026-09-23")
        _ = history.get_available_dates()

    after_t = task_repo.get_by_id(t.id)
    assert after_t == initial_t
    assert after_t.updated_at == initial_t.updated_at
