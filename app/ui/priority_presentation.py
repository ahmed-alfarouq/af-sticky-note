"""Presentation helpers for TaskPriority.

This is display vocabulary only. Persistence and validation continue to
use the domain enum ``TaskPriority`` — there is no second priority model.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLabel, QWidget

from app.core.models import TaskPriority
from app.ui.styles.app_style import (
    COLOR_CARD_BORDER,
    COLOR_SURFACE,
    COLOR_TEXT_PRIMARY,
)

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


def make_priority_badge(priority: TaskPriority, parent: Optional[QWidget] = None) -> QLabel:
    """Create a badge label configured for ``priority``."""
    badge = QLabel(parent)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    configure_priority_badge(badge, priority)
    return badge


def populate_priority_combo(
    combo: QComboBox,
    selected: TaskPriority = TaskPriority.MEDIUM,
    *,
    compact: bool = False,
) -> None:
    """Fill a combo with the three TaskPriority values and select one.

    Item data is the enum value string (``HIGH`` / ``MEDIUM`` / ``LOW``),
    never a parallel representation.
    """
    resolved = selected if isinstance(selected, TaskPriority) else TaskPriority(selected)
    combo.setObjectName("taskPrioritySelector")
    combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    combo.blockSignals(True)
    combo.clear()
    for priority in PRIORITY_CHOICES:
        combo.addItem(PRIORITY_LABELS_AR[priority], priority.value)
    index = combo.findData(resolved.value)
    combo.setCurrentIndex(index if index >= 0 else 0)
    combo.blockSignals(False)

    if compact:
        combo.setFixedWidth(112)
    else:
        combo.setMinimumWidth(140)
        combo.setMaximumWidth(200)

    view = combo.view()
    if view is not None:
        view.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        # The popup is a separate window, so the main stylesheet may not reach it.
        view.setStyleSheet(
            "background-color: "
            f"{COLOR_SURFACE}; color: {COLOR_TEXT_PRIMARY}; "
            "selection-background-color: #232C3D; selection-color: #FFFFFF; "
            f"border: 1px solid {COLOR_CARD_BORDER}; outline: 0;"
        )


def priority_from_combo(combo: QComboBox) -> TaskPriority:
    """Read the selected TaskPriority from a combo filled by this module."""
    data = combo.currentData()
    return TaskPriority(str(data))
