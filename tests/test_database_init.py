import sqlite3

import pytest

from app.database.connection import create_connection
from app.database.migrations import apply_migrations


def test_database_initializes_successfully(db_connection):
    tables = {
        row["name"]
        for row in db_connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {"days", "tasks", "quotes", "schema_migrations"} <= tables


def test_first_migration_is_applied(db_connection):
    versions = {
        row["version"]
        for row in db_connection.execute("SELECT version FROM schema_migrations")
    }
    assert 1 in versions


def test_migration_is_not_applied_twice(db_connection):
    apply_migrations(db_connection)  # must be a safe no-op
    count = db_connection.execute(
        "SELECT COUNT(*) AS c FROM schema_migrations WHERE version = 1"
    ).fetchone()["c"]
    assert count == 1


def test_migration_state_is_recorded(db_connection):
    row = db_connection.execute(
        "SELECT applied_at FROM schema_migrations WHERE version = 1"
    ).fetchone()
    assert row is not None
    assert row["applied_at"]


def test_foreign_keys_are_enforced(db_connection):
    assert db_connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    with pytest.raises(sqlite3.IntegrityError):
        db_connection.execute(
            "INSERT INTO tasks (day_id, text, position, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (9999, "orphan task", 0, "now", "now"),
        )


def test_database_can_be_reopened(db_path):
    conn1 = create_connection(db_path)
    apply_migrations(conn1)
    conn1.close()

    conn2 = create_connection(db_path)
    apply_migrations(conn2)  # already-applied migration must be a no-op
    tables = {
        row["name"]
        for row in conn2.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    conn2.close()
    assert {"days", "tasks", "quotes"} <= tables


def test_existing_data_survives_reopening(db_path):
    from app.database.day_repository import DayRepository
    from app.database.task_repository import TaskRepository

    conn1 = create_connection(db_path)
    apply_migrations(conn1)
    day = DayRepository(conn1).create("2026-09-21")
    TaskRepository(conn1).create(day.id, "مهمة محفوظة")
    conn1.close()

    conn2 = create_connection(db_path)
    apply_migrations(conn2)
    reloaded_day = DayRepository(conn2).get_by_date("2026-09-21")
    reloaded_tasks = TaskRepository(conn2).list_for_day(reloaded_day.id)
    conn2.close()

    assert reloaded_day is not None
    assert len(reloaded_tasks) == 1
    assert reloaded_tasks[0].text == "مهمة محفوظة"