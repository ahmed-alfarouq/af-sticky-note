"""Read-only History Window for viewing previous days and tasks (Phase 5J).

RTL Arabic interface displaying:
- Date navigation ([السابق] [التاريخ] [التالي])
- Dual calendar date (Gregorian & Hijri)
- Daily progress summary (X / Y مكتملة • %Z)
- Read-only task list with completed/incomplete indicators
- Graceful empty state when no tasks exist on that day
"""
from __future__ import annotations

import logging
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.models import Task
from app.core.services.history_service import DayHistoryView, HistoryService
from app.infrastructure.clock import format_dual_calendar_date
from app.ui.styles.app_style import get_application_stylesheet

logger = logging.getLogger(__name__)


class HistoryWindow(QDialog):
    """Read-only viewer window for historical days and tasks."""

    def __init__(
        self,
        history_service: HistoryService,
        initial_date: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._history_service = history_service
        self._available_dates: List[str] = self._history_service.get_available_dates()
        self._current_index: int = 0

        # If available dates exist, position on initial_date or newest
        if initial_date in self._available_dates:
            self._current_index = self._available_dates.index(initial_date)
        elif self._available_dates:
            self._current_index = 0

        self._current_date = (
            self._available_dates[self._current_index]
            if self._available_dates
            else initial_date
        )

        self.setWindowTitle("سجل المهام اليومية")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(380, 520)
        self.setMinimumSize(340, 460)

        self._init_ui()
        self.setStyleSheet(get_application_stylesheet())
        self._load_day_view(self._current_date)

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # 1. Header & Navigation Row: [Next (Newer)] [Date Label] [Prev (Older)]
        nav_card = QFrame(self)
        nav_card.setObjectName("quoteCard")
        nav_layout = QHBoxLayout(nav_card)
        nav_layout.setContentsMargins(12, 10, 12, 10)
        nav_layout.setSpacing(10)

        self._btn_prev = QPushButton("◀ السابق", nav_card)
        self._btn_prev.setObjectName("historyNavButton")
        self._btn_prev.setAccessibleName("الانتقال إلى اليوم السابق")
        self._btn_prev.clicked.connect(self._on_prev_day)

        self._date_title_label = QLabel(self._current_date, nav_card)
        self._date_title_label.setObjectName("dateLabel")
        self._date_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_next = QPushButton("التالي ▶", nav_card)
        self._btn_next.setObjectName("historyNavButton")
        self._btn_next.setAccessibleName("الانتقال إلى اليوم التالي")
        self._btn_next.clicked.connect(self._on_next_day)

        nav_layout.addWidget(self._btn_prev)
        nav_layout.addWidget(self._date_title_label, 1)
        nav_layout.addWidget(self._btn_next)

        main_layout.addWidget(nav_card)

        # 2. Dual Calendar Details & Progress Bar / Summary Card
        self._summary_card = QFrame(self)
        self._summary_card.setObjectName("quoteCard")
        summary_layout = QVBoxLayout(self._summary_card)
        summary_layout.setContentsMargins(14, 12, 14, 12)
        summary_layout.setSpacing(6)

        self._dual_date_label = QLabel("", self._summary_card)
        self._dual_date_label.setObjectName("historyDualDate")
        self._dual_date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_layout.addWidget(self._dual_date_label)

        self._stats_label = QLabel("", self._summary_card)
        self._stats_label.setObjectName("historyStatsLabel")
        self._stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_layout.addWidget(self._stats_label)

        main_layout.addWidget(self._summary_card)

        # 3. Read-Only Task List Area
        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("taskListScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._task_container = QWidget(self._scroll)
        self._task_container.setObjectName("taskListContainer")
        self._task_layout = QVBoxLayout(self._task_container)
        self._task_layout.setContentsMargins(0, 4, 0, 4)
        self._task_layout.setSpacing(8)

        self._scroll.setWidget(self._task_container)
        main_layout.addWidget(self._scroll, 1)

        # 4. Close Button
        bottom_row = QHBoxLayout()
        bottom_row.addStretch(1)
        self._close_btn = QPushButton("إغلاق", self)
        self._close_btn.setObjectName("historyCloseButton")
        self._close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(self._close_btn)

        main_layout.addLayout(bottom_row)

    def _load_day_view(self, date_str: str) -> None:
        """Fetch read-only snapshot for the given date and populate widgets."""
        self._current_date = date_str
        history_view: DayHistoryView = self._history_service.get_day_history(date_str)

        # Update Navigation Button States
        self._btn_prev.setEnabled(self._current_index < len(self._available_dates) - 1)
        self._btn_next.setEnabled(self._current_index > 0)

        # Update Date Titles
        self._date_title_label.setText(date_str)
        dual_calendar = format_dual_calendar_date(date_str)
        self._dual_date_label.setText(dual_calendar)

        # Update Stats
        stats = history_view.stats
        if stats.total > 0:
            pct_int = int(round(stats.completion_percentage))
            stats_text = f"التقدم: {stats.completed} من {stats.total} مكتملة  •  {pct_int}%"
        else:
            stats_text = "لا توجد مهام مسجلة"
        self._stats_label.setText(stats_text)

        # Clear existing items in task layout
        while self._task_layout.count() > 0:
            child = self._task_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Populate tasks (strictly read-only)
        if not history_view.tasks:
            empty_label = QLabel("لا توجد مهام في هذا اليوم", self._task_container)
            empty_label.setObjectName("historyEmptyLabel")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #8C96A8; font-size: 14px; padding: 24px;")
            self._task_layout.addWidget(empty_label)
        else:
            for task in history_view.tasks:
                row_frame = self._create_read_only_task_row(task)
                self._task_layout.addWidget(row_frame)

        self._task_layout.addStretch(1)

    def _create_read_only_task_row(self, task: Task) -> QFrame:
        """Create a purely read-only visual representation of a historical task."""
        frame = QFrame(self._task_container)
        frame.setObjectName("taskItemFrame")

        row = QHBoxLayout(frame)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)

        # Status indicator icon/symbol (no clickable checkbox)
        indicator = QLabel(frame)
        if task.is_completed:
            indicator.setText("✔")
            indicator.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
        else:
            indicator.setText("○")
            indicator.setStyleSheet("color: #8C96A8; font-size: 14px;")

        text_label = QLabel(task.text, frame)
        text_label.setWordWrap(True)
        if task.is_completed:
            text_label.setObjectName("taskTextLabelCompleted")
        else:
            text_label.setObjectName("taskTextLabel")

        row.addWidget(indicator)
        row.addWidget(text_label, 1)
        return frame

    def _on_prev_day(self) -> None:
        """Navigate to earlier recorded day."""
        if self._current_index < len(self._available_dates) - 1:
            self._current_index += 1
            self._load_day_view(self._available_dates[self._current_index])

    def _on_next_day(self) -> None:
        """Navigate to later recorded day."""
        if self._current_index > 0:
            self._current_index -= 1
            self._load_day_view(self._available_dates[self._current_index])
