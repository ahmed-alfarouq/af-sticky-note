"""Integration test for application bootstrap and composition flow.

Simulates the bootstrap sequence on a temporary database without starting Qt:
- DB path creation
- Migrations
- Repository and service instantiations
- Additive quote import
- Today resolution and quote assignment
- TaskService creation, persistence, and restart restoration
"""
from pathlib import Path

import pytest

from app.core.services.quote_import_service import QuoteImportService
from app.core.services.quote_service import QuoteService
from app.core.services.task_service import TaskService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.quote_repository import QuoteRepository
from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
from app.database.quote_usage_repository import QuoteUsageRepository
from app.database.task_repository import TaskRepository
from app.infrastructure.paths import get_quotes_path


def test_bootstrap_composition_end_to_end(tmp_path: Path):
    db_file = tmp_path / "test_bootstrap.db"

    # --- SESSION 1: Fresh startup ---
    conn1 = create_connection(db_file)
    apply_migrations(conn1)

    day_repo1 = DayRepository(conn1)
    task_repo1 = TaskRepository(conn1)
    quote_repo1 = QuoteRepository(conn1)
    quote_usage_repo1 = QuoteUsageRepository(conn1)
    rotation_repo1 = QuoteRotationStateRepository(conn1)

    task_service1 = TaskService(task_repo1)
    quote_import_service1 = QuoteImportService(quote_repo1)
    quote_service1 = QuoteService(
        conn=conn1,
        quote_repo=quote_repo1,
        day_repo=day_repo1,
        quote_usage_repo=quote_usage_repo1,
        rotation_state_repo=rotation_repo1,
    )

    # 1. Quote import from data/quotes.txt
    quotes_path = get_quotes_path()
    import_result = quote_import_service1.import_quotes(quotes_path)
    assert import_result.imported_count > 0

    # 2. Assign today's quote and get day
    today_str = "2026-09-22"
    assignment = quote_service1.get_or_assign_daily_quote(today_str)
    assert assignment.day.quote_text is not None
    day_id = assignment.day.id

    # 3. Create tasks via TaskService
    t1 = task_service1.create_task(day_id, "مهمة أولى")
    t2 = task_service1.create_task(day_id, "مهمة ثانية")
    assert t1 is not None and t2 is not None

    # 4. Complete first task
    task_service1.toggle_task_completion(t1.id, True)

    conn1.close()

    # --- SESSION 2: Restart simulation ---
    conn2 = create_connection(db_file)
    apply_migrations(conn2)  # must be idempotent

    day_repo2 = DayRepository(conn2)
    task_repo2 = TaskRepository(conn2)
    quote_repo2 = QuoteRepository(conn2)
    quote_usage_repo2 = QuoteUsageRepository(conn2)
    rotation_repo2 = QuoteRotationStateRepository(conn2)

    task_service2 = TaskService(task_repo2)
    quote_import_service2 = QuoteImportService(quote_repo2)
    quote_service2 = QuoteService(
        conn=conn2,
        quote_repo=quote_repo2,
        day_repo=day_repo2,
        quote_usage_repo=quote_usage_repo2,
        rotation_state_repo=rotation_repo2,
    )

    # Quote import should skip existing quotes
    reimport_result = quote_import_service2.import_quotes(quotes_path)
    assert reimport_result.imported_count == 0

    # Same day should return exact same quote
    reassignment = quote_service2.get_or_assign_daily_quote(today_str)
    assert reassignment.day.quote_text == assignment.day.quote_text
    assert reassignment.was_newly_assigned is False

    # Tasks and completion status must be restored
    restored_tasks = task_service2.get_today_tasks(day_id)
    assert len(restored_tasks) == 2
    assert restored_tasks[0].id == t1.id
    assert restored_tasks[0].text == "مهمة أولى"
    assert restored_tasks[0].is_completed is True
    assert restored_tasks[1].id == t2.id
    assert restored_tasks[1].text == "مهمة ثانية"
    assert restored_tasks[1].is_completed is False

    conn2.close()
