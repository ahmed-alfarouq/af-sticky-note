"""Tests for Phase 5D: Daily Rollover Runtime Integration and DailyLifecycleCoordinator."""
import sqlite3
import pytest

from app.core.models import Day, Task, TaskPriority
from app.core.services.daily_lifecycle_coordinator import DailyLifecycleCoordinator
from app.core.services.daily_rollover_service import DailyRolloverService
from app.core.services.quote_service import QuoteService
from app.core.services.task_service import TaskService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.quote_repository import QuoteRepository
from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
from app.database.quote_usage_repository import QuoteUsageRepository
from app.database.task_repository import TaskRepository


class MockMainWindow:
    """Mock for MainWindow to test DailyLifecycleCoordinator without PySide6 GUI runtime."""
    def __init__(self, initial_day, initial_quote, initial_tasks):
        self.day = initial_day
        self.quote_text = initial_quote
        self.tasks = list(initial_tasks)
        self.refresh_called_with = None
        self._event_filters = []

    def installEventFilter(self, filter_obj):
        self._event_filters.append(filter_obj)

    def removeEventFilter(self, filter_obj):
        if filter_obj in self._event_filters:
            self._event_filters.remove(filter_obj)

    def refresh_daily_view(self, day, quote_text, tasks):
        self.day = day
        self.quote_text = quote_text
        self.tasks = list(tasks)
        self.refresh_called_with = (day, quote_text, tasks)


class MockEvent:
    def __init__(self, event_type):
        self._type = event_type

    def type(self):
        return self._type


class MockTimer:
    def __init__(self, record_list):
        self.record_list = record_list
        self._interval = 0
        self._active = False
        self._single_shot = False
        self.timeout = MockSignal()

    def setSingleShot(self, val):
        self._single_shot = val

    def stop(self):
        self._active = False

    def start(self, ms):
        self._interval = ms
        self._active = True
        self.record_list.append(ms)

    def isActive(self):
        return self._active

    def interval(self):
        return self._interval


class MockSignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, cb):
        self._callbacks.append(cb)

    def emit(self):
        for cb in self._callbacks:
            cb()


def _build_test_context(db_connection, day_repo, task_repo, quote_repo, quote_usage_repo, rotation_state_repo):
    task_service = TaskService(task_repo)
    quote_service = QuoteService(
        conn=db_connection,
        quote_repo=quote_repo,
        day_repo=day_repo,
        quote_usage_repo=quote_usage_repo,
        rotation_state_repo=rotation_state_repo,
    )
    rollover_service = DailyRolloverService(conn=db_connection, day_repo=day_repo, task_repo=task_repo)

    # Insert sample quotes
    quote_repo.create("حكمة اليوم الأولى")
    quote_repo.create("حكمة اليوم الثانية")

    initial_day = day_repo.get_or_create("2026-09-24")
    t1 = task_service.create_task(initial_day.id, "مهمة غير مكتملة", priority=TaskPriority.HIGH)
    t2 = task_service.create_task(initial_day.id, "مهمة مكتملة", priority=TaskPriority.LOW)
    task_service.toggle_task_completion(t2.id, True)

    window = MockMainWindow(
        initial_day=initial_day,
        initial_quote="حكمة اليوم الأولى",
        initial_tasks=task_service.get_today_tasks(initial_day.id),
    )

    return {
        "conn": db_connection,
        "day_repo": day_repo,
        "task_service": task_service,
        "quote_service": quote_service,
        "rollover_service": rollover_service,
        "window": window,
        "initial_day": initial_day,
        "incomplete_task": t1,
        "completed_task": t2,
    }


def test_timer_scheduled_and_no_rollover_if_same_date(
    db_connection, day_repo, task_repo, quote_repo, quote_usage_repo, rotation_state_repo
):
    """Verify coordinator schedules timer and does not trigger rollover if date has not changed."""
    ctx = _build_test_context(db_connection, day_repo, task_repo, quote_repo, quote_usage_repo, rotation_state_repo)
    current_date = "2026-09-24"
    fake_now = lambda: "2026-09-24"
    scheduled_ms = []

    coord = DailyLifecycleCoordinator(
        current_date=current_date,
        rollover_service=ctx["rollover_service"],
        quote_service=ctx["quote_service"],
        day_repo=ctx["day_repo"],
        task_service=ctx["task_service"],
        main_window=ctx["window"],
        date_provider=fake_now,
        ms_until_midnight_provider=lambda: 3600000,
        timer_factory=lambda: MockTimer(scheduled_ms),
    )

    assert len(scheduled_ms) == 1
    assert scheduled_ms[0] == 3600000

    transitioned = coord.check_date_transition()
    assert not transitioned
    assert coord.current_date == "2026-09-24"
    coord.cleanup()


