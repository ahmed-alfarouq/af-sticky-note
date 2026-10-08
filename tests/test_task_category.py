"""Phase 7A: category domain, repository, and TaskService integration tests.

Backend-only (stdlib + sqlite3, no Qt). All fixtures use the shared
tmp_path database with all migrations applied (see tests/conftest.py).
"""
import sqlite3

import pytest

from app.core.models import DEFAULT_CATEGORY_ID, Category
from app.core.services.task_service import TaskService
from app.database.category_repository import CategoryRepository
from app.database.day_repository import DayRepository
from app.database.task_repository import TaskRepository


def _make_day(db_connection, date="2026-09-22"):
    return DayRepository(db_connection).create(date)


def _service(db_connection, with_categories=True):
    task_repo = TaskRepository(db_connection)
    category_repo = CategoryRepository(db_connection) if with_categories else None
    return TaskService(task_repo=task_repo, category_repo=category_repo)


# ------------------------------------------------------------ model contract

def test_default_category_id_is_stable_string():
    assert DEFAULT_CATEGORY_ID == "general"
    assert isinstance(DEFAULT_CATEGORY_ID, str)


def test_category_model_is_qt_free_and_sql_free():
    category = Category(
        id="work",
        name_ar="عمل",
        icon_key="work",
        sort_order=20,
        is_active=True,
        created_at="t",
        updated_at="t",
    )
    assert category.id == "work"
    assert category.name_ar == "عمل"
    assert category.icon_key == "work"


# ------------------------------------------------------------ repository reads

def test_list_all_returns_seeds_in_sort_order(db_connection):
    categories = CategoryRepository(db_connection).list_all()
    assert [(c.id, c.sort_order) for c in categories] == [
        ("religion", 10),
        ("work", 20),
        ("life", 30),
        ("general", 40),
    ]


def test_list_active_excludes_deactivated(db_connection):
    repo = CategoryRepository(db_connection)
    assert len(repo.list_active()) == 4
    repo.set_active("work", False)
    assert [c.id for c in repo.list_active()] == ["religion", "life", "general"]
    # Full listing still contains the inactive row (history stays valid).
    assert len(repo.list_all()) == 4


def test_get_by_id_returns_none_for_unknown(db_connection):
    assert CategoryRepository(db_connection).get_by_id("nope") is None


# ------------------------------------------------------------ creation defaults

def test_new_task_defaults_to_general_category(db_connection):
    day = _make_day(db_connection)
    task = _service(db_connection).create_task(day.id, "مهمة بدون فئة")
    assert task is not None
    assert task.category_id == "general"
    assert CategoryRepository(db_connection).get_by_id(task.category_id) is not None


def test_task_creation_without_category_repo_still_works(db_connection):
    """Existing call sites that omit the category repo keep working."""
    day = _make_day(db_connection)
    task = _service(db_connection, with_categories=False).create_task(day.id, "مهمة قديمة الأسلوب")
    assert task is not None
    assert task.category_id == "general"


def test_explicit_category_assignment(db_connection):
    day = _make_day(db_connection)
    service = _service(db_connection)
    task = service.create_task(day.id, "مهمة عمل", category_id="work")
    assert task is not None
    assert task.category_id == "work"
    assert service.get_today_tasks(day.id)[0].category_id == "work"


# ------------------------------------------------------------ validation

def test_unknown_category_is_rejected_not_defaulted(db_connection):
    service = _service(db_connection)
    day = _make_day(db_connection)
    with pytest.raises(ValueError):
        service.create_task(day.id, "مهمة مشبوهة", category_id="nope")
    assert service.get_today_tasks(day.id) == []


def test_empty_category_is_rejected(db_connection):
    service = _service(db_connection)
    day = _make_day(db_connection)
    with pytest.raises(ValueError):
        service.create_task(day.id, "x", category_id="")
    with pytest.raises(ValueError):
        service.create_task(day.id, "x", category_id=123)  # type: ignore


def test_none_category_means_default_on_create(db_connection):
    day = _make_day(db_connection)
    task = _service(db_connection).create_task(day.id, "مهمة", category_id=None)
    assert task is not None
    assert task.category_id == "general"


def test_repository_rejects_unknown_category_at_insert(db_connection):
    day = _make_day(db_connection)
    with pytest.raises(sqlite3.IntegrityError):
        TaskRepository(db_connection).create(day.id, "x", category_id="nope")


def test_repository_rejects_empty_category_value(db_connection):
    day = _make_day(db_connection)
    with pytest.raises(ValueError):
        TaskRepository(db_connection).create(day.id, "x", category_id="")


# ------------------------------------------------------------ updates

def test_update_task_category(db_connection):
    day = _make_day(db_connection)
    service = _service(db_connection)
    task = service.create_task(day.id, "مهمة")
    assert task is not None and task.category_id == "general"

    service.update_task_category(task.id, "religion")
    assert service.get_today_tasks(day.id)[0].category_id == "religion"

    service.update_task_category(task.id, "life")
    assert service.get_today_tasks(day.id)[0].category_id == "life"


def test_update_to_unknown_or_none_category_is_rejected(db_connection):
    day = _make_day(db_connection)
    service = _service(db_connection)
    task = service.create_task(day.id, "مهمة")
    assert task is not None

    with pytest.raises(ValueError):
        service.update_task_category(task.id, "nope")
    with pytest.raises(ValueError):
        service.update_task_category(task.id, None)  # type: ignore
    with pytest.raises(ValueError):
        service.update_task_category(task.id, "")
    assert service.get_today_tasks(day.id)[0].category_id == "general"


# ------------------------------------------------------------ compatibility

def test_priority_defaults_and_validation_unchanged(db_connection):
    from app.core.models import TaskPriority

    day = _make_day(db_connection)
    service = _service(db_connection)
    task = service.create_task(day.id, "مهمة")
    assert task is not None
    assert task.priority == TaskPriority.MEDIUM
    with pytest.raises(ValueError):
        service.create_task(day.id, "x", priority="INVALID")  # type: ignore
