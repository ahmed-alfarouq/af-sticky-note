"""The archive screen: past days, one at a time, read-only.

Opens on the newest past day that holds tasks. "السابق"/"التالي" step between
the days that can be opened, and "اختيار يوم" switches to a month calendar
where only those days are active. Everything is read from the history service;
nothing here can change a record.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from app.core.models import Category
from app.core.services.history_service import HistoryService
from app.infrastructure.clock import date_display
from app.ui.archive_calendar import ArchiveDates
from app.ui.category_icons import CategoryIconProvider
from app.ui.date_presentation import ArchiveDateText, archive_date_text
from app.ui.user_preferences import UserPreferences
from app.ui.widgets.archive.archive_chip import ArchiveChip
from app.ui.widgets.archive.date_picker import DatePicker
from app.ui.widgets.archive.day_view import DayView
from app.ui.widgets.screens import ScreenPanel

__all__ = ["ArchivePanel"]

logger = logging.getLogger(__name__)

EMPTY_TITLE = "لا يوجد أرشيف بعد"
EMPTY_BODY = "تظهر هنا الأيام السابقة التي أضفت إليها مهام."


class _EmptyArchive(QWidget):
    """Shown when no past day holds a task."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        title = QLabel(EMPTY_TITLE, self)
        title.setObjectName("emptyStateTitle")
        body = QLabel(EMPTY_BODY, self)
        body.setObjectName("emptyStateBody")
        for label in (title, body):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addStretch(1)


class ArchivePanel(ScreenPanel):
    """Archive screen covering ``host``; swaps with the ``home`` page."""

    def __init__(
        self,
        host: QWidget,
        home: QWidget,
        history_service: HistoryService,
        categories: Sequence[Category],
        icon_provider: CategoryIconProvider,
        preferences: UserPreferences,
        today: Callable[[], str],
    ) -> None:
        chip = ArchiveChip("اختيار يوم", "calendar")
        super().__init__(host, home, "الأرشيف", nav_trailing=chip)

        self._chip = chip
        self._history = history_service
        self._preferences = preferences
        self._today = today
        self._dates = ArchiveDates([])
        self._current: Optional[str] = None

        self._day_view = DayView(categories, icon_provider, self)
        self._picker = DatePicker(self)
        self._empty = _EmptyArchive(self)

        self._stack = QStackedWidget(self)
        for page in (self._day_view, self._picker, self._empty):
            self._stack.addWidget(page)
        self.set_body(self._stack)

        chip.toggled.connect(self._on_chip_toggled)
        self._day_view.previous_requested.connect(lambda: self._step(older=True))
        self._day_view.next_requested.connect(lambda: self._step(older=False))
        self._picker.day_chosen.connect(self._open_picked_day)

    # -- Opening ---------------------------------------------------------------

    def _prepare_open(self) -> None:
        """Reload the openable days and show the day last viewed (else the newest)."""
        self._set_chip(False)
        try:
            self._dates = ArchiveDates(self._history.get_archive_dates(self._today()))
            if self._dates:
                if self._current is None or not self._dates.contains(self._current):
                    self._current = self._dates.newest()
                if self._current is not None:
                    self._chip.setEnabled(True)
                    self._show_day(self._current)
                    return
        except Exception as exc:
            logger.error("Failed to load the archive: %s", exc)

        self._current = None
        self._chip.setEnabled(False)
        self._stack.setCurrentWidget(self._empty)

    # -- Showing a day -------------------------------------------------------------

    def _show_day(self, iso: str) -> None:
        self._current = iso
        view = self._history.get_day_history(iso)

        display = date_display(iso)
        texts = (
            archive_date_text(display, self._preferences.calendar)
            if display is not None
            else ArchiveDateText(primary=iso, secondary="")
        )
        self._day_view.show_day(
            view,
            texts,
            has_older=self._dates.older(iso) is not None,
            has_newer=self._dates.newer(iso) is not None,
        )
        self._stack.setCurrentWidget(self._day_view)

    def _step(self, *, older: bool) -> None:
        if self._current is None:
            return
        target = self._dates.older(self._current) if older else self._dates.newer(self._current)
        if target is not None:
            self._show_day(target)

    # -- The date picker ---------------------------------------------------------------

    def _on_chip_toggled(self, checked: bool) -> None:
        if checked:
            self._picker.open_month(
                self._current, self._dates, self._today(), self._preferences.week_start
            )
            self._stack.setCurrentWidget(self._picker)
        elif self._current is not None:
            self._stack.setCurrentWidget(self._day_view)

    def _open_picked_day(self, iso: str) -> None:
        self._set_chip(False)
        self._show_day(iso)

    def _set_chip(self, on: bool) -> None:
        """Set the chip without triggering the page change."""
        was_blocked = self._chip.blockSignals(True)
        self._chip.setChecked(on)
        self._chip.blockSignals(was_blocked)