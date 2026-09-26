"""Main Sticky Note window coordinator (Phase 4B).

Assembles the paper note surface, decorative pin header, daily quote,
scrollable task list, and task input. Features full accessibility
descriptions, RTL alignment, and keyboard navigation.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional, Sequence

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import APP_NAME
from app.core.models import Day, Task
from app.core.services.task_service import TaskService
from app.ui.geometry_manager import WindowGeometryManager
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
        geometry_manager: Optional[WindowGeometryManager] = None,
        history_service: Optional[object] = None,
        startup_manager: Optional[object] = None,
        on_exit_requested: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._day = day
        self._task_service = task_service
        self._geometry_manager = geometry_manager or WindowGeometryManager()
        self._history_service = history_service
        self._startup_manager = startup_manager
        self._on_exit_requested = on_exit_requested
        self._settings_window: Optional[QWidget] = None

        # Dragging state
        self._is_dragging: bool = False
        self._drag_start_pos: QPoint = QPoint()

        # Resizing edge state (frameless window resize handling)
        self._is_resizing: bool = False
        self._resize_edges: int = 0
        self._resize_start_geometry = None
        self._resize_start_mouse = None
        self.setMouseTracking(True)

        # Configure desktop widget window flags:
        # - Qt.FramelessWindowHint: remove OS title bar and borders for sticky note look
        # - Qt.Tool: classifies the window as a tool/utility window before native realization,
        #   preventing taskbar button creation and Win+D shell minimize-all broadcasts
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        )
        # Translucent background allows rounded CSS paper corners without artifacts
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(320, 420)
        self.setAccessibleName("نافذة الملاحظة اليومية دايلي ستيكي")

        self._central_widget = QWidget(self)
        self._central_widget.setObjectName("centralWidget")
        self._central_widget.setMouseTracking(True)
        self.setCentralWidget(self._central_widget)

        # Flag to indicate whether window closing should hide to tray or do real shutdown
        self._allow_window_close: bool = False

        self._init_layout(day.date, quote_text, initial_tasks)
        self.setStyleSheet(get_application_stylesheet())

        # Restore persisted geometry if valid, else default
        gx, gy, gw, gh = self._geometry_manager.get_validated_geometry()
        self.setGeometry(gx, gy, gw, gh)

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

        # 1. Decorative Pin Header (Designated Drag Area) with Top-Left Control Icons
        self._header_frame = QFrame(self._paper_frame)
        self._header_frame.setObjectName("headerFrame")
        self._header_frame.setCursor(Qt.CursorShape.ArrowCursor)
        # Set layout direction on the QFrame widget (QWidget API), NOT on the QLayout
        self._header_frame.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        pin_row = QHBoxLayout(self._header_frame)
        pin_row.setContentsMargins(0, 0, 0, 4)
        pin_row.setSpacing(4)

        # Top-Left Action Buttons (Physically on the left: Settings | History | Exit)
        # 1. Settings button
        self._settings_btn = QPushButton("⚙", self._header_frame)
        self._settings_btn.setObjectName("headerIconButton")
        self._settings_btn.setAccessibleName("فتح الإعدادات")
        self._settings_btn.setToolTip("الإعدادات")
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.clicked.connect(self._on_settings_requested)
        pin_row.addWidget(self._settings_btn)

        # 2. History button
        self._history_btn = QPushButton("⏱", self._header_frame)
        self._history_btn.setObjectName("headerIconButton")
        self._history_btn.setAccessibleName("فتح السجل اليومي")
        self._history_btn.setToolTip("السجل")
        self._history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._history_btn.clicked.connect(self._on_history_requested)
        pin_row.addWidget(self._history_btn)

        # 3. Exit Button
        self._exit_btn = QPushButton("✕", self._header_frame)
        self._exit_btn.setObjectName("exitButton")
        self._exit_btn.setAccessibleName("إغلاق التطبيق نهائياً")
        self._exit_btn.setToolTip("إغلاق التطبيق نهائياً")
        self._exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._exit_btn.clicked.connect(self._on_exit_clicked)
        pin_row.addWidget(self._exit_btn)

        # Left stretch to keep pin centered
        pin_row.addStretch(1)

        # Decorative Pin Widget in Center
        self._pin_widget = QLabel(self._header_frame)
        self._pin_widget.setObjectName("pinWidget")
        self._pin_widget.setAccessibleName("دبوس تثبيت الملاحظة")
        pin_row.addWidget(self._pin_widget)

        # Right stretch to balance the row
        pin_row.addStretch(1)

        # Symmetrical spacer matching controls group width (22*3 + 4*2 = 74px) so the pin remains perfectly centered
        pin_row.addSpacing(74)

        paper_layout.addWidget(self._header_frame)

        # 2. Daily Quote & Date Card
        self._quote_widget = QuoteWidget(date_text=date_str, quote_text=quote_text, parent=self._paper_frame)
        paper_layout.addWidget(self._quote_widget)

        # 3. Scrollable Task List
        self._task_list = TaskList(parent=self._paper_frame)
        self._task_list.task_completed_toggled.connect(self._on_task_completed_toggled)
        self._task_list.task_edit_requested.connect(self._on_task_edit_requested)
        self._task_list.task_delete_requested.connect(self._on_task_delete_requested)
        self._task_list.clear_completed_requested.connect(self._on_clear_completed_requested)
        self._task_list.history_requested.connect(self._on_history_requested)
        self._task_list.settings_requested.connect(self._on_settings_requested)
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

    def _on_task_edit_requested(self, task_id: int) -> None:
        """Open edit dialog and persist updated task text."""
        try:
            # Find current text from UI item or task service
            task_item = self._task_list._items.get(task_id)
            current_text = task_item._text_label.text() if task_item else ""

            from app.ui.widgets.task_edit_dialog import TaskEditDialog
            dialog = TaskEditDialog(initial_text=current_text, parent=self)
            if dialog.exec():
                new_text = dialog.get_text()
                if new_text and new_text != current_text:
                    if self._task_service.update_task_text(task_id, new_text):
                        self._task_list.update_task_text(task_id, new_text)
        except Exception as exc:
            logger.error("Failed to edit task %d: %s", task_id, exc)

    def _on_task_delete_requested(self, task_id: int) -> None:
        """Handle deletion of a specific task."""
        try:
            self._task_service.delete_task(task_id)
            self._task_list.remove_task(task_id)
        except Exception as exc:
            logger.error("Failed to delete task %d: %s", task_id, exc)

    def _on_clear_completed_requested(self) -> None:
        """Clear all completed tasks for today's active day."""
        if self._day.id is None:
            return
        try:
            self._task_service.clear_completed_tasks(self._day.id)
            # Refresh list with remaining tasks
            remaining_tasks = self._task_service.get_today_tasks(self._day.id)
            self._task_list.set_tasks(remaining_tasks)
        except Exception as exc:
            logger.error("Failed to clear completed tasks for day %d: %s", self._day.id, exc)

    def _on_history_requested(self) -> None:
        """Open the read-only History viewer window."""
        if self._history_service is None:
            logger.warning("HistoryService not configured on MainWindow")
            return
        try:
            from app.ui.windows.history_window import HistoryWindow
            history_win = HistoryWindow(
                history_service=self._history_service,
                initial_date=self._day.date,
                parent=self,
            )
            history_win.exec()
        except Exception as exc:
            logger.error("Failed to open History window: %s", exc)

    def _on_settings_requested(self) -> None:
        """Open the Settings dialog, reusing or activating an existing instance."""
        if self._startup_manager is None:
            logger.warning("StartupManager not configured on MainWindow")
            return
        try:
            from app.ui.windows.settings_window import SettingsWindow
            settings_dialog = SettingsWindow(
                startup_manager=self._startup_manager,
                parent=self,
            )
            settings_dialog.exec()
        except Exception as exc:
            logger.error("Failed to open Settings window: %s", exc)

    def _on_exit_clicked(self) -> None:
        """Handle top-left exit control click.

        Triggers canonical application shutdown through the registered exit path.
        """
        logger.info("Top-left Exit button clicked; initiating application shutdown.")
        self._allow_window_close = True
        if self._on_exit_requested is not None:
            self._on_exit_requested()
        else:
            # Fallback to direct window close / app quit
            self.close()

    # -------------------------------------------------------------------------
    # Dragging & Resizing Event Handlers (Phase 5G-A)
    # -------------------------------------------------------------------------

    RESIZE_BORDER_WIDTH = 8

    def _determine_resize_edges(self, global_pos: QPoint) -> int:
        """Calculate active resize edge bitmask for a given screen point."""
        rect = self.geometry()
        x, y = global_pos.x(), global_pos.y()
        edges = 0

        # Left / Right
        if abs(x - rect.left()) <= self.RESIZE_BORDER_WIDTH:
            edges |= 1  # Left
        elif abs(x - rect.right()) <= self.RESIZE_BORDER_WIDTH:
            edges |= 2  # Right

        # Top / Bottom
        if abs(y - rect.top()) <= self.RESIZE_BORDER_WIDTH:
            edges |= 4  # Top
        elif abs(y - rect.bottom()) <= self.RESIZE_BORDER_WIDTH:
            edges |= 8  # Bottom

        return edges

    def _update_cursor_for_edges(self, edges: int) -> None:
        """Update mouse cursor shape based on detected resize border."""
        if (edges & 1 and edges & 4) or (edges & 2 and edges & 8):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif (edges & 2 and edges & 4) or (edges & 1 and edges & 8):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif edges & 1 or edges & 2:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edges & 4 or edges & 8:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for dragging (header area) or resizing (window edges)."""
        if event.button() == Qt.MouseButton.LeftButton:
            global_pos = event.globalPosition().toPoint()
            edges = self._determine_resize_edges(global_pos)

            if edges != 0:
                # Start window resize
                self._is_resizing = True
                self._resize_edges = edges
                self._resize_start_geometry = self.geometry()
                self._resize_start_mouse = global_pos
                event.accept()
                return

            # Check if clicked inside header drag area (excluding child action buttons)
            if hasattr(self, "_header_frame"):
                header_rect = self._header_frame.rect()
                local_pos = self._header_frame.mapFromGlobal(global_pos)
                if header_rect.contains(local_pos):
                    # If clicked specifically on any header control buttons, let the button handle click
                    for btn_attr in ("_settings_btn", "_history_btn", "_exit_btn"):
                        btn = getattr(self, btn_attr, None)
                        if btn is not None and btn.geometry().contains(local_pos):
                            super().mousePressEvent(event)
                            return
                    self._is_dragging = True
                    self._drag_start_pos = global_pos - self.frameGeometry().topLeft()
                    event.accept()
                    return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse movement for active dragging or resizing."""
        global_pos = event.globalPosition().toPoint()

        if self._is_resizing and self._resize_start_geometry and self._resize_start_mouse:
            dx = global_pos.x() - self._resize_start_mouse.x()
            dy = global_pos.y() - self._resize_start_mouse.y()
            orig = self._resize_start_geometry

            new_x, new_y = orig.x(), orig.y()
            new_w, new_h = orig.width(), orig.height()

            edges = self._resize_edges
            # Right edge
            if edges & 2:
                new_w = max(self.minimumWidth(), orig.width() + dx)
            # Left edge
            elif edges & 1:
                potential_w = orig.width() - dx
                if potential_w >= self.minimumWidth():
                    new_x = orig.x() + dx
                    new_w = potential_w
            # Bottom edge
            if edges & 8:
                new_h = max(self.minimumHeight(), orig.height() + dy)
            # Top edge
            elif edges & 4:
                potential_h = orig.height() - dy
                if potential_h >= self.minimumHeight():
                    new_y = orig.y() + dy
                    new_h = potential_h

            self.setGeometry(new_x, new_y, new_w, new_h)
            event.accept()
            return

        if self._is_dragging:
            self.move(global_pos - self._drag_start_pos)
            event.accept()
            return

        # Update cursor shape when hovering near edges
        edges = self._determine_resize_edges(global_pos)
        self._update_cursor_for_edges(edges)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release to finalize drag or resize and persist geometry."""
        if event.button() == Qt.MouseButton.LeftButton:
            should_save = False

            if self._is_resizing:
                self._is_resizing = False
                self._resize_edges = 0
                self._resize_start_geometry = None
                self._resize_start_mouse = None
                self._update_cursor_for_edges(0)
                should_save = True

            if self._is_dragging:
                self._is_dragging = False
                should_save = True

            if should_save:
                # Save geometry on release boundary (zero polling, zero continuous writes)
                rect = self.geometry()
                self._geometry_manager.save_geometry(rect.x(), rect.y(), rect.width(), rect.height())

        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:
        """Handle window close request.

        If application exit has not been explicitly triggered (e.g. user clicked window close
        or OS sent close), hide the window to tray instead of quitting the application.
        When _allow_window_close is True (tray Exit requested), allow the window to close.
        """
        if not self._allow_window_close:
            event.ignore()
            self.hide()
            logger.debug("Window close ignored; hidden to system tray.")
        else:
            event.accept()
