"""Presentation helpers for TaskPriority.

This is display vocabulary only. Persistence and validation continue to
use the domain enum ``TaskPriority`` — there is no second priority model.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from app.core.models import TaskPriority

# User-facing Arabic labels. MEDIUM is the neutral/default wording.
PRIORITY_LABELS_AR = {
    TaskPriority.HIGH: "عاجل",
    TaskPriority.MEDIUM: "عادي",
    TaskPriority.LOW: "منخفض",
}

# Selector and menu order: urgent, normal, low.
PRIORITY_CHOICES = (
    TaskPriority.HIGH,
    TaskPriority.MEDIUM,
    TaskPriority.LOW,
)


def label_for(priority: TaskPriority) -> str:
    """Return the Arabic label for a priority value."""
    resolved = priority if isinstance(priority, TaskPriority) else TaskPriority(priority)
    return PRIORITY_LABELS_AR[resolved]


def configure_priority_badge(badge: QLabel, priority: TaskPriority) -> None:
    """Show the existing HIGH/LOW badge, or hide it for neutral MEDIUM.

    Visual language is unchanged from v0.5.0:
    HIGH → "عاجل", LOW → "منخفض", MEDIUM → no badge.
    """
    resolved = priority if isinstance(priority, TaskPriority) else TaskPriority(priority)
    if resolved is TaskPriority.HIGH:
        badge.setText(PRIORITY_LABELS_AR[TaskPriority.HIGH])
        badge.setObjectName("priorityBadgeHigh")
        badge.setVisible(True)
    elif resolved is TaskPriority.LOW:
        badge.setText(PRIORITY_LABELS_AR[TaskPriority.LOW])
        badge.setObjectName("priorityBadgeLow")
        badge.setVisible(True)
    else:
        badge.clear()
        badge.setObjectName("priorityBadgeMedium")
        badge.setVisible(False)
    style = badge.style()
    if style is not None:
        style.unpolish(badge)
        style.polish(badge)



