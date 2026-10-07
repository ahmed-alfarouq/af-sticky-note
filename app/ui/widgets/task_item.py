"""Visual representation and interaction for an individual task item."""
from __future__ import annotations

from dataclasses import replace
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QContextMenuEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QWidget,
)

from app.core.models import Task, TaskPriority
from app.ui.priority_presentation import PRIORITY_LABELS, PRIORITY_ORDER


class TaskItem(QFrame):
    """A single task row containing a checkbox, task text label, and context menu."""

    completed_toggled = Signal(int, bool)  # task_id, is_completed
    edit_requested = Signal(int)           # task_id
    delete_requested = Signal(int)         # task_id
    priority_change_requested = Signal(int, object)  # task_id, TaskPriority

    def __init__(self, task: Task, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.task_id = task.id
        self.setObjectName("taskItemFrame")
        self._task = task
        self._init_ui(task)

    def _init_ui(self, task: Task) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(10)

        self._checkbox = QCheckBox(self)
        self._checkbox.setChecked(task.is_completed)
        self._checkbox.setAccessibleName(f"تحديد إنجاز المهمة: {task.text}")
        self._checkbox.toggled.connect(self._on_toggled)

        self._text_label = QLabel(task.text, self)
        self._text_label.setWordWrap(True)
        self._text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._update_label_style(task.is_completed)

        self.setAccessibleName(f"مهمة: {task.text}")
        status_text = "مكتملة" if task.is_completed else "غير مكتملة"
        self.setAccessibleDescription(f"الحالة: {status_text}")

        layout.addWidget(self._checkbox)
        layout.addWidget(self._text_label, 1)

        self._priority_badge: Optional[QLabel] = None
        self._apply_priority_badge()

    @property
    def priority(self) -> TaskPriority:
        """The priority this row currently shows."""
        return self._task.priority

    @property
    def task_text(self) -> str:
        """The task text currently displayed by this row."""
        return self._text_label.text()

    def _apply_priority_badge(self) -> None:
        """Show the priority badge for HIGH / LOW; MEDIUM stays badge-free.

        Priority is deliberately secondary to the task text, so the neutral
        MEDIUM case adds no visual noise at all.
        """
        priority = self._task.priority
        if priority not in (TaskPriority.HIGH, TaskPriority.LOW):
            if self._priority_badge is not None:
                self._priority_badge.deleteLater()
                self._priority_badge = None
            return

        if self._priority_badge is None:
            self._priority_badge = QLabel(self)
            layout = self.layout()
            if layout is not None:
                layout.addWidget(self._priority_badge)

        self._priority_badge.setText(PRIORITY_LABELS[priority])
        self._priority_badge.setObjectName(
            "priorityBadgeHigh" if priority == TaskPriority.HIGH else "priorityBadgeLow"
        )
        self._priority_badge.style().unpolish(self._priority_badge)
        self._priority_badge.style().polish(self._priority_badge)

    def update_task_priority(self, priority: TaskPriority) -> None:
        """Refresh the row for a new priority without recreating the task.

        Only the priority field changes: the record keeps its id, day, source
        task, completion state, text and position.
        """
        self._task = replace(self._task, priority=priority)
        self._apply_priority_badge()

    def _on_toggled(self, checked: bool) -> None:
        self._update_label_style(checked)
        status_text = "مكتملة" if checked else "غير مكتملة"
        self.setAccessibleDescription(f"الحالة: {status_text}")
        self.completed_toggled.emit(self.task_id, checked)

    def _update_label_style(self, is_completed: bool) -> None:
        if is_completed:
            self._text_label.setObjectName("taskTextLabelCompleted")
        else:
            self._text_label.setObjectName("taskTextLabel")
        self._text_label.style().unpolish(self._text_label)
        self._text_label.style().polish(self._text_label)

    def set_completed_silently(self, is_completed: bool) -> None:
        """Update checkbox state without re-emitting toggled signal."""
        self._checkbox.blockSignals(True)
        self._checkbox.setChecked(is_completed)
        self._update_label_style(is_completed)
        self._checkbox.blockSignals(False)

    def update_task_text(self, new_text: str) -> None:
        """Update visible task text."""
        self._text_label.setText(new_text)
        # Keep the carried Task in step so a later priority update cannot
        # resurrect the old text.
        self._task = replace(self._task, text=new_text)
        self.setAccessibleName(f"مهمة: {new_text}")

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Show context menu for editing, changing priority, or deleting."""
        menu = QMenu(self)

        edit_action = QAction("تعديل المهمة", menu)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.task_id))
        menu.addAction(edit_action)

        # Priority submenu: checkable actions, current priority checked.
        priority_menu = QMenu("الأولوية", menu)
        priority_group = QActionGroup(menu)
        priority_group.setExclusive(True)

        for priority in PRIORITY_ORDER:
            action = QAction(PRIORITY_LABELS[priority], priority_menu)
            action.setCheckable(True)
            action.setChecked(priority == self._task.priority)
            action.setData(priority)
            action.triggered.connect(
                lambda checked=False, p=priority: self.priority_change_requested.emit(
                    self.task_id, p
                )
            )
            priority_group.addAction(action)
            priority_menu.addAction(action)

        menu.addMenu(priority_menu)

        delete_action = QAction("حذف المهمة", menu)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.task_id))
        menu.addAction(delete_action)

        menu.exec(event.globalPos())
        event.accept()
