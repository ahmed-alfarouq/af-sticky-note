"""Main Sticky Note window coordinator (Phase 4B).

Assembles the paper note surface, decorative pin header, daily quote,
scrollable task list, and task input. Features full accessibility
descriptions, RTL alignment, and keyboard navigation.

Paper silhouette (Phase 6B)
---------------------------
The note is no longer a rectangular window with rounded corners: it has an
organic paper silhouette (rounded top corners, straight sides, subtly
irregular bottom edge). The silhouette is owned by
:mod:`app.ui.note_shape` and is used in three places, always derived from
the *current* window size:

  1. ``PaperSurface`` paints the paper and its border along the path,
  2. the same path becomes the window mask, so the physical OS window
     (and therefore its clickable region) follows the paper, and
  3. the border is stroked on an inset copy of the path so it is never
     clipped by that mask.

The path and the mask are rebuilt **only** when the window size changes
(:meth:`_update_note_shape`, driven by ``resizeEvent`` / ``showEvent`` and
the initial setup) — never from ``paintEvent`` — so normal painting costs
one fill plus one stroke and no geometry or region work.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Protocol, Sequence, Tuple

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QColor, QContextMenuEvent, QIcon, QKeySequence, QMouseEvent, QShortcut
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
from app.infrastructure.paths import get_logo_path
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
from app.ui.widgets.quote_widget import QuoteWidget
from app.ui.widgets.task_input import TaskInput
from app.ui.widgets.task_list import TaskList

logger = logging.getLogger(__name__)


class StartupManager(Protocol):
    """Operations required by the Settings dialog's startup controls."""

    def is_enabled(self) -> bool: ...

    def enable(self) -> Any: ...

    def disable(self) -> Any: ...


