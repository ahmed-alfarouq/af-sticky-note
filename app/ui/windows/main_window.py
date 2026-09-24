"""Main Sticky Note window coordinator (Phase 4B).

Assembles the paper note surface, decorative pin header, daily quote,
scrollable task list, and task input. Features full accessibility
descriptions, RTL alignment, and keyboard navigation.
"""
from __future__ import annotations

import logging
from typing import Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import APP_NAME
from app.core.models import Day, Task
from app.core.services.task_service import TaskService
from app.ui.styles.app_style import get_application_stylesheet
from app.ui.widgets.quote_widget import QuoteWidget
from app.ui.widgets.task_input import TaskInput
from app.ui.widgets.task_list import TaskList

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Sticky Note main window coordinating the daily quote and tasks."""

    def __init__(
        self,
        day: Day,
        quote_text: Optional[str],
        task_service: TaskService,
        initial_tasks: Sequence[Task] = (),
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._day = day
        self._task_service = task_service

        # Configure desktop widget window flags:
        # - Qt.FramelessWindowHint: remove OS title bar and borders for sticky note look
        # Note: Do not use Qt.SubWindow or Qt.Tool which alter top-level DWM compositing
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
        )
        # Translucent background allows rounded CSS paper corners without artifacts
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.setWindowTitle(APP_NAME)
        self.resize(380, 560)
        self.setMinimumSize(320, 420)
        self.setAccessibleName("نافذة الملاحظة اليومية دايلي ستيكي")

        self._central_widget = QWidget(self)
        self._central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self._central_widget)

        self._init_layout(day.date, quote_text, initial_tasks)
        self.setStyleSheet(get_application_stylesheet())

    def _init_layout(
        self,
        date_str: str,
        quote_text: Optional[str],
        initial_tasks: Sequence[Task],
    ) -> None:
        # Outer board layout
        outer_layout = QVBoxLayout(self._central_widget)
        outer_layout.setContentsMargins(14, 14, 14, 14)
        outer_layout.setSpacing(0)

        # Sticky Note paper surface
        self._paper_frame = QFrame(self._central_widget)
        self._paper_frame.setObjectName("stickyNoteFrame")
        self._paper_frame.setAccessibleName("لوحة الملاحظة الورقية")
        outer_layout.addWidget(self._paper_frame)

        paper_layout = QVBoxLayout(self._paper_frame)
        paper_layout.setContentsMargins(16, 12, 16, 16)
        paper_layout.setSpacing(12)

        # 1. Decorative Pin Header
        pin_row = QHBoxLayout()
        pin_row.setContentsMargins(0, 0, 0, 4)
        pin_row.addStretch(1)

        self._pin_widget = QLabel(self._paper_frame)
        self._pin_widget.setObjectName("pinWidget")
        self._pin_widget.setAccessibleName("دبوس تثبيت الملاحظة")
        pin_row.addWidget(self._pin_widget)
        pin_row.addStretch(1)

        paper_layout.addLayout(pin_row)

        # 2. Daily Quote & Date Card
        self._quote_widget = QuoteWidget(date_text=date_str, quote_text=quote_text, parent=self._paper_frame)
        paper_layout.addWidget(self._quote_widget)

        # 3. Scrollable Task List
        self._task_list = TaskList(parent=self._paper_frame)
        self._task_list.task_completed_toggled.connect(self._on_task_completed_toggled)
        self._task_list.set_tasks(initial_tasks)
        paper_layout.addWidget(self._task_list, 1)

        # 4. Task Input
        self._task_input = TaskInput(parent=self._paper_frame)
        self._task_input.task_submitted.connect(self._on_task_submitted)
        paper_layout.addWidget(self._task_input)

    def refresh_daily_view(
        self,
        day: Day,
        quote_text: Optional[str],
        tasks: Sequence[Task],
    ) -> None:
        """Update the displayed date, quote, and task list without recreating widgets."""
        self._day = day
        self._quote_widget.set_date_and_quote(day.date, quote_text)
        self._task_list.set_tasks(tasks)

    def _on_task_submitted(self, raw_text: str) -> None:
        """Handle task submission from TaskInput.

        Crucial rule: TaskInput is only cleared AFTER task creation succeeds.
        If validation or persistence fails, raw text remains untouched.
        """
        if self._day.id is None:
            logger.error("Cannot create task: day.id is None")
            return

        try:
            created_task = self._task_service.create_task(self._day.id, raw_text)
            if created_task is not None:
                self._task_list.add_task(created_task)
                self._task_input.clear()
            # Retain focus in input field whether text was created or empty
            self._task_input.setFocus()
        except Exception as exc:
            logger.error("Failed to create task %r: %s", raw_text, exc)
            # Input text is intentionally retained on error

    def _on_task_completed_toggled(self, task_id: int, is_completed: bool) -> None:
        """Handle checkbox toggle from TaskList / TaskItem."""
        try:
            self._task_service.toggle_task_completion(task_id, is_completed)
        except Exception as exc:
            logger.error("Failed to toggle completion for task %d: %s", task_id, exc)
