"""UnitOfWork's own commit/rollback contract, exercised against the
tasks table so this stays decoupled from quote-domain specifics."""
import pytest

from app.database.task_repository import TaskRepository
from app.database.unit_of_work import UnitOfWork


def test_successful_block_commits(db_connection, day_repo):
    day = day_repo.create("2026-09-01")
    uow = UnitOfWork(db_connection)

    with uow:
        db_connection.execute(
            "INSERT INTO tasks (day_id, text, position, created_at, updated_at) "
            "VALUES (?, 'a task', 0, 'now', 'now')",
            (day.id,),
        )

    task_repo = TaskRepository(db_connection)
    assert len(task_repo.list_for_day(day.id)) == 1


def test_failed_block_rolls_back_everything_in_it(db_connection, day_repo):
    day = day_repo.create("2026-09-01")
    uow = UnitOfWork(db_connection)

    with pytest.raises(RuntimeError):
        with uow:
            db_connection.execute(
                "INSERT INTO tasks (day_id, text, position, created_at, updated_at) "
                "VALUES (?, 'first', 0, 'now', 'now')",
                (day.id,),
            )
            db_connection.execute(
                "INSERT INTO tasks (day_id, text, position, created_at, updated_at) "
                "VALUES (?, 'second', 1, 'now', 'now')",
                (day.id,),
            )
            raise RuntimeError("simulated mid-transaction failure")

    task_repo = TaskRepository(db_connection)
    # Neither insert survives — not "first" alone, not "second" alone.
    assert task_repo.list_for_day(day.id) == []


def test_instance_is_reusable_across_multiple_operations(db_connection, day_repo):
    day = day_repo.create("2026-09-01")
    uow = UnitOfWork(db_connection)

    with uow:
        db_connection.execute(
            "INSERT INTO tasks (day_id, text, position, created_at, updated_at) "
            "VALUES (?, 'first', 0, 'now', 'now')",
            (day.id,),
        )

    with uow:
        db_connection.execute(
            "INSERT INTO tasks (day_id, text, position, created_at, updated_at) "
            "VALUES (?, 'second', 1, 'now', 'now')",
            (day.id,),
        )

    task_repo = TaskRepository(db_connection)
    assert {t.text for t in task_repo.list_for_day(day.id)} == {"first", "second"}
