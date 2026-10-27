"""Scrollable list container for TaskItem widgets with accessibility."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QContextMenuEvent
from PySide6.QtWidgets import QFrame, QLabel, QMenu, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.core.models import Category, Task, TaskPriority
from app.ui.category_icons import CategoryIconProvider
from app.ui.icons import icon as vector_icon
from app.ui.widgets.task_item import TaskItem


def _view_order_key(task: Task) -> tuple:
    """Incomplete tasks first (by position), completed last (by position).

    A view-level ordering only: repository position values are never
    rewritten by the list.
    """
    return (1 if task.is_completed else 0, task.position, task.id or 0)


class TaskList(QScrollArea):
    """Scrollable container managing visual TaskItem instances."""

    task_completed_toggled = Signal(int, bool)  # task_id, is_completed
    task_edit_requested = Signal(int)           # task_id
    task_delete_requested = Signal(int)         # task_id
    task_priority_change_requested = Signal(int, object)  # task_id, TaskPriority
    task_category_change_requested = Signal(int, str)  # task_id, category_id
    task_inline_edit_committed = Signal(int, str)  # task_id, trimmed new text
    clear_completed_requested = Signal()        # emit to clear completed tasks for today
    history_requested = Signal()                # emit to open History UI
    dashboard_requested = Signal()              # emit to open weekly dashboard
    settings_requested = Signal()               # emit to open Settings UI

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("taskListScroll")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        # Task text wraps (including break opportunities for unbreakable
        # runs); metadata is fixed-size. A horizontal scrollbar must never
        # appear -- the Sticky is a fixed-width widget, not a document viewer.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAccessibleName("قائمة مهام اليوم")
        self.setAccessibleDescription("عرض المهام اليومية مع إمكانية تحديد إنجازها")

        self._container = QWidget(self)
        self._container.setObjectName("taskListContainer")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(12, 8, 12, 0)
        self._layout.setSpacing(2)
        self._layout.addStretch(1)

        self.setWidget(self._container)
        self._items: Dict[int, TaskItem] = {}
        # The scroll container itself is never interactive.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Completed-group header button (hidden when nothing is completed).
        # Collapse is presentation-only and session-scoped: hiding rows never
        # touches records, order, or statistics. Managed by _relayout.
        self._section_label = QPushButton(self._container)
        self._section_label.setObjectName("completedGroupHeader")
        self._section_label.setAccessibleName("مجموعة المهام المكتملة")
        self._section_label.setFixedHeight(32)
        self._section_label.clicked.connect(self._on_group_header_clicked)
        self._section_label.setVisible(False)
        self._completed_expanded = True
        # Empty/all-done states (v3 §7.1): one centered block, shown only
        # when there is nothing to act on. Presentation only: no records,
        # no signals, never focusable. Only the empty-day state remains; the
        # all-done variant was removed because a day whose tasks are all
        # finished is not an empty state -- the completed rows and their group
        # header already say so, and the block only duplicated that while
        # pushing the completed section down the list.
        self._empty_block = QWidget(self._container)
        self._empty_layout = QVBoxLayout(self._empty_block)
        self._empty_layout.setContentsMargins(24, 24, 24, 24)
        self._empty_layout.setSpacing(4)
        self._empty_title = QLabel(self._empty_block)
        self._empty_title.setObjectName("emptyStateTitle")
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_title.setWordWrap(True)
        self._empty_layout.addWidget(self._empty_title)
        self._empty_body = QLabel(self._empty_block)
        self._empty_body.setObjectName("emptyStateBody")
        self._empty_body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_body.setWordWrap(True)
        self._empty_layout.addWidget(self._empty_body)
        self._empty_block.setVisible(False)
        # Category choices forwarded to every TaskItem (empty until the
        # coordinator supplies the active list once per UI lifecycle).
        self._categories: List[Category] = []
        self._icon_provider: Optional[CategoryIconProvider] = None
        # Window-level tab-chain anchors (v3 §11), registered once by the
        # coordinator window: the chain runs before -> rows -> after, so it
        # stays correct no matter how often rows change.
        self._chain_before: Optional[QWidget] = None
        self._chain_after: Optional[QWidget] = None

    def set_categories(
        self,
        categories: Sequence[Category],
        icon_provider: Optional[CategoryIconProvider] = None,
    ) -> None:
        """Supply the category choices (and icons) for all task rows."""
        self._categories = list(categories)
        if icon_provider is not None:
            self._icon_provider = icon_provider
        for item in self._items.values():
            item.set_categories(self._categories, self._icon_provider)

    def set_tasks(self, tasks: Sequence[Task]) -> None:
        """Clear existing items and populate with provided tasks.

        View order is incomplete-first (by position), completed last --
        data order (repository position) is never rewritten by this.
        """
        self.clear_tasks()
        for task in sorted(tasks, key=_view_order_key):
            self._add_item(task)
        self._relayout()

    def add_task(self, task: Task) -> None:
        """Add a TaskItem at its view-ordered position (no list rebuild)."""
        if task.id is None:
            raise ValueError("Cannot add a task without an ID")

        if task.id in self._items:
            return

        self._add_item(task)
        self._relayout()

    def _add_item(self, task: Task) -> None:
        """Construct, wire, and register one row (positioning via _relayout)."""
        assert task.id is not None
        item = TaskItem(task, self._container, self._categories, self._icon_provider)
        item.completed_toggled.connect(self.task_completed_toggled.emit)
        item.edit_requested.connect(self.task_edit_requested.emit)
        item.delete_requested.connect(self.task_delete_requested.emit)
        item.priority_change_requested.connect(self.task_priority_change_requested.emit)
        item.category_change_requested.connect(self.task_category_change_requested.emit)
        item.inline_edit_committed.connect(self.task_inline_edit_committed.emit)
        self._items[task.id] = item

    def refresh_task_order(self) -> None:
        """Reposition existing rows after a completion toggle (same widgets).

        Called by the coordinator after persisting the toggle; moves the
        row between the active and completed sections without recreating it.
        """
        self._relayout()

    def _relayout(self) -> None:
        """Order rows (incomplete, group header, completed) before stretch.

        All row widgets are detached first: re-inserting widgets that are
        already laid out would corrupt the trailing-stretch invariant and
        push rows to the bottom (leaving a gap above the list).
        """
        ordered = sorted(self._items.values(), key=lambda item: _view_order_key(item._task))
        for item in ordered:
            self._layout.removeWidget(item)
        self._layout.removeWidget(self._section_label)
        self._layout.removeWidget(self._empty_block)
        widgets = [item for item in ordered if not item._task.is_completed]
        completed = [item for item in ordered if item._task.is_completed]
        show_empty = not ordered
        if show_empty:
            self._empty_title.setText("يومك فارغ")
            self._empty_body.setText("ابدأ بمهمة واحدة، ثم اضغط Enter لإضافة التالية.")
            widgets.append(self._empty_block)
        self._empty_block.setVisible(show_empty)
        if completed:
            self._section_label.setText(f"مكتملة • {len(completed)}")
            self._section_label.setIcon(
                vector_icon("caret_down" if self._completed_expanded else "caret_left", "#98A2B3")
            )
            widgets.append(self._section_label)
        widgets.extend(completed)
        insert_at = max(0, self._layout.count() - 1)
        for widget in widgets:
            self._layout.insertWidget(insert_at, widget)
            insert_at += 1
        self._section_label.setVisible(bool(completed))
        for item in completed:
            item.setVisible(self._completed_expanded)
        self._rechain_tab_order()

    def is_completed_expanded(self) -> bool:
        """Current session-only collapse state of the completed group."""
        return self._completed_expanded

    def _focus_sequence(self) -> List[QWidget]:
        """Focusable widgets in visual order: incomplete rows (checkbox,
        title, delete), the group header when completed rows exist, then
        completed rows. Hidden rows are skipped by Qt traversal itself."""
        ordered = sorted(self._items.values(), key=lambda item: _view_order_key(item._task))
        sequence: List[QWidget] = []
        for item in ordered:
            if not item._task.is_completed:
                sequence.extend([item._checkbox, item._text_label, item._delete_btn])
        if any(item._task.is_completed for item in ordered):
            sequence.append(self._section_label)
        for item in ordered:
            if item._task.is_completed:
                sequence.extend([item._checkbox, item._text_label, item._delete_btn])
        return sequence

    def _rechain_tab_order(self) -> None:
        """Explicit keyboard chain through the rows (v3 §11).

        Full window chain: anchor-before, row widgets, anchor-after.
        Pointer-only operation per relayout: no timers, no signals.
        """
        sequence = self._focus_sequence()
        if self._chain_before is not None and sequence:
            sequence = [self._chain_before] + sequence
        if self._chain_after is not None and sequence:
            sequence = sequence + [self._chain_after]
        if not sequence and self._chain_before is not None and self._chain_after is not None:
            sequence = [self._chain_before, self._chain_after]
        previous: Optional[QWidget] = None
        for widget in sequence:
            if previous is not None:
                QWidget.setTabOrder(previous, widget)
            previous = widget

    def set_chain_anchors(
        self, before: Optional[QWidget], after: Optional[QWidget]
    ) -> None:
        """Register window-level widgets surrounding the row chain.

        Called once by the owning window; every relayout re-links through
        them so the chain never goes stale as rows change.
        """
        self._chain_before = before
        self._chain_after = after
        self._rechain_tab_order()

    def tab_chain_ends(self) -> tuple:
        """``(first, last)`` focusable row widgets, or ``(None, None)``.

        Introspection helper (tests / diagnostics); the window-level links
        are maintained through :meth:`set_chain_anchors` instead.
        """
        sequence = self._focus_sequence()
        if not sequence:
            return (None, None)
        return (sequence[0], sequence[-1])

    def set_completed_expanded(self, expanded: bool) -> None:
        """Show or hide completed rows without touching any record or order."""
        self._completed_expanded = bool(expanded)
        self._relayout()

    def _on_group_header_clicked(self) -> None:
        """Toggle completed-row visibility (presentation only)."""
        self.set_completed_expanded(not self._completed_expanded)

    def tasks_snapshot(self) -> List[Task]:
        """Carried tasks for statistics (no DB round trip)."""
        return [item._task for item in self._items.values()]

    def update_task_text(self, task_id: int, new_text: str) -> None:
        """Update the text of a specific task item."""
        item = self._items.get(task_id)
        if item is not None:
            item.update_task_text(new_text)

    def update_task_priority(self, task_id: int, priority: TaskPriority) -> None:
        """Update the priority badge of a specific task item."""
        item = self._items.get(task_id)
        if item is not None:
            item.update_task_priority(priority)

    def update_task_category(self, task_id: int, category_id: str) -> None:
        """Update the carried category of a specific task item in place."""
        item = self._items.get(task_id)
        if item is not None:
            item.update_task_category(category_id)

    def ensure_task_visible(self, task_id: int) -> None:
        """Scroll the row into view once layout settles (no-op for unknown ids).

        The scroll is deferred by a zero-delay single shot because row
        geometry is only valid after the layout pass runs in the event loop;
        scrolling synchronously here would use stale (0, 0) positions. The
        timer is parented to the list so it dies with it (never polling,
        never a recurring timer, never a dangling callback).
        """
        item = self._items.get(task_id)
        if item is None:
            return

        def _scroll_now() -> None:
            current = self._items.get(task_id)
            if current is not None:
                self.ensureWidgetVisible(current)

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(_scroll_now)
        timer.start(0)

    def remove_task(self, task_id: int) -> None:
        """Remove a TaskItem from the visual list."""
        item = self._items.pop(task_id, None)
        if item is not None:
            self._layout.removeWidget(item)
            item.deleteLater()
            self._relayout()

    def clear_tasks(self) -> None:
        """Remove all task items."""
        for item in self._items.values():
            self._layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()
        self._layout.removeWidget(self._section_label)
        self._section_label.setVisible(False)
        self._layout.removeWidget(self._empty_block)
        self._empty_block.setVisible(False)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Show list context menu: dashboard, history, settings, clear completed."""
        menu = QMenu(self)

        dashboard_action = QAction("لوحة التقارير الأسبوعية", menu)
        dashboard_action.triggered.connect(self.dashboard_requested.emit)
        menu.addAction(dashboard_action)

        history_action = QAction("فتح السجل", menu)
        history_action.triggered.connect(self.history_requested.emit)
        menu.addAction(history_action)

        settings_action = QAction("الإعدادات", menu)
        settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        clear_action = QAction("حذف المهام المكتملة", menu)
        clear_action.triggered.connect(self.clear_completed_requested.emit)
        menu.addAction(clear_action)

        menu.exec(event.globalPos())
        event.accept()
