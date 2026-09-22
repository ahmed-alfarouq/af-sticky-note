"""Tests for TaskService application behavior.

Validates that TaskService properly manages task creation, validation,
completion, and retrieval while delegating persistence to TaskRepository.
"""
import pytest

from app.core.services.task_service import TaskService
from app.database.day_repository import DayRepository
from app.database.task_repository import TaskRepository


def _make_day(db_connection, date="2026-09-22"):
    return DayRepository(db_connection).create(date)


def test_task_service_create_valid_task(db_connection):
    day = _make_day(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)

    task = service.create_task(day.id, "مهمة اختبارية")
    assert task is not None
    assert task.text == "مهمة اختبارية"
    assert task.is_completed is False
    assert task.day_id == day.id

    tasks = service.get_today_tasks(day.id)
    assert len(tasks) == 1
    assert tasks[0].id == task.id


def test_task_service_strips_whitespace(db_connection):
    day = _make_day(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)

    task = service.create_task(day.id, "   مهمة مع مسافات   ")
    assert task is not None
    assert task.text == "مهمة مع مسافات"


def test_task_service_rejects_empty_task(db_connection):
    day = _make_day(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)

    task_empty = service.create_task(day.id, "")
    assert task_empty is None

    task_whitespace = service.create_task(day.id, "    \n\t  ")
    assert task_whitespace is None

    # Database must have 0 tasks created
    tasks = service.get_today_tasks(day.id)
    assert len(tasks) == 0


def test_task_service_toggle_completion(db_connection):
    day = _make_day(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)

    task = service.create_task(day.id, "مهمة قابلة للإنجاز")
    assert task is not None
    assert task.is_completed is False

    service.toggle_task_completion(task.id, True)
    updated = service.get_today_tasks(day.id)
    assert len(updated) == 1
    assert updated[0].is_completed is True

    service.toggle_task_completion(task.id, False)
    updated_again = service.get_today_tasks(day.id)
    assert updated_again[0].is_completed is False


def test_task_service_delete_task(db_connection):
    day = _make_day(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)

    task = service.create_task(day.id, "مهمة للحذف")
    assert task is not None
    assert len(service.get_today_tasks(day.id)) == 1

    service.delete_task(task.id)
    assert len(service.get_today_tasks(day.id)) == 0


def test_task_service_update_text(db_connection):
    day = _make_day(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)

    task = service.create_task(day.id, "نص أصلي")
    assert task is not None

    # Empty update rejected
    assert service.update_task_text(task.id, "   ") is False
    assert service.get_today_tasks(day.id)[0].text == "نص أصلي"

    # Valid update accepted
    assert service.update_task_text(task.id, "نص محدث جديد") is True
    assert service.get_today_tasks(day.id)[0].text == "نص محدث جديد"
