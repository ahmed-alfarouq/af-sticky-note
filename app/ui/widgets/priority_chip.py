"""Priority chip (colored dot + label).

Shows the priority chosen for the next task. Like :class:`CategoryChip`, it
only holds the selection; the window presents the priority sheet when the
chip asks (``open_requested``).
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from app.core.models import TaskPriority
from app.ui.priority_presentation import (
    DEFAULT_TASK_PRIORITY,
    PRIORITY_COLORS,
    priority_label,
)
from app.ui.widgets.picker_chip import PickerChip
from app.ui.widgets.priority_dot import PriorityDot

__all__ = ["PriorityChip"]


class PriorityChip(PickerChip):
    """Dot + label button exposing :class:`TaskPriority` values."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        dot = PriorityDot(PRIORITY_COLORS[DEFAULT_TASK_PRIORITY])
        super().__init__("priorityChip", "الأولوية", dot, parent)
        self._dot = dot
        self._priority = DEFAULT_TASK_PRIORITY
        self._refresh()

    def selected_priority(self) -> TaskPriority:
        return self._priority

    def set_priority(self, priority: Optional[TaskPriority]) -> None:
        """Select ``priority`` (default level for None/unknown). No signals."""
        self._priority = (
            priority if isinstance(priority, TaskPriority) else DEFAULT_TASK_PRIORITY
        )
        self._refresh()

    def _refresh(self) -> None:
        label = priority_label(self._priority)
        self._dot.set_color(PRIORITY_COLORS[self._priority])
        self._set_text(label)
        self.setToolTip(label)
        self.setAccessibleName(f"الأولوية: {label}")