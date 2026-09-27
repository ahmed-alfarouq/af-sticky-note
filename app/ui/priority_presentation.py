"""The Arabic presentation of task priority -- with no Qt dependency at all.

This is the single boundary between the ``TaskPriority`` domain enum and the
labels the user sees. It deliberately contains no Qt imports so that the
mapping can be used (and tested) everywhere, including the backend suite that
runs without PySide6 installed.

No Arabic label is ever stored in the database; the enum value is what is
persisted.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from app.core.models import TaskPriority

#: The Arabic label for each priority. MEDIUM reads as an explicit "عادي" so
#: the user always sees a value, even though a MEDIUM task deliberately carries
#: no badge in the task row -- priority must stay secondary to the task text.
PRIORITY_LABELS: Dict[TaskPriority, str] = {
    TaskPriority.HIGH: "عاجل",
    TaskPriority.MEDIUM: "عادي",
    TaskPriority.LOW: "منخفض",
}

#: Display order: most urgent first.
PRIORITY_ORDER: Tuple[TaskPriority, ...] = (
    TaskPriority.HIGH,
    TaskPriority.MEDIUM,
    TaskPriority.LOW,
)


def priority_label(priority: Optional[TaskPriority]) -> str:
    """Return the Arabic label for ``priority`` (MEDIUM when unknown)."""
    if isinstance(priority, TaskPriority):
        return PRIORITY_LABELS[priority]
    return PRIORITY_LABELS[TaskPriority.MEDIUM]
