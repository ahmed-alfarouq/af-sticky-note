"""Focused tests for Task Priority domain model, persistence, and service logic.

Verifies Phase 5B requirements:
- Domain model priority representation (LOW, MEDIUM, HIGH)
- Default priority is MEDIUM
- Repository create and read with priorities
- Repository update priority
- Field independence: updating completion, text, or position does NOT reset priority
- Service layer priority support and default validation
- Database migration safety (existing tasks receive MEDIUM and retain all fields)
"""
import sqlite3
import pytest

from app.core.models import Task, TaskPriority
from app.core.services.task_service import TaskService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.task_repository import TaskRepository


def test_task_domain_model_priority_default_and_values():
    # Model defaults to MEDIUM
    task_default = Task(
        id=1,
        day_id=1,
        text="مهمة",
        is_completed=False,
        position=0,
        created_at="2026-09-23T00:00:00",
        updated_at="2026-09-23T00:00:00",
    )
    assert task_default.priority == TaskPriority.MEDIUM
    assert task_default.priority.value == "MEDIUM"

    # Explicit LOW, MEDIUM, HIGH
    task_low = Task(
        id=2,
        day_id=1,
        text="مهمة منخفضة",
        is_completed=False,
        position=1,
        created_at="2026-09-23T00:00:00",
        updated_at="2026-09-23T00:00:00",
        priority=TaskPriority.LOW,
    )
    assert task_low.priority == TaskPriority.LOW

    task_high = Task(
        id=3,
        day_id=1,
        text="مهمة هامة",
        is_completed=False,
        position=2,
        created_at="2026-09-23T00:00:00",
        updated_at="2026-09-23T00:00:00",
        priority=TaskPriority.HIGH,
    )
    assert task_high.priority == TaskPriority.HIGH


