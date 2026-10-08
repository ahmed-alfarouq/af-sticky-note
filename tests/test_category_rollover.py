"""Phase 7A: rollover preserves task categories.

Backend-only (stdlib + sqlite3, no Qt). Verifies that DailyRolloverService
carries category_id onto copied tasks while keeping every existing guarantee
(new ids, incomplete copies, idempotency, untouched sources).
"""
from app.core.services.daily_rollover_service import DailyRolloverService
from app.core.services.task_service import TaskService
from app.database.category_repository import CategoryRepository
from app.database.day_repository import DayRepository
from app.database.task_repository import TaskRepository


def _wiring(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    category_repo = CategoryRepository(db_connection)
    service = TaskService(task_repo=task_repo, category_repo=category_repo)
    rollover = DailyRolloverService(conn=db_connection, day_repo=day_repo, task_repo=task_repo)
    return day_repo, task_repo, service, rollover


def test_rollover_inherits_source_category(db_connection):
    day_repo, task_repo, service, rollover = _wiring(db_connection)
    source = day_repo.get_or_create("2026-09-20")
    original = service.create_task(source.id, "مهمة عمل", category_id="work")
    assert original is not None

    created = rollover.rollover_tasks("2026-09-20", "2026-09-21")
    assert len(created) == 1
    assert created[0].id != original.id
    assert created[0].category_id == "work"
    assert created[0].is_completed is False
    assert created[0].text == original.text
    assert created[0].priority == original.priority
    assert created[0].source_task_id == original.id
    # Source row untouched.
    assert task_repo.get_by_id(original.id).category_id == "work"


def test_rollover_preserves_mixed_categories(db_connection):
    day_repo, _, service, rollover = _wiring(db_connection)
    source = day_repo.get_or_create("2026-09-20")
    service.create_task(source.id, "دين", category_id="religion")
    service.create_task(source.id, "حياة", category_id="life")
    service.create_task(source.id, "عام")

    created = rollover.rollover_tasks("2026-09-20", "2026-09-21")
    assert sorted(t.category_id for t in created) == ["general", "life", "religion"]


def test_rollover_category_survives_multiple_days(db_connection):
    day_repo, _, service, rollover = _wiring(db_connection)
    day1 = day_repo.get_or_create("2026-09-20")
    service.create_task(day1.id, "متابعة يومية", category_id="work")

    rollover.rollover_tasks("2026-09-20", "2026-09-21")
    created = rollover.rollover_tasks("2026-09-21", "2026-09-22")
    assert len(created) == 1
    assert created[0].category_id == "work"

    day3 = day_repo.get_by_date("2026-09-22")
    assert day3 is not None
    assert [t.category_id for t in TaskRepository(db_connection).list_for_day(day3.id)] == ["work"]


def test_completed_tasks_are_not_copied_regardless_of_category(db_connection):
    day_repo, _, service, rollover = _wiring(db_connection)
    source = day_repo.get_or_create("2026-09-20")
    done = service.create_task(source.id, "منجزة", category_id="work")
    assert done is not None
    service.toggle_task_completion(done.id, True)

    assert rollover.rollover_tasks("2026-09-20", "2026-09-21") == []
    target = day_repo.get_by_date("2026-09-21")
    assert target is not None
    assert TaskRepository(db_connection).list_for_day(target.id) == []


def test_rollover_with_category_stays_idempotent(db_connection):
    day_repo, _, service, rollover = _wiring(db_connection)
    source = day_repo.get_or_create("2026-09-20")
    service.create_task(source.id, "مهمة", category_id="life")

    first = rollover.rollover_tasks("2026-09-20", "2026-09-21")
    assert len(first) == 1
    assert rollover.rollover_tasks("2026-09-20", "2026-09-21") == []

    target = day_repo.get_by_date("2026-09-21")
    assert target is not None
    rows = TaskRepository(db_connection).list_for_day(target.id)
    assert len(rows) == 1
    assert rows[0].category_id == "life"
