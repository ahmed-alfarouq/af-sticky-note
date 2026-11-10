"""The Arabic presentation of task priority -- with no Qt dependency at all.

This is the single boundary between the ``TaskPriority`` domain enum and what
the user sees: label, one-line hint, and color. It deliberately contains no
Qt imports so that the mapping can be used (and tested) everywhere, including
the backend suite that runs without PySide6 installed.

No Arabic label is ever stored in the database; the enum value is what is
persisted.

Levels, most urgent first: HIGH = "عاجل", MEDIUM = "متوسط", LOW = "عادي".
"عادي" (LOW) is the everyday level with no special priority, so it is the
default for new tasks in the UI.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from app.core.models import TaskPriority

PRIORITY_LABELS: Dict[TaskPriority, str] = {
    TaskPriority.HIGH: "عاجل",
    TaskPriority.MEDIUM: "متوسط",
    TaskPriority.LOW: "عادي",
}

#: One-line explanation shown under each label in the priority picker.
PRIORITY_HINTS: Dict[TaskPriority, str] = {
    TaskPriority.HIGH: "يظهر أولاً في القائمة",
    TaskPriority.MEDIUM: "مهم لكن غير مستعجل",
    TaskPriority.LOW: "بدون أولوية خاصة",
}

#: The one color of each level (dots in the task row, picker, and chip).
PRIORITY_COLORS: Dict[TaskPriority, str] = {
    TaskPriority.HIGH: "#f08a6c",
    TaskPriority.MEDIUM: "#f0b24a",
    TaskPriority.LOW: "#5b8fd6",
}

#: Display order: most urgent first.
PRIORITY_ORDER: Tuple[TaskPriority, ...] = (
    TaskPriority.HIGH,
    TaskPriority.MEDIUM,
    TaskPriority.LOW,
)

#: Priority a new task starts with in the UI.
DEFAULT_TASK_PRIORITY = TaskPriority.LOW


def priority_label(priority: Optional[TaskPriority]) -> str:
    """Return the Arabic label for ``priority`` (default level when unknown)."""
    if isinstance(priority, TaskPriority):
        return PRIORITY_LABELS[priority]
    return PRIORITY_LABELS[DEFAULT_TASK_PRIORITY]