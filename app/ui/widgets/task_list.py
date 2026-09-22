"""Scrollable list container for TaskItem widgets with accessibility."""
from __future__ import annotations

from typing import Dict, Optional, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from app.core.models import Task
from app.ui.widgets.task_item import TaskItem


class TaskList(QScrollArea):
    """Scrollable container managing visual TaskItem instances."""

    task_completed_toggled = Signal(int, bool)  # task_id, is_completed

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("taskListScroll")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
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

    def set_tasks(self, tasks: Sequence[Task]) -> None:
        """Clear existing items and populate with provided tasks."""
        self.clear_tasks()
        for task in tasks:
            self.add_task(task)

    def add_task(self, task: Task) -> None:
        """Append a new TaskItem to the visual list."""
        if task.id is None:
            raise ValueError("Cannot add a task without an ID")

        if task.id in self._items:
            return

        item = TaskItem(task, self._container)
        item.completed_toggled.connect(self.task_completed_toggled.emit)

        # Insert before the trailing stretch item
        stretch_index = max(0, self._layout.count() - 1)
        self._layout.insertWidget(stretch_index, item)
        self._items[task.id] = item

    def remove_task(self, task_id: int) -> None:
        """Remove a TaskItem from the visual list."""
        item = self._items.pop(task_id, None)
        if item is not None:
            self._layout.removeWidget(item)
            item.deleteLater()

    def clear_tasks(self) -> None:
        """Remove all task items."""
        for item in self._items.values():
            self._layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()