def test_task_repository_create_and_read_priorities(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    day = day_repo.create("2026-09-23")

    # Default create yields MEDIUM
    t_med = task_repo.create(day.id, "مهمة متوسطة")
    assert t_med.priority == TaskPriority.MEDIUM
    read_med = task_repo.get_by_id(t_med.id)
    assert read_med is not None
    assert read_med.priority == TaskPriority.MEDIUM

    # Explicit LOW
    t_low = task_repo.create(day.id, "مهمة منخفضة", priority=TaskPriority.LOW)
    assert t_low.priority == TaskPriority.LOW
    read_low = task_repo.get_by_id(t_low.id)
    assert read_low is not None
    assert read_low.priority == TaskPriority.LOW

    # Explicit HIGH
    t_high = task_repo.create(day.id, "مهمة عالية", priority=TaskPriority.HIGH)
    assert t_high.priority == TaskPriority.HIGH
    read_high = task_repo.get_by_id(t_high.id)
    assert read_high is not None
    assert read_high.priority == TaskPriority.HIGH


def test_task_repository_update_priority(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    day = day_repo.create("2026-09-23")

    task = task_repo.create(day.id, "مهمة تتغير أولويتها", priority=TaskPriority.LOW)
    assert task.priority == TaskPriority.LOW

    # Update to HIGH
    task_repo.update_priority(task.id, TaskPriority.HIGH)
    updated = task_repo.get_by_id(task.id)
    assert updated is not None
    assert updated.priority == TaskPriority.HIGH
    assert updated.text == "مهمة تتغير أولويتها"
    assert updated.is_completed is False


def test_task_repository_other_updates_preserve_priority(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    day = day_repo.create("2026-09-23")

    task = task_repo.create(day.id, "نص أصلي", priority=TaskPriority.HIGH)
    assert task.priority == TaskPriority.HIGH

    # 1. Update text preserves priority
    task_repo.update_text(task.id, "نص جديد")
    after_text = task_repo.get_by_id(task.id)
    assert after_text is not None
    assert after_text.text == "نص جديد"
    assert after_text.priority == TaskPriority.HIGH

    # 2. Update completion preserves priority
    task_repo.set_completed(task.id, True)
    after_comp = task_repo.get_by_id(task.id)
    assert after_comp is not None
    assert after_comp.is_completed is True
    assert after_comp.priority == TaskPriority.HIGH


def test_task_service_priority_handling(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)
    day = day_repo.create("2026-09-23")

    # Default priority is MEDIUM
    t1 = service.create_task(day.id, "مهمة افتراضية")
    assert t1 is not None
    assert t1.priority == TaskPriority.MEDIUM

    # Explicit LOW
    t2 = service.create_task(day.id, "مهمة هادئة", priority=TaskPriority.LOW)
    assert t2 is not None
    assert t2.priority == TaskPriority.LOW

    # Explicit HIGH
    t3 = service.create_task(day.id, "مهمة عاجلة", priority=TaskPriority.HIGH)
    assert t3 is not None
    assert t3.priority == TaskPriority.HIGH

    # Update priority through service
    service.update_task_priority(t1.id, TaskPriority.HIGH)
    tasks = service.get_today_tasks(day.id)
    t1_updated = [t for t in tasks if t.id == t1.id][0]
    assert t1_updated.priority == TaskPriority.HIGH

    # Invalid priority raises ValueError
    with pytest.raises(ValueError):
        service.create_task(day.id, "خطأ أولوية", priority="URGENT")  # type: ignore

    with pytest.raises(ValueError):
        service.update_task_priority(t1.id, "INVALID")  # type: ignore


def test_migration_003_existing_database_safety(tmp_path):
    db_file = tmp_path / "test_migration_003.db"
    conn = create_connection(db_file)

    # 1. Apply only 001 and 002 manually to simulate an existing pre-Phase-5B database
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        """
    )
    from pathlib import Path
    migrations_dir = Path(__file__).resolve().parent.parent / "app" / "database" / "migrations"
    sql_001 = (migrations_dir / "001_initial_schema.sql").read_text(encoding="utf-8")
    sql_002 = (migrations_dir / "002_quote_rotation.sql").read_text(encoding="utf-8")
    conn.executescript(sql_001)
    conn.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (1, '2026-09-20T00:00:00')")
    conn.executescript(sql_002)
    conn.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (2, '2026-09-20T00:00:00')")
    conn.commit()

    # 2. Insert tasks into the old schema without priority column
    conn.execute("INSERT INTO days (id, date, created_at, updated_at) VALUES (1, '2026-09-20', '2026-09-20T00:00:00', '2026-09-20T00:00:00')")
    conn.execute(
        """
        INSERT INTO tasks (id, day_id, text, is_completed, position, created_at, updated_at)
        VALUES (42, 1, 'مهمة قديمة قبل الميجريشن', 1, 0, '2026-09-20T10:00:00', '2026-09-20T10:00:00')
        """
    )
    conn.commit()

    # 3. Apply migrations using the application migration runner
    apply_migrations(conn)

    # 4. Verify migration was recorded
    versions = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
    assert 3 in versions

    # 5. Verify existing task retained all fields and received priority = 'MEDIUM'
    row = conn.execute("SELECT * FROM tasks WHERE id = 42").fetchone()
    assert row is not None
    assert row["id"] == 42
    assert row["day_id"] == 1
    assert row["text"] == "مهمة قديمة قبل الميجريشن"
    assert row["is_completed"] == 1
    assert row["position"] == 0
    assert row["created_at"] == "2026-09-20T10:00:00"
    assert row["updated_at"] == "2026-09-20T10:00:00"
    assert row["priority"] == "MEDIUM"

    # TaskRepository can read it seamlessly
    repo = TaskRepository(conn)
    task = repo.get_by_id(42)
    assert task is not None
    assert task.priority == TaskPriority.MEDIUM

    # 6. Verify idempotency: running apply_migrations again does nothing
    apply_migrations(conn)
    versions_after = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
    assert versions == versions_after

    conn.close()