def test_midnight_timeout_triggers_rollover_and_ui_refresh(
    db_connection, day_repo, task_repo, quote_repo, quote_usage_repo, rotation_state_repo
):
    """Verify that when date advances, check_date_transition rolls over tasks and updates UI in-place."""
    ctx = _build_test_context(db_connection, day_repo, task_repo, quote_repo, quote_usage_repo, rotation_state_repo)
    current_date = "2026-09-24"
    today_state = ["2026-09-24"]
    fake_now = lambda: today_state[0]
    scheduled_ms = []

    coord = DailyLifecycleCoordinator(
        current_date=current_date,
        rollover_service=ctx["rollover_service"],
        quote_service=ctx["quote_service"],
        day_repo=ctx["day_repo"],
        task_service=ctx["task_service"],
        main_window=ctx["window"],
        date_provider=fake_now,
        ms_until_midnight_provider=lambda: 1000,
        timer_factory=lambda: MockTimer(scheduled_ms),
    )

    # Date advances to next day
    today_state[0] = "2026-09-25"
    transitioned = coord.check_date_transition()

    assert transitioned
    assert coord.current_date == "2026-09-25"

    # Verify UI updated
    window = ctx["window"]
    assert window.day.date == "2026-09-25"
    assert len(window.tasks) == 1
    assert window.tasks[0].text == "مهمة غير مكتملة"
    assert window.tasks[0].source_task_id == ctx["incomplete_task"].id
    assert window.tasks[0].priority == TaskPriority.HIGH

    # Verify timer was rescheduled for next midnight
    assert len(scheduled_ms) == 2

    coord.cleanup()


def test_activation_event_triggers_date_transition_after_sleep(
    db_connection, day_repo, task_repo, quote_repo, quote_usage_repo, rotation_state_repo
):
    """Verify that window activation event checks date and performs rollover if system was asleep."""
    ctx = _build_test_context(db_connection, day_repo, task_repo, quote_repo, quote_usage_repo, rotation_state_repo)
    today_state = ["2026-09-25"]
    fake_now = lambda: today_state[0]

    coord = DailyLifecycleCoordinator(
        current_date="2026-09-25",
        rollover_service=ctx["rollover_service"],
        quote_service=ctx["quote_service"],
        day_repo=ctx["day_repo"],
        task_service=ctx["task_service"],
        main_window=ctx["window"],
        date_provider=fake_now,
        ms_until_midnight_provider=lambda: 5000,
        timer_factory=lambda: MockTimer([]),
    )

    # Date advances two days while sleeping
    today_state[0] = "2026-09-27"

    # Simulate WindowActivate / ApplicationActivate event
    event = MockEvent(24)
    coord.eventFilter(ctx["window"], event)

    assert coord.current_date == "2026-09-27"
    assert ctx["window"].day.date == "2026-09-27"
    coord.cleanup()


def test_multi_day_skip_rollover(
    db_connection, day_repo, task_repo, quote_repo, quote_usage_repo, rotation_state_repo
):
    """Verify that skipping multiple days rolls over through intermediate days correctly."""
    ctx = _build_test_context(db_connection, day_repo, task_repo, quote_repo, quote_usage_repo, rotation_state_repo)
    # The initial task was created on 2026-09-24 in ctx
    today_state = ["2026-09-24"]
    fake_now = lambda: today_state[0]

    coord = DailyLifecycleCoordinator(
        current_date="2026-09-24",
        rollover_service=ctx["rollover_service"],
        quote_service=ctx["quote_service"],
        day_repo=ctx["day_repo"],
        task_service=ctx["task_service"],
        main_window=ctx["window"],
        date_provider=fake_now,
        timer_factory=lambda: MockTimer([]),
    )

    today_state[0] = "2026-09-27"  # 3 days forward
    transitioned = coord.check_date_transition()

    assert transitioned
    assert coord.current_date == "2026-09-27"
    window = ctx["window"]
    assert window.day.date == "2026-09-27"

    # Tasks on 2026-09-27 should contain the rolled-over task
    tasks_27 = ctx["task_service"].get_today_tasks(window.day.id)
    assert len(tasks_27) == 1
    assert tasks_27[0].text == "مهمة غير مكتملة"
    coord.cleanup()
