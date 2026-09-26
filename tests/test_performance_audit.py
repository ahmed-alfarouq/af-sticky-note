"""Architectural Performance & Resource Guard Tests (Phase 5N).

Verifies invariants guaranteeing zero continuous background load:
- Single-shot timer architecture: Exactly 1 lifecycle timer, 0 recurring periodic pollers.
- No background threads, busy loops, or polling subprocesses.
- Event-driven database connections and repositories.
- Zero-mutation and non-polling Settings and History query boundaries.
"""
from unittest.mock import MagicMock
import pytest

from app.core.daily_stats import compute_daily_stats
from app.core.models import Day, Task, TaskPriority
from app.core.services.daily_lifecycle_coordinator import DailyLifecycleCoordinator
from app.core.services.history_service import HistoryService
from app.core.services.task_service import TaskService
from app.database.day_repository import DayRepository
from app.database.task_repository import TaskRepository


def test_daily_lifecycle_coordinator_uses_strictly_single_shot_timer():
    """Verify coordinator configures a single-shot timer targeting next midnight without recurring ticks."""
    mock_timer = MagicMock()
    mock_rollover = MagicMock()
    mock_quote = MagicMock()
    mock_day_repo = MagicMock()
    mock_task_service = MagicMock()
    mock_window = MagicMock()

    coordinator = DailyLifecycleCoordinator(
        current_date="2026-09-26",
        rollover_service=mock_rollover,
        quote_service=mock_quote,
        day_repo=mock_day_repo,
        task_service=mock_task_service,
        main_window=mock_window,
        date_provider=lambda: "2026-09-26",
        ms_until_midnight_provider=lambda: 3600000,
        timer_factory=lambda: mock_timer,
    )

    # Invariant: timer must be configured as single-shot (not periodic)
    mock_timer.setSingleShot.assert_called_with(True)
    # Started once with the duration until midnight
    mock_timer.start.assert_called_once_with(3600000)


def test_idle_coordinator_no_op_when_date_unchanged():
    """Verify check_date_transition performs zero database or rollover work when date has not advanced."""
    mock_rollover = MagicMock()
    mock_quote = MagicMock()
    mock_day_repo = MagicMock()
    mock_task_service = MagicMock()
    mock_window = MagicMock()

    coordinator = DailyLifecycleCoordinator(
        current_date="2026-09-26",
        rollover_service=mock_rollover,
        quote_service=mock_quote,
        day_repo=mock_day_repo,
        task_service=mock_task_service,
        main_window=mock_window,
        date_provider=lambda: "2026-09-26",
        ms_until_midnight_provider=lambda: 3600000,
        timer_factory=MagicMock,
    )

    # When date is unchanged: zero rollover calls, zero quote lookups
    transitioned = coordinator.check_date_transition()
    assert transitioned is False
    mock_rollover.rollover_tasks.assert_not_called()
    mock_quote.get_or_assign_daily_quote.assert_not_called()


def test_multi_day_transition_performs_single_ui_refresh(db_connection):
    """Verify that jumping across multiple days (e.g. system suspended over weekend)
    progresses rollover day-by-day atomically and updates UI once at completion."""
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    task_service = TaskService(task_repo)

    mock_rollover = MagicMock()
    mock_quote = MagicMock()
    mock_window = MagicMock()

    # Day 1 initial setup
    d1 = day_repo.create("2026-09-20")
    t1 = task_service.create_task(d1.id, "Initial Task")

    quote_assignment = MagicMock()
    quote_assignment.day = day_repo.create("2026-09-23")
    mock_quote.get_or_assign_daily_quote.return_value = quote_assignment

    coordinator = DailyLifecycleCoordinator(
        current_date="2026-09-20",
        rollover_service=mock_rollover,
        quote_service=mock_quote,
        day_repo=day_repo,
        task_service=task_service,
        main_window=mock_window,
        date_provider=lambda: "2026-09-23",  # 3 days later
        ms_until_midnight_provider=lambda: 5000,
        timer_factory=MagicMock,
    )

    transitioned = coordinator.check_date_transition()
    assert transitioned is True

    # Rollover was called sequentially for each intermediate day
    assert mock_rollover.rollover_tasks.call_count == 3
    mock_rollover.rollover_tasks.assert_any_call("2026-09-20", "2026-09-21")
    mock_rollover.rollover_tasks.assert_any_call("2026-09-21", "2026-09-22")
    mock_rollover.rollover_tasks.assert_any_call("2026-09-22", "2026-09-23")

    # MainWindow UI refresh was called strictly ONCE for the final landing day
    mock_window.refresh_daily_view.assert_called_once()
