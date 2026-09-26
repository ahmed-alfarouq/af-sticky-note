"""Visual representation and interaction for an individual task item."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QContextMenuEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QWidget,
)

from app.core.models import Task


class TaskItem(QFrame):
    """A single task row containing a checkbox, task text label, and context menu."""

    completed_toggled = Signal(int, bool)  # task_id, is_completed
    edit_requested = Signal(int)           # task_id
    delete_requested = Signal(int)         # task_id

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

        # Checkbox first on the right in RTL, followed by text next to it
        layout.addWidget(self._checkbox)
        layout.addWidget(self._text_label, 1)

        # Subtle, restrained priority indicator if high or low
        if task.priority and task.priority.value == "HIGH":
            self._priority_badge = QLabel("عاجل", self)
            self._priority_badge.setObjectName("priorityBadgeHigh")
            layout.addWidget(self._priority_badge)
        elif task.priority and task.priority.value == "LOW":
            self._priority_badge = QLabel("منخفض", self)
            self._priority_badge.setObjectName("priorityBadgeLow")
            layout.addWidget(self._priority_badge)

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
        self.setAccessibleName(f"مهمة: {new_text}")

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Show context menu for editing or deleting this specific task."""
        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        edit_action = QAction("تعديل المهمة", menu)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.task_id))
        menu.addAction(edit_action)

        delete_action = QAction("حذف المهمة", menu)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.task_id))
        menu.addAction(delete_action)

        menu.exec(event.globalPos())
        event.accept()
