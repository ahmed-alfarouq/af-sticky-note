"""Main Sticky Note window coordinator.

Assembles the paper note surface, decorative pin header, date header, daily
progress ring, daily quote, scrollable task list, and task input.

Paper silhouette
----------------
The note has an organic paper silhouette (rounded top corners, straight
sides, subtly irregular bottom edge) owned by :mod:`app.ui.note_shape`. The
same :class:`NoteShape`, always derived from the *current* paper size, is
used in three places:

  1. ``PaperSurface`` paints the paper and its border along the path,
  2. the path becomes the window mask, so the physical OS window (and its
     clickable region) follows the paper, and
  3. the border is stroked on an inset copy of the path so the mask never
     clips it.

The shape and mask are rebuilt **only** when the size changes
(:meth:`MainWindow._update_note_shape`, driven by ``resizeEvent`` /
``showEvent`` and initial setup), never from ``paintEvent``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import IntFlag
from typing import Any, Callable, Optional, Protocol, Sequence

from PySide6.QtCore import QPoint, QRect, QSettings, QUrl, Qt
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
    QContextMenuEvent,
    QDesktopServices,
    QIcon,
    QKeySequence,
    QMouseEvent,
    QShortcut,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import APP_NAME
from app.core.daily_stats import compute_daily_stats
from app.core.models import DEFAULT_CATEGORY_ID, Category, Day, Task, TaskPriority
from app.core.services.category_service import CategoryService
from app.core.services.history_service import HistoryService
from app.core.services.report_service import ReportService
from app.core.services.task_service import TaskService
from app.infrastructure.paths import get_app_data_dir, get_logo_path
from app.platform.interfaces import DesktopWindowController
from app.ui import theme
from app.ui.category_icons import CategoryIconProvider
from app.ui.geometry_manager import WindowGeometryManager
from app.ui.note_shape import NoteShape, build_note_shape
from app.ui.pin_state import PinStateManager
from app.ui.styles.app_style import get_application_stylesheet
from app.ui.widgets.category_chip import CategoryChip
from app.ui.widgets.date_header import DateHeaderWidget
from app.ui.widgets.icon_button import IconButton
from app.ui.widgets.paper_surface import PaperSurface, shape_to_region
from app.ui.widgets.priority_selector import PrioritySelector
from app.ui.widgets.progress_ring import ProgressRing
from app.ui.widgets.quote_widget import QuoteWidget
from app.ui.widgets.task_input import TaskInput
from app.ui.widgets.task_list import TaskList

logger = logging.getLogger(__name__)

_NO_QUOTE_TEXT = "لا توجد حكمة متاحة لهذا اليوم"


class StartupManager(Protocol):
    """Operations required by the Settings dialog's startup controls."""

    def is_enabled(self) -> bool: ...

    def enable(self) -> Any: ...

    def disable(self) -> Any: ...


class _Edge(IntFlag):
    """Window edges grabbed during a frameless resize."""

    NONE = 0
    LEFT = 1
    RIGHT = 2
    TOP = 4
    BOTTOM = 8


@dataclass(frozen=True)
class _ResizeState:
    """Everything needed to compute an in-progress edge resize."""

    edges: _Edge
    start_geometry: QRect
    start_mouse: QPoint


