"""Phase 6A — priority selection, persistence, rollover, and history.

UI interaction is covered in test_task_priority_ui.py. These tests stay
free of Qt so they run in any environment.
"""
import pytest

from app.core.models import TaskPriority
from app.core.services.daily_rollover_service import DailyRolloverService
from app.core.services.history_service import HistoryService
from app.core.services.task_service import TaskService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.task_repository import TaskRepository


def _services(conn):
    day_repo = DayRepository(conn)
    task_repo = TaskRepository(conn)
    return day_repo, task_repo, TaskService(task_repo)


def test_default_create_is_medium_and_explicit_priorities_persist(db_connection):
    day_repo, task_repo, service = _services(db_connection)
    day = day_repo.get_or_create("2026-09-27")

    medium = service.create_task(day.id, "مهمة عادية")
    high = service.create_task(day.id, "مهمة عاجلة", priority=TaskPriority.HIGH)
    low = service.create_task(day.id, "مهمة منخفضة", priority=TaskPriority.LOW)

    assert medium.priority == TaskPriority.MEDIUM
    assert high.priority == TaskPriority.HIGH
    assert low.priority == TaskPriority.LOW

    reloaded = {task.id: task for task in service.get_today_tasks(day.id)}
    assert reloaded[medium.id].priority == TaskPriority.MEDIUM
    assert reloaded[high.id].priority == TaskPriority.HIGH
    assert reloaded[low.id].priority == TaskPriority.LOW
    assert reloaded[high.id].text == "مهمة عاجلة"


def test_priority_survives_database_reopen(db_path):
    conn = create_connection(db_path)
    apply_migrations(conn)
    day_repo, _, service = _services(conn)
    day = day_repo.get_or_create("2026-09-27")
    created = service.create_task(day.id, "تبقى عاجلة", priority=TaskPriority.HIGH)
    task_id = created.id
    conn.close()

    reopened = create_connection(db_path)
    try:
        task = TaskRepository(reopened).get_by_id(task_id)
        assert task is not None
        assert task.priority == TaskPriority.HIGH
        assert task.text == "تبقى عاجلة"
        assert task.day_id == day.id
    finally:
        reopened.close()


def test_combined_edit_persists_text_and_priority_together(db_connection):
    day_repo, task_repo, service = _services(db_connection)
    day = day_repo.get_or_create("2026-09-27")
    created = service.create_task(day.id, "نص أصلي", priority=TaskPriority.MEDIUM)
    service.toggle_task_completion(created.id, True)

    assert service.update_task_text_and_priority(created.id, "نص جديد", TaskPriority.HIGH) is True

    updated = task_repo.get_by_id(created.id)
    assert updated.id == created.id
    assert updated.day_id == day.id
    assert updated.text == "نص جديد"
    assert updated.priority == TaskPriority.HIGH
    assert updated.is_completed is True
    assert updated.position == created.position
    assert updated.source_task_id is None


def test_combined_edit_rejects_blank_text_without_writing_priority(db_connection):
    day_repo, task_repo, service = _services(db_connection)
    day = day_repo.get_or_create("2026-09-27")
    created = service.create_task(day.id, "لا تتغير", priority=TaskPriority.LOW)
    before = task_repo.get_by_id(created.id)

    assert service.update_task_text_and_priority(created.id, "   ", TaskPriority.HIGH) is False
    assert service.update_task_text_and_priority(created.id, "", TaskPriority.HIGH) is False

    after = task_repo.get_by_id(created.id)
    assert after == before
    assert after.priority == TaskPriority.LOW
    assert after.updated_at == before.updated_at


def test_combined_edit_noop_does_not_touch_timestamp(db_connection):
    day_repo, task_repo, service = _services(db_connection)
    day = day_repo.get_or_create("2026-09-27")
    created = service.create_task(day.id, "كما هي", priority=TaskPriority.HIGH)
    before = task_repo.get_by_id(created.id)

    assert service.update_task_text_and_priority(created.id, "كما هي", TaskPriority.HIGH) is True

    after = task_repo.get_by_id(created.id)
    assert after == before
    assert after.updated_at == before.updated_at


def test_combined_edit_invalid_priority_writes_nothing(db_connection):
    day_repo, task_repo, service = _services(db_connection)
    day = day_repo.get_or_create("2026-09-27")
    created = service.create_task(day.id, "محمية", priority=TaskPriority.MEDIUM)
    before = task_repo.get_by_id(created.id)

    with pytest.raises(ValueError):
        service.update_task_text_and_priority(created.id, "نص جديد", "URGENT")  # type: ignore

    after = task_repo.get_by_id(created.id)
    assert after.text == before.text
    assert after.priority == TaskPriority.MEDIUM
    assert after.updated_at == before.updated_at


