"""Scrollable list container for TaskItem widgets with accessibility."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QContextMenuEvent
from PySide6.QtWidgets import QFrame, QLabel, QMenu, QScrollArea, QVBoxLayout, QWidget

from app.core.models import Category, Task, TaskPriority
from app.ui.category_icons import CategoryIconProvider
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
        self._layout.setContentsMargins(0, 4, 0, 4)
        self._layout.setSpacing(8)
        self._layout.addStretch(1)

        self.setWidget(self._container)
        self._items: Dict[int, TaskItem] = {}
        # Static completed-section label (hidden when nothing is completed).
        # Managed by _relayout; never a task row, never persisted.
        self._section_label = QLabel(self._container)
        self._section_label.setObjectName("completedSectionLabel")
        self._section_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._section_label.setVisible(False)
        # Category choices forwarded to every TaskItem (empty until the
        # coordinator supplies the active list once per UI lifecycle).
        self._categories: List[Category] = []
        self._icon_provider: Optional[CategoryIconProvider] = None

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
        self._items[task.id] = item

    def refresh_task_order(self) -> None:
        """Reposition existing rows after a completion toggle (same widgets).

        Called by the coordinator after persisting the toggle; moves the
        row between the active and completed sections without recreating it.
        """
        self._relayout()

    def _relayout(self) -> None:
        """Order rows (incomplete, section label, completed) before stretch.

        All row widgets are detached first: re-inserting widgets that are
        already laid out would corrupt the trailing-stretch invariant and
        push rows to the bottom (leaving a gap above the list).
        """
        ordered = sorted(self._items.values(), key=lambda item: _view_order_key(item._task))
        for item in ordered:
            self._layout.removeWidget(item)
        self._layout.removeWidget(self._section_label)
        widgets = [item for item in ordered if not item._task.is_completed]
        completed = [item for item in ordered if item._task.is_completed]
        if completed:
            self._section_label.setText(f"مكتملة • {len(completed)}")
            widgets.append(self._section_label)
        widgets.extend(completed)
        insert_at = max(0, self._layout.count() - 1)
        for widget in widgets:
            self._layout.insertWidget(insert_at, widget)
            insert_at += 1
        self._section_label.setVisible(bool(completed))

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