class MainWindow(QMainWindow):
    """Sticky Note main window coordinating the daily quote and tasks."""

    #: Bottom content margin. Deeper than the side margins so no content row
    #: collides with the organic bottom edge of the paper.
    PAPER_BOTTOM_MARGIN = 18

    #: Transparent outer margin around the paper, inside which the drop
    #: shadow paints. Never used for content.
    SHADOW_MARGIN = 32

    #: Distance from a paper edge within which a press starts a resize.
    RESIZE_BORDER_WIDTH = 8

    #: Spacer that keeps the drag grip optically centered between the pin
    #: button (right) and the action group (left).
    HEADER_BALANCE_SPACING = 76

    def __init__(
        self,
        day: Day,
        quote_text: Optional[str],
        task_service: TaskService,
        initial_tasks: Sequence[Task] = (),
        geometry_manager: Optional[WindowGeometryManager] = None,
        history_service: Optional[HistoryService] = None,
        startup_manager: Optional[StartupManager] = None,
        on_exit_requested: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
        category_service: Optional[CategoryService] = None,
        icon_provider: Optional[CategoryIconProvider] = None,
        report_service: Optional[ReportService] = None,
        window_controller: Optional[DesktopWindowController] = None,
        pin_state_manager: Optional[PinStateManager] = None,
        on_carry_forward_requested: Optional[Callable[[], int]] = None,
    ) -> None:
        super().__init__(parent)
        self._day = day
        self._task_service = task_service
        self._report_service = report_service
        self._history_service = history_service
        self._startup_manager = startup_manager
        self._on_exit_requested = on_exit_requested
        self._window_controller = window_controller
        self._on_carry_forward_requested_cb = on_carry_forward_requested
        self._geometry_manager = geometry_manager or WindowGeometryManager()

        # Categories load once per window lifecycle: no polling, no
        # per-interaction DB reads. Both are empty when no service is wired.
        # New-task selection uses active categories only; read-only surfaces
        # (History) need all of them so inactive ones stay identifiable.
        self._categories: Sequence[Category] = (
            category_service.list_active_categories() if category_service else ()
        )
        self._all_categories: Sequence[Category] = (
            category_service.list_all_categories() if category_service else ()
        )
        # The icon provider is filesystem-only, so a default is always safe.
        self._icon_provider = icon_provider or CategoryIconProvider()

        # Pinned is the historical default (desktop tool window). The flag
        # only changes through _apply_pin_state, after the platform confirms.
        self._pin_manager = pin_state_manager or PinStateManager()
        self._pinned = self._pin_manager.is_pinned()

        # True only when an explicit exit was requested; otherwise closing
        # the window hides it to the tray.
        self._allow_window_close = False

        # Drag / resize state (frameless window).
        self._is_dragging = False
        self._drag_start_pos = QPoint()
        self._resize: Optional[_ResizeState] = None
        self.setMouseTracking(True)

        # Organic paper silhouette, refreshed on size changes only.
        self._note_shape: Optional[NoteShape] = None
        self._note_shape_size: Optional[tuple[int, int]] = None

        # Frameless window; pinned adds Qt.Tool before native realization,
        # which prevents a taskbar button and Win+D minimize-all.
        self.setWindowFlags(self._window_flags(self._pinned))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(320, 480)
        self.setAccessibleName("نافذة الملاحظة اليومية دايلي ستيكي")
        self._apply_window_icon()

        self._central_widget = QWidget(self)
        self._central_widget.setObjectName("centralWidget")
        self._central_widget.setMouseTracking(True)
        self.setCentralWidget(self._central_widget)

        self._init_layout(day.date, quote_text, initial_tasks)
        self.setStyleSheet(get_application_stylesheet())

        gx, gy, gw, gh = self._geometry_manager.get_validated_geometry()
        self.setGeometry(gx, gy, gw, gh)
        self._update_note_shape()

    # -------------------------------------------------------------------------
    # Construction
    # -------------------------------------------------------------------------

    def _apply_window_icon(self) -> None:
        try:
            logo_path = get_logo_path()
            if logo_path.is_file():
                self.setWindowIcon(QIcon(str(logo_path)))
        except Exception as exc:
            logger.debug("Window icon unavailable: %s", exc)

    def _init_layout(
        self,
        date_str: str,
        quote_text: Optional[str],
        initial_tasks: Sequence[Task],
    ) -> None:
        # The transparent margin frames the paper on every side: the drop
        # shadow paints into it and clicks pass through it (the window mask
        # follows the paper, not the outer rect).
        outer_layout = QVBoxLayout(self._central_widget)
        outer_layout.setContentsMargins(*(self.SHADOW_MARGIN,) * 4)
        outer_layout.setSpacing(0)

        self._paper_surface = PaperSurface(parent=self._central_widget)
        self._paper_surface.setAccessibleName("لوحة الملاحظة الورقية")
        outer_layout.addWidget(self._paper_surface)

        # The deeper bottom margin keeps content clear of the organic tears.
        paper_layout = QVBoxLayout(self._paper_surface)
        paper_layout.setContentsMargins(16, 12, 16, self.PAPER_BOTTOM_MARGIN)
        paper_layout.setSpacing(12)

        # 1. Top bar, 2. date, 3. progress ring, 4. quote, 5. tasks, 6. input.
        paper_layout.addWidget(self._build_header())

        self._date_header = DateHeaderWidget(date_str, parent=self._paper_surface)
        paper_layout.addWidget(self._date_header)

        self._progress_ring = ProgressRing(parent=self._paper_surface)
        paper_layout.addWidget(self._progress_ring)

        self._quote_widget = QuoteWidget(
            quote_text=quote_text, parent=self._paper_surface
        )
        paper_layout.addWidget(self._quote_widget)

        self._build_task_list(initial_tasks)
        paper_layout.addWidget(self._task_list, 1)

        paper_layout.addWidget(self._build_input_dock())

        self._init_shadow()
        self._init_shortcuts()
        self._rechain_window_tab_order()

    def _build_header(self) -> QFrame:
        """Top bar: pin (right), drag grip (center), actions (left).

        The bar is a drag area except on the buttons.
        """
        header = QFrame(self._paper_surface)
        header.setObjectName("headerFrame")
        header.setCursor(Qt.CursorShape.ArrowCursor)
        self._header_frame = header

        row = QHBoxLayout(header)
        row.setContentsMargins(0, 0, 0, 4)
        row.setSpacing(4)

        self._pin_btn = self._make_header_button(
            "pin", "pinButton", "تثبيت", "تثبيت على سطح المكتب",
            self._on_pin_clicked, header,
        )
        row.addWidget(self._pin_btn)
        row.addSpacing(self.HEADER_BALANCE_SPACING)
        row.addStretch(1)

        # Drag grip: affordance only, never focusable.
        self._grip = QLabel(header)
        self._grip.setObjectName("gripPill")
        self._grip.setFixedSize(32, 4)
        self._grip.setAccessibleName("")
        self._grip.setCursor(Qt.CursorShape.OpenHandCursor)
        self._grip.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        row.addWidget(self._grip)
        row.addStretch(1)

        self._archive_btn = self._make_header_button(
            "archive", "headerIconButton", "الأرشيف", "الأرشيف",
            self._on_history_requested, header,
        )
        self._settings_btn = self._make_header_button(
            "settings", "headerIconButton", "إعدادات", "إعدادات",
            self._on_settings_requested, header,
        )
        self._close_btn = self._make_header_button(
            "close", "headerIconButton", "إغلاق", "إغلاق",
            self._on_exit_clicked, header,
        )
        for button in (self._archive_btn, self._settings_btn, self._close_btn):
            row.addWidget(button)

        # Buttons that must receive clicks instead of starting a drag.
        self._header_buttons = (
            self._pin_btn,
            self._archive_btn,
            self._settings_btn,
            self._close_btn,
        )

        self._refresh_pin_visuals()
        return header

    @staticmethod
    def _make_header_button(
        icon_key: str,
        object_name: str,
        accessible_name: str,
        tooltip: str,
        on_click: Callable[[], None],
        parent: QWidget,
    ) -> IconButton:
        button = IconButton(icon_key, parent=parent)
        button.setObjectName(object_name)
        button.setAccessibleName(accessible_name)
        button.setToolTip(tooltip)
        button.clicked.connect(on_click)
        return button

    def _build_task_list(self, initial_tasks: Sequence[Task]) -> None:
        task_list = TaskList(parent=self._paper_surface)
        task_list.task_completed_toggled.connect(self._on_task_completed_toggled)
        task_list.task_edit_requested.connect(self._on_task_edit_requested)
        task_list.task_delete_requested.connect(self._on_task_delete_requested)
        task_list.task_priority_change_requested.connect(
            self._on_task_priority_change_requested
        )
        task_list.task_category_change_requested.connect(
            self._on_task_category_change_requested
        )
        task_list.task_inline_edit_committed.connect(
            self._on_task_inline_edit_committed
        )
        task_list.clear_completed_requested.connect(self._on_clear_completed_requested)
        task_list.history_requested.connect(self._on_history_requested)
        task_list.dashboard_requested.connect(self._on_dashboard_requested)
        task_list.settings_requested.connect(self._on_settings_requested)
        task_list.set_categories(self._categories, self._icon_provider)
        task_list.set_tasks(initial_tasks)
        self._task_list = task_list
        self._refresh_progress()

    def _build_input_dock(self) -> QFrame:
        """Bottom dock: input card (text + add) and, on its physical left,
        the category chip and priority selector (RTL: added after the card).
        """
        dock = QFrame(self._paper_surface)
        dock.setObjectName("taskInputDock")
        dock_layout = QHBoxLayout(dock)
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.setSpacing(8)

        card = QFrame(dock)
        card.setObjectName("taskInputCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(6, 4, 6, 4)
        card_layout.setSpacing(6)

        self._task_input = TaskInput(parent=card)
        self._task_input.task_submitted.connect(self._on_task_submitted)
        card_layout.addWidget(self._task_input, 1)

        # Disabled while the input is blank; the Enter path keeps its own
        # empty-text guard.
        self._add_btn = QPushButton("+", card)
        self._add_btn.setObjectName("taskAddButton")
        self._add_btn.setAccessibleName("إضافة المهمة")
        self._add_btn.setToolTip("إضافة المهمة")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add_button_clicked)
        self._task_input.textChanged.connect(self._on_input_text_changed)
        card_layout.addWidget(self._add_btn)

        dock_layout.addWidget(card, 1)

        self._category_selector = CategoryChip(self._categories, parent=dock)
        dock_layout.addWidget(self._category_selector)
        self._priority_selector = PrioritySelector(parent=dock)
        dock_layout.addWidget(self._priority_selector)

        return dock

    def _init_shadow(self) -> None:
        """Create the paper's drop shadow once; only its parameters change."""
        self._shadow_effect = QGraphicsDropShadowEffect(self._paper_surface)
        self._paper_surface.setGraphicsEffect(self._shadow_effect)
        self._apply_shadow_variant()

    def _init_shortcuts(self) -> None:
        """Window-scope shortcuts that never collide with text editing."""
        self._focus_input_shortcut = self._make_shortcut(
            "Ctrl+N", self._task_input.setFocus
        )
        self._toggle_pin_shortcut = self._make_shortcut(
            "Ctrl+Shift+P", self._on_pin_clicked
        )

    def _make_shortcut(self, sequence: str, slot: Callable[[], Any]) -> QShortcut:
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        shortcut.activated.connect(slot)
        return shortcut

    def _rechain_window_tab_order(self) -> None:
        """Keyboard chain: pin, archive, settings, close, rows, input, add,
        category chip, priority selector.

        Row ends are anchored through the list, which re-links them on every
        relayout, so this runs once at setup.
        """
        QWidget.setTabOrder(self._pin_btn, self._archive_btn)
        QWidget.setTabOrder(self._archive_btn, self._settings_btn)
        QWidget.setTabOrder(self._settings_btn, self._close_btn)
        self._task_list.set_chain_anchors(self._close_btn, self._task_input)
        QWidget.setTabOrder(self._task_input, self._add_btn)
        QWidget.setTabOrder(self._add_btn, self._category_selector)
        QWidget.setTabOrder(self._category_selector, self._priority_selector)

    # -------------------------------------------------------------------------
    # Organic paper silhouette: shape + window mask lifecycle
    # -------------------------------------------------------------------------

    def _update_note_shape(self) -> None:
        """Rebuild the paper silhouette and window mask for the paper size.

        Skipped when the size is unchanged, so repeated resize/show events
        cost nothing.
        """
        paper = self._paper_surface.geometry()
        size = (paper.width(), paper.height())
        if self._note_shape is not None and size == self._note_shape_size:
            return

        self._note_shape_size = size
        try:
            shape = build_note_shape(float(size[0]), float(size[1]))
        except ValueError as exc:
            # A zero-sized window can happen transiently while minimising.
            logger.debug("Skipping paper silhouette for size %s: %s", size, exc)
            return

        self._note_shape = shape
        self._paper_surface.set_shape(shape)
        self._update_note_mask()

    def _update_note_mask(self) -> None:
        """Make the OS window follow the paper silhouette.

        The mask comes from the same shape the paper is painted from,
        translated to the paper's position, so the transparent shadow margin
        stays click-through.
        """
        if self._note_shape is None:
            return
        try:
            top_left = self._paper_surface.pos()
            region = shape_to_region(self._note_shape)
            self.setMask(region.translated(top_left.x(), top_left.y()))
        except Exception as exc:  # pragma: no cover - platform specific
            logger.warning("Failed to apply the organic paper window mask: %s", exc)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._update_note_shape()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().showEvent(event)
        self._update_note_shape()

    # -------------------------------------------------------------------------
    # Pin state
    # -------------------------------------------------------------------------

    @staticmethod
    def _window_flags(pinned: bool) -> Qt.WindowType:
        flags = Qt.WindowType.FramelessWindowHint
        if pinned:
            flags |= Qt.WindowType.Tool
        return flags

    def is_pinned(self) -> bool:
        """Current pinned state (desktop-widget mode when True)."""
        return self._pinned

    def _refresh_pin_visuals(self) -> None:
        """Sync the pin button with the current state (never persists)."""
        if self._pinned:
            self._pin_btn.set_icon_key("pin_active")
            self._pin_btn.set_state_colors(
                theme.AMBER, theme.AMBER, theme.TEXT_DISABLED
            )
            label = "إلغاء التثبيت"
            tooltip = label
        else:
            self._pin_btn.set_icon_key("pin")
            self._pin_btn.set_state_colors(
                theme.TEXT_SECONDARY, theme.TEXT, theme.TEXT_DISABLED
            )
            label = "تثبيت"
            tooltip = "تثبيت على سطح المكتب"

        self._pin_btn.setToolTip(tooltip)
        self._pin_btn.setAccessibleName(label)
        self._pin_btn.setProperty("active", self._pinned)
        self._pin_btn.style().unpolish(self._pin_btn)
        self._pin_btn.style().polish(self._pin_btn)

    def _apply_shadow_variant(self) -> None:
        """Drop-shadow parameters for the current pin state."""
        if self._pinned:
            blur, offset_y, alpha = 24, 8, 89
        else:
            blur, offset_y, alpha = 60, 24, 115
        self._shadow_effect.setBlurRadius(blur)
        self._shadow_effect.setOffset(0, offset_y)
        self._shadow_effect.setColor(QColor(0, 0, 0, alpha))

    def _sync_pin_presentation(self) -> None:
        self._refresh_pin_visuals()
        self._apply_shadow_variant()

    def _on_pin_clicked(self) -> None:
        """Toggle the pinned state through the platform layer."""
        if not self._apply_pin_state(not self._pinned):
            QMessageBox.warning(
                self,
                "تعذر تغيير التثبيت",
                "تعذر تطبيق حالة التثبيت على سطح المكتب.",
            )

    def _reshow_with_flags(self, pinned: bool) -> None:
        """Recreate the native window with the flags for ``pinned``."""
        self.hide()
        self.setWindowFlags(self._window_flags(pinned))
        self.show()

    def _apply_pin_state(self, pinned: bool) -> bool:
        """Apply a pin state end to end; roll back on failure.

        Window flags are switched first, then the platform layer applies
        desktop/taskbar behavior for the new HWND. Anything but a confirmed
        platform success keeps the previous state: window flags and visuals
        restored, nothing persisted. Returns True on success.
        """
        if pinned == self._pinned:
            self._sync_pin_presentation()
            return True

        try:
            self._reshow_with_flags(pinned)
            applied = (
                self._window_controller is not None
                and self._window_controller.set_pinned(int(self.winId()), pinned)
            )
            if not applied:
                raise RuntimeError("platform layer rejected the pin state")
        except Exception as exc:
            logger.error("Failed to apply pin state %s: %s", pinned, exc)
            try:
                self._reshow_with_flags(self._pinned)
            except Exception as rollback_exc:  # pragma: no cover - defensive
                logger.error("Pin rollback failed: %s", rollback_exc)
            self._sync_pin_presentation()
            return False

        self._pinned = pinned
        self._sync_pin_presentation()
        self._pin_manager.save_pinned(pinned)
        return True

    # -------------------------------------------------------------------------
    # Daily view and progress
    # -------------------------------------------------------------------------

    def refresh_daily_view(
        self,
        day: Day,
        quote_text: Optional[str],
        tasks: Sequence[Task],
    ) -> None:
        """Update date, quote, and tasks without recreating widgets."""
        self._day = day
        self._date_header.set_date(day.date)
        self._quote_widget.set_quote_text(quote_text or _NO_QUOTE_TEXT)
        self._task_list.set_tasks(tasks)
        self._refresh_progress()

    def _refresh_progress(self) -> None:
        """Recompute today's stats from in-memory rows and update the ring.

        No DB round trip: TaskList rows already carry current Tasks.
        """
        stats = compute_daily_stats(self._task_list.tasks_snapshot())
        self._progress_ring.set_progress(stats.completed, stats.total)

    def _reload_tasks(self) -> None:
        """Reload today's rows from the service and refresh the ring."""
        if self._day.id is None:
            logger.warning("Cannot reload tasks: day.id is None")
            return

        self._task_list.set_tasks(self._task_service.get_today_tasks(self._day.id))
        self._refresh_progress()

    def _task_item(self, task_id: int | None):
        """Return the on-screen row for ``task_id``, if any."""
        if task_id is None:
            return None
        return self._task_list.item_for(task_id)

    # -------------------------------------------------------------------------
    # Task input
    # -------------------------------------------------------------------------

    def _on_task_submitted(self, raw_text: str) -> None:
        """Create a task from the input.

        Priority and category come from the selectors, never from the text.
        The input is cleared only AFTER creation succeeds; on failure the
        text (and category selection) stay untouched.
        """
        if self._day.id is None:
            logger.error("Cannot create task: day.id is None")
            return

        try:
            created_task = self._task_service.create_task(
                self._day.id,
                raw_text,
                priority=self._priority_selector.selected_priority(),
                category_id=self._category_selector.selected_category_id(),
            )
            if created_task is not None:
                self._task_list.add_task(created_task)
                self._task_input.clear()
                # Priority resets to neutral; the category is kept for fast
                # batch entry.
                self._priority_selector.set_priority(TaskPriority.MEDIUM)
                if created_task.id is not None:
                    self._task_list.ensure_task_visible(created_task.id)
                self._refresh_progress()
            self._task_input.setFocus()
        except Exception as exc:
            logger.error("Failed to create task %r: %s", raw_text, exc)

    def _on_add_button_clicked(self) -> None:
        self._on_task_submitted(self._task_input.text())

    def _on_input_text_changed(self, text: str) -> None:
        self._add_btn.setEnabled(bool(text.strip()))

    # -------------------------------------------------------------------------
    # Task row actions
    # -------------------------------------------------------------------------

    def _on_task_completed_toggled(self, task_id: int, is_completed: bool) -> None:
        try:
            self._task_service.toggle_task_completion(task_id, is_completed)
            # Keep the row in sync even if this handler was invoked without
            # the checkbox signal.
            item = self._task_item(task_id)
            if item is not None:
                item.set_completed_silently(is_completed)
            self._task_list.refresh_task_order()
            self._refresh_progress()
            self._move_focus_after_toggle(task_id)
        except Exception as exc:
            logger.error("Failed to toggle completion for task %d: %s", task_id, exc)

    def _move_focus_after_toggle(self, task_id: int) -> None:
        """Focus the next open task, or the input when none remains.

        "Next" is positional in the stored order, at or after the toggled
        row: completing a middle task moves to its successor; completing the
        last open task moves to the add input; uncompleting keeps focus on
        the row itself. Only visible, live rows are targeted. Focus only:
        completion, order, and records are untouched.
        """
        if self._day.id is None:
            return

        try:
            open_tasks = [
                task
                for task in self._task_service.get_today_tasks(self._day.id)
                if not task.is_completed
            ]
        except Exception as exc:
            logger.error("Failed to resolve focus target after toggle: %s", exc)
            return

        def order_key(task: Task) -> tuple[int, int]:
            return (task.position, task.id or 0)

        toggled = self._task_item(task_id)
        anchor = order_key(toggled.task) if toggled is not None else None

        for task in sorted(open_tasks, key=order_key):
            if anchor is not None and order_key(task) < anchor:
                continue
            target = self._task_item(task.id)
            if target is not None and target.isVisible():
                target.focus_checkbox()
                return

        self._task_input.setFocus()

    def _on_task_edit_requested(self, task_id: int) -> None:
        """Open the edit dialog and persist changed text/category/priority.

        Current values come from the on-screen row, so no DB round trip is
        needed. Each field is saved independently: changing one never
        resets the others.
        """
        try:
            item = self._task_item(task_id)
            current_text = item.task_text if item else ""
            current_priority = item.priority if item else TaskPriority.MEDIUM
            current_category = item.category_id if item else DEFAULT_CATEGORY_ID

            from app.ui.widgets.task_edit_dialog import TaskEditDialog

            dialog = TaskEditDialog(
                initial_text=current_text,
                initial_priority=current_priority,
                initial_category_id=current_category,
                categories=self._categories,
                icon_provider=self._icon_provider,
                parent=self,
            )
            if not dialog.exec():
                return

            new_text = dialog.get_text()
            if new_text and new_text != current_text:
                if self._task_service.update_task_text(task_id, new_text):
                    self._task_list.update_task_text(task_id, new_text)

            new_priority = dialog.get_priority()
            if new_priority != current_priority:
                self._task_service.update_task_priority(task_id, new_priority)
                self._task_list.update_task_priority(task_id, new_priority)

            # Without category choices (pre-category call sites) the dialog
            # can only echo the default; never downgrade a real category.
            if dialog.has_category_choices():
                new_category = dialog.get_category_id()
                if new_category != current_category:
                    self._task_service.update_task_category(task_id, new_category)
                    self._task_list.update_task_category(task_id, new_category)
        except Exception as exc:
            logger.error("Failed to edit task %d: %s", task_id, exc)

    def _on_task_priority_change_requested(
        self, task_id: int, priority: TaskPriority
    ) -> None:
        """Change only a task's priority (from its context menu)."""
        try:
            if not isinstance(priority, TaskPriority):
                priority = TaskPriority(priority)
            self._task_service.update_task_priority(task_id, priority)
            self._task_list.update_task_priority(task_id, priority)
        except Exception as exc:
            logger.error("Failed to change priority for task %d: %s", task_id, exc)

    def _on_task_category_change_requested(
        self, task_id: int, category_id: str
    ) -> None:
        """Change only a task's category (from its context menu)."""
        try:
            self._task_service.update_task_category(task_id, category_id)
            self._task_list.update_task_category(task_id, category_id)
        except Exception as exc:
            logger.error("Failed to change category for task %d: %s", task_id, exc)

    def _on_task_inline_edit_committed(self, task_id: int, new_text: str) -> None:
        """Persist an inline title edit (text column only).

        Blank input never reaches here (the row cancels it) and the service
        rejects it again defensively.
        """
        try:
            if self._task_service.update_task_text(task_id, new_text):
                self._task_list.update_task_text(task_id, new_text)
        except Exception as exc:
            logger.error("Failed to save inline edit for task %d: %s", task_id, exc)

    def _on_task_delete_requested(self, task_id: int) -> None:
        try:
            self._task_service.delete_task(task_id)
            self._task_list.remove_task(task_id)
            self._refresh_progress()
        except Exception as exc:
            logger.error("Failed to delete task %d: %s", task_id, exc)

    def _on_clear_completed_requested(self) -> None:
        if self._day.id is None:
            return
        try:
            self._task_service.clear_completed_tasks(self._day.id)
            self._reload_tasks()
        except Exception as exc:
            logger.error(
                "Failed to clear completed tasks for day %d: %s", self._day.id, exc
            )

    # -------------------------------------------------------------------------
    # Secondary windows
    # -------------------------------------------------------------------------

    def _on_history_requested(self) -> None:
        """Open the read-only History viewer."""
        if self._history_service is None:
            logger.warning("HistoryService not configured on MainWindow")
            return
        try:
            from app.ui.windows.history_window import HistoryWindow

            HistoryWindow(
                history_service=self._history_service,
                initial_date=self._day.date,
                parent=self,
                categories=self._all_categories,
                icon_provider=self._icon_provider,
            ).exec()
        except Exception as exc:
            logger.error("Failed to open History window: %s", exc)

    def _on_dashboard_requested(self) -> None:
        """Open the weekly reporting dashboard (fresh dialog per open)."""
        if self._report_service is None:
            logger.warning("ReportService not configured on MainWindow")
            return
        try:
            from app.ui.windows.dashboard_window import WeeklyDashboardWindow

            WeeklyDashboardWindow(
                report_service=self._report_service,
                icon_provider=self._icon_provider,
                qsettings=QSettings(),
                parent=self,
            ).exec()
        except Exception as exc:
            logger.error("Failed to open Dashboard window: %s", exc)

    def _on_settings_requested(self) -> None:
        """Open the Settings dialog (fresh dialog per open)."""
        if self._startup_manager is None:
            logger.warning("StartupManager not configured on MainWindow")
            return
        try:
            from app.ui.windows.settings_window import SettingsWindow

            SettingsWindow(startup_manager=self._startup_manager, parent=self).exec()
        except Exception as exc:
            logger.error("Failed to open Settings window: %s", exc)

    def _on_exit_clicked(self) -> None:
        """Trigger canonical application shutdown via the registered path."""
        logger.info("Exit button clicked; initiating application shutdown.")
        self._allow_window_close = True
        if self._on_exit_requested is not None:
            self._on_exit_requested()
        else:
            self.close()

    # -------------------------------------------------------------------------
    # Application menu
    # -------------------------------------------------------------------------

    def _on_carry_forward_requested(self) -> None:
        """Manually carry yesterday's leftovers into today (idempotent).

        Same-day catch-up for a rollover that never ran (e.g. the app was
        closed at midnight). Delegates to the injected operation, then
        reloads today's rows and progress.
        """
        if self._day.id is None:
            return
        if self._on_carry_forward_requested_cb is None:
            logger.warning("Carry-forward requested without an injected operation")
            return
        try:
            carried = self._on_carry_forward_requested_cb() or 0
            logger.info("Carried %d task(s) forward into %s", carried, self._day.date)
            self._reload_tasks()
        except Exception as exc:
            logger.error(
                "Failed to carry tasks forward for day %s: %s", self._day.date, exc
            )

    def _on_open_app_data_requested(self) -> None:
        """Open the per-user application-data folder in the file manager."""
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(get_app_data_dir())))
        except Exception as exc:
            logger.error("Failed to open application data folder: %s", exc)

    def _build_window_menu(self) -> QMenu:
        """Assemble the application menu (fresh instance per open).

        Every action routes to an existing handler exactly once; dismissing
        the menu triggers nothing. Rows keep their own context menu.
        """
        menu = QMenu(self)
        menu.setObjectName("appContextMenu")
        menu.setAccessibleName("قائمة التطبيق")
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        menu.setMinimumWidth(220)

        def add(text: str, slot: Callable[[], Any]) -> None:
            action = QAction(text, menu)
            action.triggered.connect(slot)
            menu.addAction(action)

        add("إضافة مهمة", self._task_input.setFocus)
        add("نقل غير المكتمل", self._on_carry_forward_requested)
        add("إلغاء التثبيت" if self._pinned else "تثبيت", self._on_pin_clicked)
        add("إعدادات", self._on_settings_requested)
        menu.addSeparator()
        add("فتح بيانات التطبيق", self._on_open_app_data_requested)
        add("إغلاق التطبيق", self._on_exit_clicked)

        return menu

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Show the application menu for window-level clicks.

        Task rows and the task list handle (and accept) their own context
        menus, so only clicks elsewhere reach this handler.
        """
        self._build_window_menu().exec(event.globalPos())
        event.accept()

    # -------------------------------------------------------------------------
    # Dragging and resizing (frameless window)
    # -------------------------------------------------------------------------

    def _determine_resize_edges(self, global_pos: QPoint) -> _Edge:
        """Return the resize edges near ``global_pos``.

        Edges follow the paper rect: the shadow margin is click-through, so
        grabbing works on the paper itself.
        """
        paper = self._paper_surface.geometry()
        top_left = self.mapToGlobal(paper.topLeft())
        bottom_right = self.mapToGlobal(paper.bottomRight())
        grab = self.RESIZE_BORDER_WIDTH
        x, y = global_pos.x(), global_pos.y()
        edges = _Edge.NONE

        if abs(x - top_left.x()) <= grab:
            edges |= _Edge.LEFT
        elif abs(x - bottom_right.x()) <= grab:
            edges |= _Edge.RIGHT

        if abs(y - top_left.y()) <= grab:
            edges |= _Edge.TOP
        elif abs(y - bottom_right.y()) <= grab:
            edges |= _Edge.BOTTOM

        return edges

    def _update_cursor_for_edges(self, edges: _Edge) -> None:
        if edges in (_Edge.LEFT | _Edge.TOP, _Edge.RIGHT | _Edge.BOTTOM):
            shape = Qt.CursorShape.SizeFDiagCursor
        elif edges in (_Edge.RIGHT | _Edge.TOP, _Edge.LEFT | _Edge.BOTTOM):
            shape = Qt.CursorShape.SizeBDiagCursor
        elif edges & (_Edge.LEFT | _Edge.RIGHT):
            shape = Qt.CursorShape.SizeHorCursor
        elif edges & (_Edge.TOP | _Edge.BOTTOM):
            shape = Qt.CursorShape.SizeVerCursor
        else:
            shape = Qt.CursorShape.ArrowCursor
        self.setCursor(shape)

    def _is_on_header_drag_area(self, global_pos: QPoint) -> bool:
        """True inside the header but not on one of its buttons."""
        local_pos = self._header_frame.mapFromGlobal(global_pos)
        if not self._header_frame.rect().contains(local_pos):
            return False
        return not any(
            button.geometry().contains(local_pos) for button in self._header_buttons
        )

    def _resized_geometry(self, state: _ResizeState, global_pos: QPoint) -> QRect:
        """Geometry for the given resize, honoring the minimum size."""
        start = state.start_geometry
        delta = global_pos - state.start_mouse
        edges = state.edges
        rect = QRect(start)

        if edges & _Edge.RIGHT:
            rect.setWidth(max(self.minimumWidth(), start.width() + delta.x()))
        elif edges & _Edge.LEFT:
            if start.width() - delta.x() >= self.minimumWidth():
                rect.setLeft(start.x() + delta.x())

        if edges & _Edge.BOTTOM:
            rect.setHeight(max(self.minimumHeight(), start.height() + delta.y()))
        elif edges & _Edge.TOP:
            if start.height() - delta.y() >= self.minimumHeight():
                rect.setTop(start.y() + delta.y())

        return rect

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            global_pos = event.globalPosition().toPoint()
            edges = self._determine_resize_edges(global_pos)

            if edges:
                self._resize = _ResizeState(edges, self.geometry(), global_pos)
                event.accept()
                return

            if self._is_on_header_drag_area(global_pos):
                self._is_dragging = True
                self._drag_start_pos = global_pos - self.frameGeometry().topLeft()
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        global_pos = event.globalPosition().toPoint()

        if self._resize is not None:
            self.setGeometry(self._resized_geometry(self._resize, global_pos))
            event.accept()
            return

        if self._is_dragging:
            self.move(global_pos - self._drag_start_pos)
            event.accept()
            return

        self._update_cursor_for_edges(self._determine_resize_edges(global_pos))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finish a drag/resize and persist geometry once, on release."""
        if event.button() == Qt.MouseButton.LeftButton:
            was_active = self._resize is not None or self._is_dragging

            if self._resize is not None:
                self._resize = None
                self._update_cursor_for_edges(_Edge.NONE)
            self._is_dragging = False

            if was_active:
                rect = self.geometry()
                self._geometry_manager.save_geometry(
                    rect.x(), rect.y(), rect.width(), rect.height()
                )

        super().mouseReleaseEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Hide to the tray unless an explicit exit was requested."""
        if self._allow_window_close:
            event.accept()
            return

        event.ignore()
        self.hide()
        logger.debug("Window close ignored; hidden to system tray.")
