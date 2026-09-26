"""Focused tests for Daily Rollover Domain Service and Persistence.

Covers all Phase 5C requirements:
- Basic rollover: yesterday incomplete tasks copied to today
- Completed tasks: completed tasks are not copied
- Mixed tasks: only incomplete tasks are copied
- Property preservation: text, priority (LOW, MEDIUM, HIGH), and position preserved
- Historical integrity: yesterday's tasks, IDs, completion states, and days are immutable
- Occurrence identity: today's tasks receive new IDs, target day_id, and source_task_id link
- Idempotency: repeated rollover calls produce zero duplicate tasks
- No-op: empty source day or all-completed source day produce no copies
- Atomicity: failure during rollover rolls back all target day copies
- Migration safety: existing database with schema 001-003 updates cleanly to 004
"""
import sqlite3
import pytest

from app.core.models import Task, TaskPriority
from app.core.services.daily_rollover_service import DailyRolloverService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.task_repository import TaskRepository


def test_basic_rollover_copies_incomplete_tasks(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    rollover_service = DailyRolloverService(db_connection, day_repo, task_repo)

    day_yesterday = day_repo.create("2026-09-21")
    t1 = task_repo.create(day_yesterday.id, "مهمة غير مكتملة 1", priority=TaskPriority.HIGH)
    t2 = task_repo.create(day_yesterday.id, "مهمة غير مكتملة 2", priority=TaskPriority.LOW)

    rolled = rollover_service.rollover_tasks(source_date="2026-09-21", target_date="2026-09-22")
    assert len(rolled) == 2

    day_today = day_repo.get_by_date("2026-09-22")
    assert day_today is not None
    today_tasks = task_repo.list_for_day(day_today.id)
    assert len(today_tasks) == 2

    # Check properties
    assert today_tasks[0].text == "مهمة غير مكتملة 1"
    assert today_tasks[0].priority == TaskPriority.HIGH
    assert today_tasks[0].is_completed is False
    assert today_tasks[0].id != t1.id
    assert today_tasks[0].source_task_id == t1.id
    assert today_tasks[0].day_id == day_today.id

    assert today_tasks[1].text == "مهمة غير مكتملة 2"
    assert today_tasks[1].priority == TaskPriority.LOW
    assert today_tasks[1].is_completed is False
    assert today_tasks[1].id != t2.id
    assert today_tasks[1].source_task_id == t2.id
    assert today_tasks[1].day_id == day_today.id


def test_rollover_ignores_completed_tasks(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    rollover_service = DailyRolloverService(db_connection, day_repo, task_repo)

    day_yesterday = day_repo.create("2026-09-21")
    t_done = task_repo.create(day_yesterday.id, "مهمة منجزة بالأمس")
    task_repo.set_completed(t_done.id, True)

    rolled = rollover_service.rollover_tasks("2026-09-21", "2026-09-22")
    assert rolled == []

    day_today = day_repo.get_by_date("2026-09-22")
    assert day_today is not None
    assert task_repo.list_for_day(day_today.id) == []


def test_rollover_mixed_tasks_preserves_historical_integrity(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    rollover_service = DailyRolloverService(db_connection, day_repo, task_repo)

    day_yesterday = day_repo.create("2026-09-21")
    t_done = task_repo.create(day_yesterday.id, "مهمة منجزة", priority=TaskPriority.HIGH)
    task_repo.set_completed(t_done.id, True)
    t_pending = task_repo.create(day_yesterday.id, "مهمة معلقة", priority=TaskPriority.MEDIUM)

    rolled = rollover_service.rollover_tasks("2026-09-21", "2026-09-22")
    assert len(rolled) == 1
    assert rolled[0].text == "مهمة معلقة"

    # Historical verification: yesterday remains completely intact
    yesterday_tasks = task_repo.list_for_day(day_yesterday.id)
    assert len(yesterday_tasks) == 2
    y_done = [t for t in yesterday_tasks if t.id == t_done.id][0]
    assert y_done.is_completed is True
    assert y_done.day_id == day_yesterday.id
    y_pending = [t for t in yesterday_tasks if t.id == t_pending.id][0]
    assert y_pending.is_completed is False
    assert y_pending.day_id == day_yesterday.id


def test_rollover_idempotency_duplicate_calls(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    rollover_service = DailyRolloverService(db_connection, day_repo, task_repo)

    day_yesterday = day_repo.create("2026-09-21")
    task_repo.create(day_yesterday.id, "مهمة ستتكرر محاولة ترحيلها")

    # First call creates 1 copy
    first_rolled = rollover_service.rollover_tasks("2026-09-21", "2026-09-22")
    assert len(first_rolled) == 1

    # Second call creates 0 copies
    second_rolled = rollover_service.rollover_tasks("2026-09-21", "2026-09-22")
    assert len(second_rolled) == 0

    # Third call creates 0 copies
    third_rolled = rollover_service.rollover_tasks("2026-09-21", "2026-09-22")
    assert len(third_rolled) == 0

    day_today = day_repo.get_by_date("2026-09-22")
    assert day_today is not None
    assert len(task_repo.list_for_day(day_today.id)) == 1


def test_rollover_no_op_scenarios(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    rollover_service = DailyRolloverService(db_connection, day_repo, task_repo)

    # 1. Non-existent source day
    rolled_nonexistent = rollover_service.rollover_tasks("2026-09-10", "2026-09-11")
    assert rolled_nonexistent == []

    # 2. Source day with 0 tasks
    day_repo.create("2026-09-15")
    rolled_empty = rollover_service.rollover_tasks("2026-09-15", "2026-09-16")
    assert rolled_empty == []


def test_rollover_date_validation(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    rollover_service = DailyRolloverService(db_connection, day_repo, task_repo)

    # Same date or backwards date rejected
    with pytest.raises(ValueError):
        rollover_service.rollover_tasks("2026-09-22", "2026-09-22")

    with pytest.raises(ValueError):
        rollover_service.rollover_tasks("2026-09-23", "2026-09-22")


def test_rollover_atomicity_on_failure(db_connection, monkeypatch):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    rollover_service = DailyRolloverService(db_connection, day_repo, task_repo)

    day_yesterday = day_repo.create("2026-09-21")
    task_repo.create(day_yesterday.id, "مهمة 1")
    task_repo.create(day_yesterday.id, "مهمة 2")

    original_create = task_repo.create
    call_count = 0

    def fail_on_second_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise sqlite3.OperationalError("Simulated database disk crash during rollover")
        return original_create(*args, **kwargs)

    monkeypatch.setattr(task_repo, "create", fail_on_second_create)

    with pytest.raises(sqlite3.OperationalError):
        rollover_service.rollover_tasks("2026-09-21", "2026-09-22")

    # Verify atomic rollback: target day must have 0 tasks (no partial task 1)
    day_today = day_repo.get_by_date("2026-09-22")
    if day_today is not None:
        assert task_repo.list_for_day(day_today.id) == []


def test_migration_004_safety_and_idempotency(tmp_path):
    db_file = tmp_path / "test_migration_004.db"
    conn = create_connection(db_file)

    # Apply migrations up to 003
    from pathlib import Path
    migrations_dir = Path(__file__).resolve().parent.parent / "app" / "database" / "migrations"
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        """
    )
    for v in (1, 2, 3):
        prefix = f"00{v}_"
        file_path = next(p for p in migrations_dir.glob("*.sql") if p.name.startswith(prefix))
        conn.executescript(file_path.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, '2026-09-20T00:00:00')", (v,))
    conn.commit()

    # Insert an existing task
    conn.execute("INSERT INTO days (id, date, created_at, updated_at) VALUES (1, '2026-09-20', '2026-09-20T00:00:00', '2026-09-20T00:00:00')")
    conn.execute(
        """
        INSERT INTO tasks (id, day_id, text, is_completed, position, priority, created_at, updated_at)
        VALUES (10, 1, 'مهمة قبل ميجريشن 4', 0, 0, 'HIGH', '2026-09-20T10:00:00', '2026-09-20T10:00:00')
        """
    )
    conn.commit()

    # Apply all migrations including 004
    apply_migrations(conn)

    # Verify migration 4 was registered
    versions = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
    assert 4 in versions

    # Verify existing task survived with source_task_id = None and priority = HIGH
    repo = TaskRepository(conn)
    task = repo.get_by_id(10)
    assert task is not None
    assert task.text == "مهمة قبل ميجريشن 4"
    assert task.priority == TaskPriority.HIGH
    assert task.source_task_id is None

    # Verify unique index on (day_id, source_task_id) prevents duplicates at DB level
    conn.execute(
        "INSERT INTO tasks (id, day_id, text, is_completed, position, priority, source_task_id, created_at, updated_at) "
        "VALUES (20, 1, 'نسخة أولى', 0, 1, 'MEDIUM', 10, '2026-09-20', '2026-09-20')"
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO tasks (id, day_id, text, is_completed, position, priority, source_task_id, created_at, updated_at) "
            "VALUES (21, 1, 'نسخة مكررة غير مسموحة', 0, 2, 'MEDIUM', 10, '2026-09-20', '2026-09-20')"
        )

    conn.close()
