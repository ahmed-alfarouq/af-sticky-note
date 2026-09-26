"""Tests for Phase 5I — Context Menu, Task Editing, Deletion, and Clear Completed."""
import sqlite3
import pytest

from app.core.models import Day, Task, TaskPriority
from app.core.services.daily_rollover_service import DailyRolloverService
from app.core.services.task_service import TaskService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.task_repository import TaskRepository


def test_edit_task_preserves_id_day_priority_and_completion(db_connection):
    """Verify editing task text preserves all metadata and relationships."""
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)

    day = day_repo.get_or_create("2026-09-26")
    created = service.create_task(day.id, "Original Task", priority=TaskPriority.HIGH)
    assert created is not None

    service.toggle_task_completion(created.id, True)

    # Edit task text
    success = service.update_task_text(created.id, "Updated Task Text")
    assert success is True

    # Retrieve and verify
    updated = task_repo.get_by_id(created.id)
    assert updated.id == created.id
    assert updated.day_id == day.id
    assert updated.text == "Updated Task Text"
    assert updated.priority == TaskPriority.HIGH
    assert updated.is_completed is True


def test_edit_task_rejects_empty_or_whitespace(db_connection):
    """Verify editing text with blank or whitespace-only strings fails."""
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)

    day = day_repo.get_or_create("2026-09-26")
    created = service.create_task(day.id, "Valid Task")

    assert service.update_task_text(created.id, "") is False
    assert service.update_task_text(created.id, "   ") is False

    task = task_repo.get_by_id(created.id)
    assert task.text == "Valid Task"


def test_delete_task_removes_only_target_task(db_connection):
    """Verify deleting a task deletes only that task and keeps others intact."""
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)

    day = day_repo.get_or_create("2026-09-26")
    t1 = service.create_task(day.id, "Task 1")
    t2 = service.create_task(day.id, "Task 2")

    service.delete_task(t1.id)

    tasks = service.get_today_tasks(day.id)
    assert len(tasks) == 1
    assert tasks[0].id == t2.id
    assert task_repo.get_by_id(t1.id) is None


def test_clear_completed_tasks_scoped_to_current_day(db_connection):
    """Verify clear completed removes completed tasks for target day only."""
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)

    day_prev = day_repo.get_or_create("2026-09-25")
    day_curr = day_repo.get_or_create("2026-09-26")

    # Day prev completed task
    t_prev = service.create_task(day_prev.id, "Prev Day Task")
    service.toggle_task_completion(t_prev.id, True)

    # Day curr tasks
    t_curr_inc = service.create_task(day_curr.id, "Curr Incomplete")
    t_curr_comp = service.create_task(day_curr.id, "Curr Completed")
    service.toggle_task_completion(t_curr_comp.id, True)

    # Clear completed on day_curr
    deleted_count = service.clear_completed_tasks(day_curr.id)
    assert deleted_count == 1

    # Current day checks
    curr_tasks = service.get_today_tasks(day_curr.id)
    assert len(curr_tasks) == 1
    assert curr_tasks[0].id == t_curr_inc.id

    # Previous day remains completely untouched
    prev_tasks = service.get_today_tasks(day_prev.id)
    assert len(prev_tasks) == 1
    assert prev_tasks[0].id == t_prev.id
    assert prev_tasks[0].is_completed is True


def test_rollover_historical_immutability_on_edit_and_delete(db_connection):
    """Verify editing/deleting a rollover task does NOT affect historical source task."""
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)
    rollover = DailyRolloverService(conn=db_connection, day_repo=day_repo, task_repo=task_repo)

    day_a = day_repo.get_or_create("2026-09-25")
    task_a = service.create_task(day_a.id, "Source Task A", priority=TaskPriority.HIGH)

    # Perform rollover to Day B
    day_b = day_repo.get_or_create("2026-09-26")
    rolled_tasks = rollover.rollover_tasks(source_date="2026-09-25", target_date="2026-09-26")
    assert len(rolled_tasks) == 1

    tasks_b = service.get_today_tasks(day_b.id)
    assert len(tasks_b) == 1
    task_b = tasks_b[0]
    assert task_b.source_task_id == task_a.id

    # 1. Edit Day B copy
    service.update_task_text(task_b.id, "Modified Task B Text")
    source_after_edit = task_repo.get_by_id(task_a.id)
    assert source_after_edit.text == "Source Task A"  # Source remains unchanged!

    # 2. Complete and Clear on Day B
    service.toggle_task_completion(task_b.id, True)
    service.clear_completed_tasks(day_b.id)

    assert len(service.get_today_tasks(day_b.id)) == 0

    # Historical day A remains completely intact
    historical_a = service.get_today_tasks(day_a.id)
    assert len(historical_a) == 1
    assert historical_a[0].id == task_a.id
    assert historical_a[0].text == "Source Task A"
    assert historical_a[0].is_completed is False