def test_priority_only_update_preserves_identity_and_text(db_connection):
    day_repo, task_repo, service = _services(db_connection)
    day = day_repo.get_or_create("2026-09-27")
    created = service.create_task(day.id, "النص ثابت", priority=TaskPriority.MEDIUM)

    service.update_task_priority(created.id, TaskPriority.LOW)
    updated = task_repo.get_by_id(created.id)
    assert updated.id == created.id
    assert updated.day_id == day.id
    assert updated.text == "النص ثابت"
    assert updated.priority == TaskPriority.LOW
    assert updated.is_completed is False
    assert updated.position == created.position

    service.update_task_priority(created.id, TaskPriority.HIGH)
    assert task_repo.get_by_id(created.id).priority == TaskPriority.HIGH
    service.update_task_priority(created.id, TaskPriority.MEDIUM)
    assert task_repo.get_by_id(created.id).priority == TaskPriority.MEDIUM
    assert task_repo.get_by_id(created.id).text == "النص ثابت"


def test_rollover_preserves_priority_and_history_stays_immutable(db_connection):
    day_repo, task_repo, service = _services(db_connection)
    rollover = DailyRolloverService(conn=db_connection, day_repo=day_repo, task_repo=task_repo)
    history = HistoryService(day_repo=day_repo, task_repo=task_repo)

    day_a = day_repo.get_or_create("2026-09-26")
    pending = service.create_task(day_a.id, "غير مكتملة", priority=TaskPriority.HIGH)
    done = service.create_task(day_a.id, "مكتملة", priority=TaskPriority.LOW)
    service.toggle_task_completion(done.id, True)

    day_b = day_repo.get_or_create("2026-09-27")
    rolled = rollover.rollover_tasks(source_date="2026-09-26", target_date="2026-09-27")
    assert len(rolled) == 1
    copy = rolled[0]
    assert copy.priority == TaskPriority.HIGH
    assert copy.text == "غير مكتملة"
    assert copy.is_completed is False
    assert copy.source_task_id == pending.id
    assert copy.id != pending.id
    assert copy.day_id == day_b.id

    # Completed task is not copied, and its priority stays on the source day.
    today = service.get_today_tasks(day_b.id)
    assert [task.id for task in today] == [copy.id]
    historical_done = task_repo.get_by_id(done.id)
    assert historical_done.is_completed is True
    assert historical_done.priority == TaskPriority.LOW
    assert historical_done.day_id == day_a.id

    # Changing the new occurrence must not rewrite Day 1.
    service.update_task_priority(copy.id, TaskPriority.LOW)
    service.update_task_text(copy.id, "نسخة اليوم")

    view_a = history.get_day_history("2026-09-26")
    by_id = {task.id: task for task in view_a.tasks}
    assert by_id[pending.id].priority == TaskPriority.HIGH
    assert by_id[pending.id].text == "غير مكتملة"
    assert by_id[pending.id].is_completed is False
    assert by_id[done.id].priority == TaskPriority.LOW

    view_b = history.get_day_history("2026-09-27")
    assert len(view_b.tasks) == 1
    assert view_b.tasks[0].id == copy.id
    assert view_b.tasks[0].priority == TaskPriority.LOW
    assert view_b.tasks[0].text == "نسخة اليوم"
    assert view_b.tasks[0].source_task_id == pending.id


def test_stylesheet_alignment_expression_does_not_drop_later_rules():
    """Qt rejects ``qproperty-alignment: AlignRight | AlignVCenter`` and then
    drops every stylesheet rule after it, including priority badges.
    """
    from app.ui.styles.app_style import get_application_stylesheet

    stylesheet = get_application_stylesheet()
    assert "qproperty-alignment: Align" not in stylesheet
    assert "QLabel#priorityBadgeHigh" in stylesheet
    assert "QToolButton#taskPriorityButton" in stylesheet


def test_priority_does_not_reorder_tasks(db_connection):
    day_repo, _, service = _services(db_connection)
    day = day_repo.get_or_create("2026-09-27")
    first = service.create_task(day.id, "أولاً", priority=TaskPriority.LOW)
    second = service.create_task(day.id, "ثانياً", priority=TaskPriority.HIGH)
    tasks = service.get_today_tasks(day.id)
    assert [task.id for task in tasks] == [first.id, second.id]
