"""Scrollable, transparent vertical stack of task rows.

Order, identical on every screen:

  1. special block (empty-day state, or the all-done banner),
  2. open tasks,
  3. the "مكتملة · N" group header,
  4. completed tasks.

The list has no background, border, or title; rows and the header are
separated by ``LIST_ITEM_SPACING``. The add bar lives outside this widget.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QContextMenuEvent
from PySide6.QtWidgets import QFrame, QMenu, QScrollArea, QVBoxLayout, QWidget

from app.core.models import Category, Task, TaskPriority
from app.ui.category_icons import CategoryIconProvider
from app.ui.styles.task_list_style import LIST_ITEM_SPACING
from app.ui.widgets.task_item import TaskItem
from app.ui.widgets.task_list.all_done_banner import AllDoneBanner
from app.ui.widgets.task_list.completed_header import CompletedGroupHeader
from app.ui.widgets.task_list.empty_state import EmptyState
from app.ui.widgets.task_list.focus_chain import apply_tab_order, build_focus_sequence
from app.ui.widgets.task_list.ordering import split_rows, view_order_key

__all__ = ["TaskList"]


class TaskList(QScrollArea):
    """Scrollable container managing visual TaskItem instances."""

    task_completed_toggled = Signal(int, bool)            # task_id, is_completed
    task_edit_requested = Signal(int)                     # task_id
    task_delete_requested = Signal(int)                   # task_id
    task_priority_change_requested = Signal(int, object)  # task_id, TaskPriority
    task_category_change_requested = Signal(int, str)     # task_id, category_id
    task_inline_edit_committed = Signal(int, str)         # task_id, trimmed new text
    clear_completed_requested = Signal()
    history_requested = Signal()
    dashboard_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("taskListScroll")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.viewport().setAutoFillBackground(False)
        # Rows elide long titles, so a horizontal scrollbar is never needed.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # The scroll area itself is never a tab stop.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAccessibleName("قائمة مهام اليوم")
        self.setAccessibleDescription("عرض المهام اليومية مع إمكانية تحديد إنجازها")

        self._container = QWidget(self)
        self._container.setObjectName("taskListContainer")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(LIST_ITEM_SPACING)
        self._layout.addStretch(1)  # trailing spacer; always the last item
        self.setWidget(self._container)

        self._items: Dict[int, TaskItem] = {}

        self._header = CompletedGroupHeader(self._container)
        self._header.clicked.connect(self._on_group_header_clicked)
        self._banner = AllDoneBanner(self._container)
        self._empty = EmptyState(self._container)
        for block in (self._header, self._banner, self._empty):
            block.setVisible(False)

        self._categories: List[Category] = []
        self._icon_provider: Optional[CategoryIconProvider] = None
        self._read_only = False
        # Session-only collapse state: hiding rows never touches records.
        self._completed_expanded = True
        # Window-level tab-chain anchors, registered once by the window.
        self._chain_before: Optional[QWidget] = None
        self._chain_after: Optional[QWidget] = None

    # -- Configuration ------------------------------------------------------

    def set_categories(
        self,
        categories: Sequence[Category],
        icon_provider: Optional[CategoryIconProvider] = None,
    ) -> None:
        """Supply category choices (and icons) for all rows."""
        self._categories = list(categories)
        if icon_provider is not None:
            self._icon_provider = icon_provider
        for item in self._items.values():
            item.set_categories(self._categories, self._icon_provider)

    def set_read_only(self, read_only: bool) -> None:
        """Past-day mode: read-only rows and no all-done banner."""
        if read_only == self._read_only:
            return
        self._read_only = read_only
        for item in self._items.values():
            item.set_read_only(read_only)
        self._relayout()

    def is_read_only(self) -> bool:
        return self._read_only

    def set_chain_anchors(
        self, before: Optional[QWidget], after: Optional[QWidget]
    ) -> None:
        """Register the window widgets surrounding the row tab chain."""
        self._chain_before = before
        self._chain_after = after
        self._rechain_tab_order()

    # -- Content ------------------------------------------------------------

    def set_tasks(self, tasks: Sequence[Task]) -> None:
        """Replace all rows (view order only; stored positions untouched)."""
        self.clear_tasks()
        for task in sorted(tasks, key=view_order_key):
            self._add_item(task)
        self._relayout()

    def add_task(self, task: Task) -> None:
        if task.id is None:
            raise ValueError("Cannot add a task without an ID")
        if task.id in self._items:
            return
        self._add_item(task)
        self._relayout()

    def remove_task(self, task_id: int) -> None:
        item = self._items.pop(task_id, None)
        if item is not None:
            self._layout.removeWidget(item)
            item.deleteLater()
            self._relayout()

    def clear_tasks(self) -> None:
        for item in self._items.values():
            self._layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()
        for block in (self._header, self._banner, self._empty):
            self._layout.removeWidget(block)
            block.setVisible(False)

    def refresh_task_order(self) -> None:
        """Reposition rows after a completion toggle (same widgets)."""
        self._relayout()

    def item_for(self, task_id: Optional[int]) -> Optional[TaskItem]:
        """The on-screen row for ``task_id``, if any."""
        return self._items.get(task_id) if task_id is not None else None

    def tasks_snapshot(self) -> List[Task]:
        """Carried tasks for statistics (no DB round trip)."""
        return [item.task for item in self._items.values()]

    def update_task_text(self, task_id: int, new_text: str) -> None:
        item = self.item_for(task_id)
        if item is not None:
            item.update_task_text(new_text)

    def update_task_priority(self, task_id: int, priority: TaskPriority) -> None:
        item = self.item_for(task_id)
        if item is not None:
            item.update_task_priority(priority)

    def update_task_category(self, task_id: int, category_id: str) -> None:
        item = self.item_for(task_id)
        if item is not None:
            item.update_task_category(category_id)

    def _add_item(self, task: Task) -> None:
        assert task.id is not None
        item = TaskItem(
            task,
            self._container,
            self._categories,
            self._icon_provider,
            read_only=self._read_only,
        )
        item.completed_toggled.connect(self.task_completed_toggled.emit)
        item.edit_requested.connect(self.task_edit_requested.emit)
        item.delete_requested.connect(self.task_delete_requested.emit)
        item.priority_change_requested.connect(self.task_priority_change_requested.emit)
        item.category_change_requested.connect(self.task_category_change_requested.emit)
        item.inline_edit_committed.connect(self.task_inline_edit_committed.emit)
        self._items[task.id] = item

    # -- Completed group ----------------------------------------------------

    def is_completed_expanded(self) -> bool:
        return self._completed_expanded

    def set_completed_expanded(self, expanded: bool) -> None:
        """Show or hide completed rows without touching records or order."""
        self._completed_expanded = bool(expanded)
        self._relayout()

    def _on_group_header_clicked(self) -> None:
        self.set_completed_expanded(not self._completed_expanded)

    # -- Layout -------------------------------------------------------------

    def _relayout(self) -> None:
        """Place blocks in order, ahead of the trailing spacer.

        Everything is detached first: re-inserting widgets that are already
        laid out would corrupt the trailing-spacer invariant and push rows
        to the bottom.
        """
        open_rows, done_rows = split_rows(self._items.values())
        show_empty = not self._items
        show_banner = bool(done_rows) and not open_rows and not self._read_only

        for widget in (*self._items.values(), self._header, self._banner, self._empty):
            self._layout.removeWidget(widget)

        blocks: List[QWidget] = []
        if show_empty:
            blocks.append(self._empty)
        if show_banner:
            blocks.append(self._banner)
        blocks.extend(open_rows)
        if done_rows:
            self._header.set_state(len(done_rows), self._completed_expanded)
            blocks.append(self._header)
            blocks.extend(done_rows)

        for index, widget in enumerate(blocks):
            stretch = 1 if widget is self._empty else 0
            self._layout.insertWidget(index, widget, stretch)

        # The empty state fills the space (centered); otherwise the trailing
        # spacer pushes rows to the top.
        self._layout.setStretch(self._layout.count() - 1, 0 if show_empty else 1)

        for block in (self._header, self._banner, self._empty):
            block.setVisible(block in blocks)
        for row in open_rows:
            row.setVisible(True)
        for row in done_rows:
            row.setVisible(self._completed_expanded)

        self._rechain_tab_order(open_rows, done_rows)

    def _rechain_tab_order(
        self,
        open_rows: Optional[Sequence[TaskItem]] = None,
        done_rows: Optional[Sequence[TaskItem]] = None,
    ) -> None:
        if open_rows is None or done_rows is None:
            open_rows, done_rows = split_rows(self._items.values())
        sequence = build_focus_sequence(open_rows, done_rows, self._header)
        apply_tab_order(sequence, self._chain_before, self._chain_after)

    def tab_chain_ends(self) -> tuple:
        """``(first, last)`` focusable row widgets, or ``(None, None)``."""
        open_rows, done_rows = split_rows(self._items.values())
        sequence = build_focus_sequence(open_rows, done_rows, self._header)
        if not sequence:
            return (None, None)
        return (sequence[0], sequence[-1])

    # -- Scrolling ----------------------------------------------------------

    def ensure_task_visible(self, task_id: int) -> None:
        """Scroll the row into view once layout has settled.

        Deferred by a zero-delay single-shot timer because row geometry is
        only valid after the layout pass; the timer deletes itself.
        """
        if self.item_for(task_id) is None:
            return

        def scroll_now() -> None:
            current = self.item_for(task_id)
            if current is not None:
                self.ensureWidgetVisible(current)

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(scroll_now)
        timer.timeout.connect(timer.deleteLater)
        timer.start(0)

    # -- Context menu -------------------------------------------------------

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802
        """List menu: dashboard, history, settings, clear completed."""
        menu = QMenu(self)

        def add(text: str, signal: Signal) -> None:
            action = QAction(text, menu)
            action.triggered.connect(signal.emit)
            menu.addAction(action)

        add("لوحة التقارير الأسبوعية", self.dashboard_requested)
        add("فتح السجل", self.history_requested)
        add("الإعدادات", self.settings_requested)
        menu.addSeparator()
        add("حذف المهام المكتملة", self.clear_completed_requested)

        menu.exec(event.globalPos())
        event.accept()
