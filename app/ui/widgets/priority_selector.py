"""Compact priority control: one button, one Arabic label, one menu.

A QComboBox drop-down paints as a separate native box under RTL and
looks detached from its label. A tool button with an instant menu keeps
the current value (عاجل / عادي / منخفض) inside a single Daily Sticky control.
"""
from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QSizePolicy, QToolButton, QWidget

from app.core.models import TaskPriority
from app.ui.priority_presentation import PRIORITY_CHOICES, label_for


class PrioritySelector(QToolButton):
    """Shows the current TaskPriority and lets the user pick another."""

    def __init__(
        self,
        selected: TaskPriority = TaskPriority.MEDIUM,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("taskPriorityButton")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        # Text direction only. Physical placement is decided by the parent row.
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAccessibleName("أولوية المهمة")
        self.setAccessibleDescription("اختر عاجل أو عادي أو منخفض. الافتراضي عادي")
        self.setToolTip("أولوية المهمة")

        self._priority = TaskPriority.MEDIUM
        self._menu = QMenu(self)
        self._menu.setObjectName("taskPriorityMenu")
        self._menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMenu(self._menu)

        self._group = QActionGroup(self._menu)
        self._group.setExclusive(True)
        self._actions: Dict[TaskPriority, QAction] = {}
        for priority in PRIORITY_CHOICES:
            action = QAction(label_for(priority), self._menu)
            action.setCheckable(True)
            action.setData(priority.value)
            self._group.addAction(action)
            self._menu.addAction(action)
            action.triggered.connect(
                lambda checked=False, chosen=priority: self.set_priority(chosen)
            )
            self._actions[priority] = action

        self.set_priority(selected)

    def priority(self) -> TaskPriority:
        return self._priority

    def set_priority(self, priority: TaskPriority) -> None:
        resolved = priority if isinstance(priority, TaskPriority) else TaskPriority(priority)
        self._priority = resolved
        # Chevron is part of the label, not a separate drop-down box.
        self.setText(f"{label_for(resolved)}  ▾")
        self._actions[resolved].setChecked(True)
