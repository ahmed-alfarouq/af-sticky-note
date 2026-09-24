"""Runtime coordinator for daily rollover and date change detection.

Responsibilities:
- Schedules a single, long-duration QTimer targeting the next local midnight.
- Listens for application resume / window activation to catch date changes
  that occurred while the system was suspended or asleep.
- Re-reads local calendar date using clock utilities.
- When the date advances (single or multi-day skip), coordinates with
  DailyRolloverService to carry forward incomplete tasks across intermediate days.
- Triggers minimal in-place UI refresh on MainWindow (date, quote, tasks)
  without recreating widgets or polling.
- Zero background threads, zero polling loops, zero continuous CPU overhead.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Callable, Optional

try:
    from PySide6.QtCore import QEvent, QObject, QTimer
except ImportError:
    # Graceful fallback when running in non-GUI / headless backend test runners
    class QObject:  # type: ignore
        def __init__(self, parent: Any = None) -> None:
            self._parent = parent

        def eventFilter(self, watched: Any, event: Any) -> bool:
            return False

    class QEvent:  # type: ignore
        class Type:
            ApplicationActivate = 121
            WindowActivate = 24

    class QTimer(QObject):  # type: ignore
        pass

from app.core.models import Day, Task
from app.core.services.daily_rollover_service import DailyRolloverService
from app.core.services.quote_service import NoAvailableQuotesError, QuoteService
from app.core.services.task_service import TaskService
from app.database.day_repository import DayRepository
from app.infrastructure.clock import local_today_iso, ms_until_next_local_midnight

logger = logging.getLogger(__name__)


class DailyLifecycleCoordinator(QObject):
    """Coordinates daily rollover detection and UI refresh for a running application."""

    def __init__(
        self,
        current_date: str,
        rollover_service: DailyRolloverService,
        quote_service: QuoteService,
        day_repo: DayRepository,
        task_service: TaskService,
        main_window: Any,
        date_provider: Optional[Callable[[], str]] = None,
        ms_until_midnight_provider: Optional[Callable[[], int]] = None,
        timer_factory: Optional[Callable[[], Any]] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._current_date = current_date
        self._rollover_service = rollover_service
        self._quote_service = quote_service
        self._day_repo = day_repo
        self._task_service = task_service
        self._main_window = main_window

        self._get_today = date_provider or local_today_iso
        self._get_ms_until_midnight = ms_until_midnight_provider or ms_until_next_local_midnight

        # Exactly ONE single-shot QTimer for next midnight
        if timer_factory is not None:
            self._midnight_timer = timer_factory()
        else:
            self._midnight_timer = QTimer(self)
        self._midnight_timer.setSingleShot(True)
        self._midnight_timer.timeout.connect(self._on_midnight_timeout)

        # Install event filter on main_window to intercept resume / activation events
        self._main_window.installEventFilter(self)

        self._schedule_next_midnight()

    @property
    def current_date(self) -> str:
        return self._current_date

    def _schedule_next_midnight(self) -> None:
        """Schedule or reschedule the single timer to fire at next local midnight."""
        ms = self._get_ms_until_midnight()
        self._midnight_timer.stop()
        self._midnight_timer.start(ms)
        logger.debug("Scheduled next midnight rollover check in %d ms", ms)

    def _on_midnight_timeout(self) -> None:
        """Invoked when the single midnight timer fires."""
        self.check_date_transition()
        self._schedule_next_midnight()

    def eventFilter(self, watched: Any, event: Any) -> bool:
        """Intercept application activation / window focus to check for date transitions
        after system sleep or inactivity."""
        event_type = event.type()
        # Handle both Qt QEvent.Type enum and int value representation
        if event_type in (
            getattr(QEvent.Type, "ApplicationActivate", 121),
            getattr(QEvent.Type, "WindowActivate", 24),
            121,
            24,
        ):
            self.check_date_transition()
        return super().eventFilter(watched, event)

    def check_date_transition(self) -> bool:
        """Validate current date against tracked date. If advanced, perform rollover
        and refresh UI. Returns True if a date transition occurred."""
        today = self._get_today()
        if today <= self._current_date:
            return False

        logger.info("Date transition detected: %s -> %s", self._current_date, today)
        success = self._handle_date_transition(self._current_date, today)
        if success:
            self._current_date = today
            self._schedule_next_midnight()
        return success

    def _handle_date_transition(self, from_date: str, to_date: str) -> bool:
        """Run rollover step-by-step across all intermediate calendar days,
        assign today's quote, and refresh UI."""
        try:
            # Parse dates to handle single or multi-day jumps (e.g. sleep over weekend)
            start_d = date.fromisoformat(from_date)
            end_d = date.fromisoformat(to_date)

            curr = start_d
            while curr < end_d:
                nxt = curr + timedelta(days=1)
                source_str = curr.isoformat()
                target_str = nxt.isoformat()
                self._rollover_service.rollover_tasks(source_str, target_str)
                curr = nxt

            # Resolve today's Day and Quote
            try:
                assignment = self._quote_service.get_or_assign_daily_quote(to_date)
                today_day = assignment.day
                quote_text = assignment.day.quote_text
            except NoAvailableQuotesError:
                today_day = self._day_repo.get_or_create(to_date)
                quote_text = "لا توجد حكمة متاحة لهذا اليوم"

            assert today_day.id is not None, "Today day must have an ID"
            today_tasks = self._task_service.get_today_tasks(today_day.id)

            # In-place UI update (re-uses existing widgets, no recreation)
            self._main_window.refresh_daily_view(today_day, quote_text, today_tasks)
            return True

        except Exception as exc:
            logger.error("Failed to execute daily rollover transition from %s to %s: %s", from_date, to_date, exc)
            return False

    def cleanup(self) -> None:
        """Stop timer and unhook event filter upon shutdown."""
        self._midnight_timer.stop()
        self._main_window.removeEventFilter(self)