class MainWindow(QMainWindow):
    """Sticky Note main window coordinating the daily quote and tasks."""

    #: Bottom content margin. Deeper than the side margins so no content row
    #: ever collides with the organic bottom edge of the paper.
    PAPER_BOTTOM_MARGIN = 18

    #: Transparent outer margin around the paper surface, inside which the
    #: drop shadow paints (v3 §2). Never used for content.
    SHADOW_MARGIN = 32

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
        self._category_service = category_service
        # Categories are loaded once per window lifecycle -- no polling, no
        # per-interaction DB reads. Empty when no service is wired (older
        # call sites), in which case category UI stays out of the way.
        self._categories: Sequence[Category] = (
            category_service.list_active_categories() if category_service is not None else ()
        )
        # Full metadata for read-only surfaces (History): inactive
        # categories must stay identifiable there, while new-task selection
        # above stays active-only.
        self._all_categories: Sequence[Category] = (
            category_service.list_all_categories() if category_service is not None else ()
        )
        # The icon provider is filesystem-only (no DB), so a default one is
        # always safe to construct.
        self._icon_provider = icon_provider or CategoryIconProvider()
        self._geometry_manager = geometry_manager or WindowGeometryManager()
        self._history_service = history_service
        self._startup_manager = startup_manager
        self._on_exit_requested = on_exit_requested
        self._window_controller = window_controller
        # Pinned is the historical default (desktop tool window). The stored
        # flag only ever changes through _apply_pin_state after the platform
        # confirms the new state.
        self._pin_manager = pin_state_manager or PinStateManager()
        self._pinned = self._pin_manager.is_pinned()
        self._on_carry_forward_requested_cb = on_carry_forward_requested
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
        # - Qt.Tool (pinned only): classifies the window as a tool/utility window
        #   before native realization, preventing taskbar button creation and
        #   Win+D shell minimize-all broadcasts
        if self._pinned:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
            )
        else:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        # Translucent background allows rounded CSS paper corners without artifacts
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(320, 480)
        self.setAccessibleName("نافذة الملاحظة اليومية دايلي ستيكي")

        # Set application window icon from bundled logo if present
        try:
            logo_path = get_logo_path()
            if logo_path.exists() and logo_path.is_file():
                self.setWindowIcon(QIcon(str(logo_path)))
        except Exception:
            pass

        self._central_widget = QWidget(self)
        self._central_widget.setObjectName("centralWidget")
        self._central_widget.setMouseTracking(True)
        self.setCentralWidget(self._central_widget)

        # Flag to indicate whether window closing should hide to tray or do real shutdown
        self._allow_window_close: bool = False

        # Organic paper silhouette state. The shape is derived from the current
        # window size and refreshed on size changes only -- see
        # _update_note_shape() / _update_note_mask().
        self._note_shape: Optional[NoteShape] = None
        self._note_shape_size: Optional[Tuple[int, int]] = None

        self._init_layout(day.date, quote_text, initial_tasks)
        self.setStyleSheet(get_application_stylesheet())

        # Restore persisted geometry if valid, else default
        gx, gy, gw, gh = self._geometry_manager.get_validated_geometry()
        self.setGeometry(gx, gy, gw, gh)

        # Build the paper silhouette (and its window mask) for the restored
        # size. Also re-checked in showEvent / resizeEvent.
        self._update_note_shape()

    def _init_layout(
        self,
        date_str: str,
        quote_text: Optional[str],
        initial_tasks: Sequence[Task],
    ) -> None:
        # Outer board layout. The 32 px transparent margin frames the paper
        # on every side: the drop shadow paints into it and clicks pass
        # through it to whatever is beneath (the window mask follows the
        # paper, not the outer rect).
        outer_layout = QVBoxLayout(self._central_widget)
        outer_layout.setContentsMargins(
            self.SHADOW_MARGIN, self.SHADOW_MARGIN, self.SHADOW_MARGIN, self.SHADOW_MARGIN
        )
        outer_layout.setSpacing(0)

        # Sticky Note paper surface (organic silhouette, painted by PaperSurface)
        self._paper_surface = PaperSurface(parent=self._central_widget)
        self._paper_surface.setAccessibleName("لوحة الملاحظة الورقية")
        outer_layout.addWidget(self._paper_surface)

        paper_layout = QVBoxLayout(self._paper_surface)
        # The bottom margin is deliberately deeper than the others: it keeps
        # every content row clear of the organic bottom edge, whose tears can
        # rise up to DEFAULT_TEAR_DEPTH pixels into the paper.
        paper_layout.setContentsMargins(16, 12, 16, self.PAPER_BOTTOM_MARGIN)
        paper_layout.setSpacing(12)

        # 1. Top bar (v3 §4): Pin button, Grip, Actions group. Visual order
        # right -> left; the bar is a drag area except on the buttons.
        self._header_frame = QFrame(self._paper_surface)
        self._header_frame.setObjectName("headerFrame")
        self._header_frame.setCursor(Qt.CursorShape.ArrowCursor)

        pin_row = QHBoxLayout(self._header_frame)
        pin_row.setContentsMargins(0, 0, 0, 4)
        pin_row.setSpacing(4)

        # Rightmost: pin toggle.
        self._pin_btn = IconButton("pin", parent=self._header_frame)
        self._pin_btn.setObjectName("pinButton")
        self._pin_btn.setAccessibleName("تثبيت")
        self._pin_btn.setToolTip("تثبيت على سطح المكتب")
        self._pin_btn.clicked.connect(self._on_pin_clicked)
        pin_row.addWidget(self._pin_btn)

        # Balancing spacer so the grip stays optically centered: the actions
        # group is 3*36 + 2*2 wide, the pin 36, so 76 px evens the sides.
        pin_row.addSpacing(76)
        pin_row.addStretch(1)

        # Center: drag grip (affordance only, never focusable).
        self._grip = QLabel(self._header_frame)
        self._grip.setObjectName("gripPill")
        self._grip.setFixedSize(32, 4)
        self._grip.setAccessibleName("")
        self._grip.setCursor(Qt.CursorShape.OpenHandCursor)
        self._grip.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        pin_row.addWidget(self._grip)

        pin_row.addStretch(1)

        # Leftmost: Archive, Settings, Close.
        self._archive_btn = IconButton("archive", parent=self._header_frame)

        self._archive_btn.setObjectName("headerIconButton")
        self._archive_btn.setAccessibleName("الأرشيف")
        self._archive_btn.setToolTip("الأرشيف")
        self._archive_btn.clicked.connect(self._on_history_requested)
        pin_row.addWidget(self._archive_btn)

        self._settings_btn = IconButton("settings", parent=self._header_frame)
        self._settings_btn.setObjectName("headerIconButton")
        self._settings_btn.setAccessibleName("إعدادات")
        self._settings_btn.setToolTip("إعدادات")
        self._settings_btn.clicked.connect(self._on_settings_requested)
        pin_row.addWidget(self._settings_btn)

        self._close_btn = IconButton("close", parent=self._header_frame)
        self._close_btn.setObjectName("headerIconButton")
        self._close_btn.setAccessibleName("إغلاق")
        self._close_btn.setToolTip("إغلاق")
        self._close_btn.clicked.connect(self._on_exit_clicked)
        pin_row.addWidget(self._close_btn)

        self._refresh_pin_visuals()

        paper_layout.addWidget(self._header_frame)

        # 2. Date header: strong day hierarchy + daily progress ring.
        self._date_header = DateHeaderWidget(date_str, parent=self._paper_surface)
        paper_layout.addWidget(self._date_header)

        # 3. Quiet daily quote (date lives in the header now).
        self._quote_widget = QuoteWidget(quote_text=quote_text, parent=self._paper_surface)
        paper_layout.addWidget(self._quote_widget)

        # 4. Scrollable Task List (completed sink last, section-labeled).
        self._task_list = TaskList(parent=self._paper_surface)
        self._task_list.task_completed_toggled.connect(self._on_task_completed_toggled)
        self._task_list.task_edit_requested.connect(self._on_task_edit_requested)
        self._task_list.task_delete_requested.connect(self._on_task_delete_requested)
        self._task_list.task_priority_change_requested.connect(
            self._on_task_priority_change_requested
        )
        self._task_list.task_category_change_requested.connect(
            self._on_task_category_change_requested
        )
        self._task_list.task_inline_edit_committed.connect(
            self._on_task_inline_edit_committed
        )
        self._task_list.clear_completed_requested.connect(self._on_clear_completed_requested)
        self._task_list.history_requested.connect(self._on_history_requested)
        self._task_list.dashboard_requested.connect(self._on_dashboard_requested)
        self._task_list.settings_requested.connect(self._on_settings_requested)
        self._task_list.set_categories(self._categories, self._icon_provider)
        self._task_list.set_tasks(initial_tasks)
        self._refresh_progress()
        paper_layout.addWidget(self._task_list, 1)

        # 4. Bottom input dock (Phase 7H): the input CARD holds only the
        # task text input and the add button. Category/priority selectors
        # are direct dock children OUTSIDE the card, on its physical left
        # (RTL: added after the card). Gaps come from the dock spacing.
        dock = QFrame(self._paper_surface)
        dock.setObjectName("taskInputDock")
        dock_layout = QHBoxLayout(dock)
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.setSpacing(8)

        # 1. Input card (RIGHTMOST in RTL): text field + add button only.
        card = QFrame(dock)
        card.setObjectName("taskInputCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(6, 4, 6, 4)
        card_layout.setSpacing(6)

        self._task_input = TaskInput(parent=card)
        self._task_input.task_submitted.connect(self._on_task_submitted)
        card_layout.addWidget(self._task_input, 1)

        self._add_btn = QPushButton("+", card)
        self._add_btn.setObjectName("taskAddButton")
        self._add_btn.setAccessibleName("إضافة المهمة")
        self._add_btn.setToolTip("إضافة المهمة")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._on_add_button_clicked)
        # Disabled-when-empty (v3 §8.1): whitespace-only input disables the
        # button; the Enter path keeps its own empty-text guard.
        self._add_btn.setEnabled(False)
        self._task_input.textChanged.connect(self._on_input_text_changed)
        card_layout.addWidget(self._add_btn)

        dock_layout.addWidget(card, 1)

        # 2. Category chip (v3 §8.2) + priority selector, on the physical
        # left of the card. The chip opens the custom dropdown (§9); the
        # priority combo stays until its own phase.
        self._category_selector = CategoryChip(
            self._categories, parent=dock
        )
        dock_layout.addWidget(self._category_selector)
        self._priority_selector = PrioritySelector(parent=dock)
        dock_layout.addWidget(self._priority_selector)

        paper_layout.addWidget(dock)

        # Documented shortcuts (v3 §11), window scope: they fire only while
        # this window is active, never while a popup/menu owns input, and
        # neither sequence collides with text-editing keys. Created once.
        self._focus_input_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        self._focus_input_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._focus_input_shortcut.activated.connect(self._task_input.setFocus)
        self._toggle_pin_shortcut = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        self._toggle_pin_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._toggle_pin_shortcut.activated.connect(self._on_pin_clicked)
        self._rechain_window_tab_order()

    def _rechain_window_tab_order(self) -> None:
        """Explicit keyboard chain (v3 §11): pin, archive, settings, close,
        rows, input, add, category chip, priority selector.

        Row ends are anchored through the list, which re-links them on every
        relayout, so this runs once at setup: no per-mutation calls needed.
        Pointer-only, no timers or signals.
        """
        QWidget.setTabOrder(self._pin_btn, self._archive_btn)
        QWidget.setTabOrder(self._archive_btn, self._settings_btn)
        QWidget.setTabOrder(self._settings_btn, self._close_btn)
        self._task_list.set_chain_anchors(self._close_btn, self._task_input)
        QWidget.setTabOrder(self._task_input, self._add_btn)
        QWidget.setTabOrder(self._add_btn, self._category_selector)
        QWidget.setTabOrder(self._category_selector, self._priority_selector)

        # Drop shadow for the paper, painted into the transparent margin.
        # Created once; only its parameters change with the pin state.
        self._shadow_effect = QGraphicsDropShadowEffect(self._paper_surface)
        self._paper_surface.setGraphicsEffect(self._shadow_effect)
        self._apply_shadow_variant()

    # -------------------------------------------------------------------------
    # Organic paper silhouette: shape + window mask lifecycle
    # -------------------------------------------------------------------------

    def _paper_rect(self):
        """Paper geometry in window coordinates (inside the shadow margin)."""
        pos = self._paper_surface.pos()
        size = self._paper_surface.size()
        return (pos.x(), pos.y(), size.width(), size.height())

    def _update_note_shape(self) -> None:
        """Rebuild the paper silhouette for the current paper size.

        This is the single place where the shape is (re)generated, and it is
        driven by geometry changes only:

            initial setup -> resizeEvent -> showEvent -> drag/resize release

        It is deliberately *not* called from ``paintEvent``: repainting must
        not rebuild paths or re-create window masks.

        The work is skipped entirely when the size has not changed, so
        repeated calls (e.g. several resize events while dragging a window
        edge, or a show after a resize) cost nothing.
        """
        _, _, width, height = self._paper_rect()
        size = (width, height)
        if self._note_shape is not None and size == self._note_shape_size:
            return

        self._note_shape_size = size
        try:
            shape = build_note_shape(float(size[0]), float(size[1]))
        except ValueError as exc:
            # A zero-sized window can happen transiently while minimising.
            logger.debug("Skipping paper silhouette for degenerate size %s: %s", size, exc)
            return

        self._note_shape = shape
        self._paper_surface.set_shape(shape)
        self._update_note_mask()

    def _update_note_mask(self) -> None:
        """Make the physical OS window follow the paper silhouette.

        The mask is derived from the exact same :class:`NoteShape` the paper
        is painted from, translated to the paper's window position (the paper
        sits inside the transparent shadow margin, so the margin stays
        click-through). Visible note, border and clickable region agree.

        Called from :meth:`_update_note_shape` only -- never while painting.
        """
        if self._note_shape is None:
            return
        try:
            x, y, _, _ = self._paper_rect()
            self.setMask(shape_to_region(self._note_shape).translated(x, y))
        except Exception as exc:  # pragma: no cover - defensive, platform specific
            logger.warning("Failed to apply the organic paper window mask: %s", exc)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        """Keep the paper silhouette and window mask in sync with the size."""
        super().resizeEvent(event)
        self._update_note_shape()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt naming
        """Refresh the silhouette once the window is actually sized and shown."""
        super().showEvent(event)
        self._update_note_shape()

    # -------------------------------------------------------------------------
    # Pin state (v3 §4.1)
    # -------------------------------------------------------------------------

    def is_pinned(self) -> bool:
        """Current pinned state (desktop-widget mode when True)."""
        return self._pinned

    def _refresh_pin_visuals(self) -> None:
        """Sync the pin button with the current state (never persists)."""
        if self._pinned:
            self._pin_btn.set_icon_key("pin_active")
            self._pin_btn.set_state_colors(theme.AMBER, theme.AMBER, theme.TEXT_DISABLED)
            self._pin_btn.setToolTip("إلغاء التثبيت")
            self._pin_btn.setAccessibleName("إلغاء التثبيت")
            self._pin_btn.setProperty("active", True)
        else:
            self._pin_btn.set_icon_key("pin")
            self._pin_btn.set_state_colors(theme.TEXT_SECONDARY, theme.TEXT, theme.TEXT_DISABLED)
            self._pin_btn.setToolTip("تثبيت على سطح المكتب")
            self._pin_btn.setAccessibleName("تثبيت")
            self._pin_btn.setProperty("active", False)
        self._pin_btn.style().unpolish(self._pin_btn)
        self._pin_btn.style().polish(self._pin_btn)

    def _apply_shadow_variant(self) -> None:
        """Drop-shadow parameters for the current pin state (v3 §2).

        No timers or animation: applied once per state change.
        """
        if self._pinned:
            self._shadow_effect.setBlurRadius(24)
            self._shadow_effect.setOffset(0, 8)
            self._shadow_effect.setColor(QColor(0, 0, 0, 89))
        else:
            self._shadow_effect.setBlurRadius(60)
            self._shadow_effect.setOffset(0, 24)
            self._shadow_effect.setColor(QColor(0, 0, 0, 115))

    def _on_pin_clicked(self) -> None:
        """Toggle the pinned state through the platform layer."""
        if not self._apply_pin_state(not self._pinned):
            QMessageBox.warning(
                self,
                "تعذر تغيير التثبيت",
                "تعذر تطبيق حالة التثبيت على سطح المكتب.",
            )

    def _apply_pin_state(self, pinned: bool) -> bool:
        """Apply a pin state end to end; roll back the visuals on failure.

        Window flags are switched first (pinned = Tool, unpinned = normal),
        then the platform layer applies desktop/taskbar behavior for the new
        HWND. Anything but a confirmed platform success keeps the previous
        state: visuals restored, nothing persisted. Returns True on success.
        """
        if pinned == self._pinned:
            self._refresh_pin_visuals()
            self._apply_shadow_variant()
            return True

        previous = self._pinned
        try:
            self.hide()
            if pinned:
                self.setWindowFlags(
                    Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                )
            else:
                self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.show()
            hwnd = int(self.winId())
            applied = (
                self._window_controller.set_pinned(hwnd, pinned)
                if self._window_controller is not None
                else False
            )
            if not applied:
                raise RuntimeError("platform layer rejected the pin state")
        except Exception as exc:
            logger.error("Failed to apply pin state %s: %s", pinned, exc)
            try:
                self.hide()
                if previous:
                    self.setWindowFlags(
                        Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                    )
                else:
                    self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
                self.show()
            except Exception as rollback_exc:  # pragma: no cover - defensive
                logger.error("Pin rollback failed: %s", rollback_exc)
            self._refresh_pin_visuals()
            self._apply_shadow_variant()
            return False

        self._pinned = pinned
        self._refresh_pin_visuals()
        self._apply_shadow_variant()
        self._pin_manager.save_pinned(pinned)
        return True

    def refresh_daily_view(
        self,
        day: Day,
        quote_text: Optional[str],
        tasks: Sequence[Task],
    ) -> None:
        """Update the displayed date, quote, and task list without recreating widgets."""
        self._day = day
        self._date_header.set_date(day.date)
        self._quote_widget.set_quote_text(quote_text or "لا توجد حكمة متاحة لهذا اليوم")
        self._task_list.set_tasks(tasks)
        self._refresh_progress()

    def _refresh_progress(self) -> None:
        """Recompute today's stats from in-memory rows and update the ring.

        No DB round trip: TaskList rows already carry current Tasks.
        """
        stats = compute_daily_stats(self._task_list.tasks_snapshot())
        self._date_header.set_progress(stats.completed, stats.total)

    def _on_task_submitted(self, raw_text: str) -> None:
        """Handle task submission from TaskInput.

        The priority and category chosen in the selectors are handed to the
        service as values -- they are never inferred from the task text.

        Crucial rule: TaskInput is only cleared AFTER task creation succeeds.
        If validation or persistence fails, raw text remains untouched -- and
        so does the category selection.
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
                # Priority resets to neutral; the category is KEPT for fast
                # batch entry (v3 §8.1). Clearing the input re-disables the
                # add button through the textChanged wiring below.
                self._priority_selector.set_priority(TaskPriority.MEDIUM)
                self._task_list.ensure_task_visible(created_task.id)
                self._refresh_progress()
            # Retain focus in input field whether text was created or empty
            self._task_input.setFocus()
        except Exception as exc:
            logger.error("Failed to create task %r: %s", raw_text, exc)
            # Input text is intentionally retained on error

    def _on_add_button_clicked(self) -> None:
        """Submit the current input text through the same creation path."""
        self._on_task_submitted(self._task_input.text())

    def _on_input_text_changed(self, text: str) -> None:
        """Enable the add button only for non-blank input."""
        self._add_btn.setEnabled(bool(text.strip()))

    def _on_task_completed_toggled(self, task_id: int, is_completed: bool) -> None:
        """Handle checkbox toggle from TaskList / TaskItem."""
        try:
            self._task_service.toggle_task_completion(task_id, is_completed)
            # Keep the row's carried task in sync even when this handler is
            # invoked without the checkbox signal (silent no-op otherwise).
            item = self._task_list._items.get(task_id)
            if item is not None:
                item.set_completed_silently(is_completed)
            # The row already restyled itself; reposition it between the
            # active/completed sections and refresh the progress ring.
            self._task_list.refresh_task_order()
            self._refresh_progress()
            self._move_focus_after_toggle(task_id)
        except Exception as exc:
            logger.error("Failed to toggle completion for task %d: %s", task_id, exc)

    def _move_focus_after_toggle(self, task_id: int) -> None:
        """Focus the next open task, or the input when none remains (v3 §7.3).

        "Next" is positional in the stored order, at or after the toggled
        row: completing a middle task moves to its successor; completing the
        last open task (or finding no open tasks at all) moves to the add
        input, ready for the next entry; uncompleting keeps focus on the row
        itself, which is open again. Only visible, live rows are targeted;
        anything else falls through to the input. Completion, order, and
        records are untouched -- focus only.
        """
        if self._day.id is None:
            return
        try:
            open_tasks = [
                task for task in self._task_service.get_today_tasks(self._day.id)
                if not task.is_completed
            ]
        except Exception as exc:
            logger.error("Failed to resolve focus target after toggle: %s", exc)
            return
        anchor = None
        item = self._task_list._items.get(task_id)
        if item is not None:
            anchor = (item._task.position, item._task.id or 0)
        ordered = sorted(open_tasks, key=lambda task: (task.position, task.id or 0))
        candidates = [
            task for task in ordered
            if anchor is None or (task.position, task.id or 0) >= anchor
        ]
        for task in candidates:
            target = self._task_list._items.get(task.id)
            if target is not None and target.isVisible():
                target._checkbox.setFocus()
                return
        self._task_input.setFocus()

    def _on_task_edit_requested(self, task_id: int) -> None:
        """Open edit dialog and persist updated task text/category/priority.

        The current values are read from the TaskItem that is already on
        screen -- the Task object it holds carries text, category, and
        priority -- so no extra database round trip is needed.
        """
        try:
            # Find the current task from the UI item; it already carries the
            # text, category, and priority.
            task_item = self._task_list._items.get(task_id)
            current_text = task_item.task_text if task_item else ""
            current_priority = task_item.priority if task_item else TaskPriority.MEDIUM
            current_category = (
                task_item.category_id if task_item is not None else DEFAULT_CATEGORY_ID
            )

            from app.ui.widgets.task_edit_dialog import TaskEditDialog
            dialog = TaskEditDialog(
                initial_text=current_text,
                initial_priority=current_priority,
                initial_category_id=current_category,
                categories=self._categories,
                icon_provider=self._icon_provider,
                parent=self,
            )
            if dialog.exec():
                new_text = dialog.get_text()
                new_priority = dialog.get_priority()

                # Text, category, and priority are independent: changing one
                # must never silently reset the others.
                if new_text and new_text != current_text:
                    if self._task_service.update_task_text(task_id, new_text):
                        self._task_list.update_task_text(task_id, new_text)
                if new_priority != current_priority:
                    self._task_service.update_task_priority(task_id, new_priority)
                    self._task_list.update_task_priority(task_id, new_priority)
                # Without category choices (pre-category call sites) the
                # dialog can only echo the default -- never downgrade a real
                # category the dialog never offered.
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
        """Change a task's priority straight from its context menu.

        Updates the record in place: same id, day, source task, completion
        state, text and position -- only the priority column changes.
        """
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
        """Change a task's category straight from its context menu.

        Updates the record in place: same id, day, source task, completion
        state, text, position and priority -- only the category column changes.
        """
        try:
            self._task_service.update_task_category(task_id, category_id)
            self._task_list.update_task_category(task_id, category_id)
        except Exception as exc:
            logger.error("Failed to change category for task %d: %s", task_id, exc)

    def _on_task_inline_edit_committed(self, task_id: int, new_text: str) -> None:
        """Persist an inline title edit through the single update path.

        Only the text column changes: identity, day, priority, completion,
        category, position, source, and timestamps handling stay with the
        service/repository. Blank input never reaches here (the row cancels
        it), and the service rejects it again defensively.
        """
        try:
            if self._task_service.update_task_text(task_id, new_text):
                self._task_list.update_task_text(task_id, new_text)
        except Exception as exc:
            logger.error("Failed to save inline edit for task %d: %s", task_id, exc)

    def _on_task_delete_requested(self, task_id: int) -> None:
        """Handle deletion of a specific task."""
        try:
            self._task_service.delete_task(task_id)
            self._task_list.remove_task(task_id)
            self._refresh_progress()
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
            self._refresh_progress()
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
                categories=self._all_categories,
                icon_provider=self._icon_provider,
            )
            history_win.exec()
        except Exception as exc:
            logger.error("Failed to open History window: %s", exc)

    def _on_dashboard_requested(self) -> None:
        """Open the weekly reporting dashboard (fresh dialog per open)."""
        if self._report_service is None:
            logger.warning("ReportService not configured on MainWindow")
            return
        try:
            from PySide6.QtCore import QSettings

            from app.ui.windows.dashboard_window import WeeklyDashboardWindow
            dashboard = WeeklyDashboardWindow(
                report_service=self._report_service,
                icon_provider=self._icon_provider,
                qsettings=QSettings(),
                parent=self,
            )
            dashboard.exec()
        except Exception as exc:
            logger.error("Failed to open Dashboard window: %s", exc)

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
    # Pinned-mode application menu (v3 §10)
    # -------------------------------------------------------------------------

    def _on_carry_forward_requested(self) -> None:
        """Manually carry yesterday's leftovers into today (idempotent).

        Same-day catch-up for a rollover that never ran (e.g. the app was
        closed at midnight and no transition has fired yet). Delegates to
        the injected carry-forward operation, then reloads today's rows and
        progress from the task service. Without an injected operation the
        menu action warns instead of silently doing nothing.
        """
        if self._day.id is None:
            return
        if self._on_carry_forward_requested_cb is None:
            logger.warning("Carry-forward requested without an injected operation")
            return
        try:
            carried = self._on_carry_forward_requested_cb() or 0
            logger.info("Carried %d task(s) forward into %s", carried, self._day.date)
            self._task_list.set_tasks(self._task_service.get_today_tasks(self._day.id))
            self._refresh_progress()
        except Exception as exc:
            logger.error("Failed to carry tasks forward for day %s: %s", self._day.date, exc)

    def _on_open_app_data_requested(self) -> None:
        """Open the per-user application-data folder in the file manager."""
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            from app.infrastructure.paths import get_app_data_dir

            QDesktopServices.openUrl(QUrl.fromLocalFile(str(get_app_data_dir())))
        except Exception as exc:
            logger.error("Failed to open application data folder: %s", exc)

    def _build_window_menu(self) -> QMenu:
        """Assemble the pinned-mode application menu (fresh instance per open).

        Item order, separator placement, and pin-label state follow v3 §10.
        Every action routes to an existing handler exactly once; dismissing
        the menu triggers nothing. Rows keep their own context menu, which
        is built and tested separately.
        """
        menu = QMenu(self)
        menu.setObjectName("appContextMenu")
        menu.setAccessibleName("قائمة التطبيق")
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        menu.setMinimumWidth(220)

        add_action = QAction("إضافة مهمة", menu)
        add_action.triggered.connect(lambda: self._task_input.setFocus())
        menu.addAction(add_action)

        carry_action = QAction("نقل غير المكتمل", menu)
        carry_action.triggered.connect(self._on_carry_forward_requested)
        menu.addAction(carry_action)

        pin_action = QAction(
            "إلغاء التثبيت" if self._pinned else "تثبيت", menu
        )
        pin_action.triggered.connect(self._on_pin_clicked)
        menu.addAction(pin_action)

        settings_action = QAction("إعدادات", menu)
        settings_action.triggered.connect(self._on_settings_requested)
        menu.addAction(settings_action)

        menu.addSeparator()

        data_action = QAction("فتح بيانات التطبيق", menu)
        data_action.triggered.connect(self._on_open_app_data_requested)
        menu.addAction(data_action)

        exit_action = QAction("إغلاق التطبيق", menu)
        exit_action.triggered.connect(self._on_exit_clicked)
        menu.addAction(exit_action)

        return menu

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Show the pinned-mode application menu for window-level clicks.

        Task rows and the task list handle their own context menus and
        accept those events, so only clicks elsewhere reach this handler.
        """
        menu = self._build_window_menu()
        menu.exec(event.globalPos())
        event.accept()

    # -------------------------------------------------------------------------
    # Dragging & Resizing Event Handlers (Phase 5G-A)
    # -------------------------------------------------------------------------

    RESIZE_BORDER_WIDTH = 8

    def _determine_resize_edges(self, global_pos: QPoint) -> int:
        """Calculate active resize edge bitmask for a given screen point.

        Edges follow the paper rect (inside the transparent shadow margin):
        the margin itself is click-through, so grabbing works on the paper.
        """
        paper = self._paper_surface.geometry()
        left = self.mapToGlobal(paper.topLeft())
        right = self.mapToGlobal(paper.bottomRight())
        x, y = global_pos.x(), global_pos.y()
        edges = 0

        # Left / Right
        if abs(x - left.x()) <= self.RESIZE_BORDER_WIDTH:
            edges |= 1  # Left
        elif abs(x - right.x()) <= self.RESIZE_BORDER_WIDTH:
            edges |= 2  # Right

        # Top / Bottom
        if abs(y - left.y()) <= self.RESIZE_BORDER_WIDTH:
            edges |= 4  # Top
        elif abs(y - right.y()) <= self.RESIZE_BORDER_WIDTH:
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
                    for btn_attr in ("_pin_btn", "_archive_btn", "_settings_btn", "_close_btn"):
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
