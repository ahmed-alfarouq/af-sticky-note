import sqlite3

import pytest

from app.database.day_repository import DayRepository
from app.database.task_repository import TaskRepository


def _make_day(db_connection, date="2026-09-21"):
    return DayRepository(db_connection).create(date)


def test_create_task_defaults_incomplete(db_connection):
    day = _make_day(db_connection)
    repo = TaskRepository(db_connection)
    task = repo.create(day.id, "شراء القهوة")
    assert task.is_completed is False
    assert task.position == 0


def test_retrieve_task_by_id(db_connection):
    day = _make_day(db_connection)
    repo = TaskRepository(db_connection)
    created = repo.create(day.id, "مهمة")
    assert repo.get_by_id(created.id) == created


def test_update_task_text(db_connection):
    day = _make_day(db_connection)
    repo = TaskRepository(db_connection)
    task = repo.create(day.id, "نص أصلي")
    repo.update_text(task.id, "نص محدث")
    assert repo.get_by_id(task.id).text == "نص محدث"


def test_mark_task_completed(db_connection):
    day = _make_day(db_connection)
    repo = TaskRepository(db_connection)
    task = repo.create(day.id, "مهمة")
    repo.set_completed(task.id, True)
    assert repo.get_by_id(task.id).is_completed is True


def test_delete_task(db_connection):
    day = _make_day(db_connection)
    repo = TaskRepository(db_connection)
    task = repo.create(day.id, "مهمة للحذف")
    repo.delete(task.id)
    assert repo.get_by_id(task.id) is None


def test_tasks_belong_to_correct_day(db_connection):
    repo = TaskRepository(db_connection)
    day1 = _make_day(db_connection, "2026-09-20")
    day2 = _make_day(db_connection, "2026-09-21")
    repo.create(day1.id, "مهمة اليوم الأول")
    repo.create(day2.id, "مهمة اليوم الثاني")

    assert [t.text for t in repo.list_for_day(day1.id)] == ["مهمة اليوم الأول"]
    assert [t.text for t in repo.list_for_day(day2.id)] == ["مهمة اليوم الثاني"]


def test_invalid_day_id_cannot_create_orphan_task(db_connection):
    repo = TaskRepository(db_connection)
    with pytest.raises(sqlite3.IntegrityError):
        repo.create(day_id=9999, text="مهمة يتيمة")


def test_task_ordering_is_preserved(db_connection):
    day = _make_day(db_connection)
    repo = TaskRepository(db_connection)
    repo.create(day.id, "أولاً")
    repo.create(day.id, "ثانياً")
    repo.create(day.id, "ثالثاً")

    assert [t.text for t in repo.list_for_day(day.id)] == ["أولاً", "ثانياً", "ثالثاً"]