"""Visual representation and interaction for an individual task item."""
from __future__ import annotations

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
from app.ui.priority_presentation import (
    PRIORITY_CHOICES,
    configure_priority_badge,
    label_for,
)


class TaskItem(QFrame):
    """A single task row containing a checkbox, task text, and context menu."""

    completed_toggled = Signal(int, bool)  # task_id, is_completed
    edit_requested = Signal(int)           # task_id
    delete_requested = Signal(int)         # task_id
    priority_change_requested = Signal(int, str)  # task_id, TaskPriority value

    def __init__(self, task: Task, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.task_id = task.id
        self.setObjectName("taskItemFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._priority = task.priority if isinstance(task.priority, TaskPriority) else TaskPriority(task.priority)
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

        # Checkbox first (physical right in RTL), then text, then the badge.
        layout.addWidget(self._checkbox)
        layout.addWidget(self._text_label, 1)

        self._priority_badge = QLabel(self)
        self._priority_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        configure_priority_badge(self._priority_badge, self._priority)
        layout.addWidget(self._priority_badge)

        self._refresh_accessible_description()

    def priority(self) -> TaskPriority:
        return self._priority

    def text(self) -> str:
        return self._text_label.text()

    def _on_toggled(self, checked: bool) -> None:
        self._update_label_style(checked)
        self._refresh_accessible_description()
        if self.task_id is not None:
            self.completed_toggled.emit(self.task_id, checked)

    def _refresh_accessible_description(self) -> None:
        status_text = "مكتملة" if self._checkbox.isChecked() else "غير مكتملة"
        self.setAccessibleDescription(
            f"الحالة: {status_text} • الأولوية: {label_for(self._priority)}"
        )

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
        self._refresh_accessible_description()
        self._checkbox.blockSignals(False)

    def update_task_text(self, new_text: str) -> None:
        """Update visible task text."""
        self._text_label.setText(new_text)
        self.setAccessibleName(f"مهمة: {new_text}")
        self._checkbox.setAccessibleName(f"تحديد إنجاز المهمة: {new_text}")

    def set_priority(self, priority: TaskPriority) -> None:
        """Update the visible priority badge. Does not emit or persist."""
        resolved = priority if isinstance(priority, TaskPriority) else TaskPriority(priority)
        self._priority = resolved
        configure_priority_badge(self._priority_badge, resolved)
        self._refresh_accessible_description()

    def _create_context_menu(self) -> QMenu:
        """Build the task context menu, including the priority section."""
        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        edit_action = QAction("تعديل المهمة", menu)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.task_id))
        menu.addAction(edit_action)

        delete_action = QAction("حذف المهمة", menu)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.task_id))
        menu.addAction(delete_action)

        menu.addSeparator()

        priority_menu = QMenu("الأولوية", menu)
        priority_menu.setObjectName("taskPriorityMenu")
        priority_menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        menu.addMenu(priority_menu)

        group = QActionGroup(priority_menu)
        group.setExclusive(True)

        for priority in PRIORITY_CHOICES:
            action = QAction(label_for(priority), priority_menu)
            action.setCheckable(True)
            action.setData(priority.value)
            action.setChecked(priority == self._priority)
            group.addAction(action)
            priority_menu.addAction(action)
            action.triggered.connect(
                lambda checked=False, selected=priority: self._on_priority_action(selected)
            )

        return menu

    def _on_priority_action(self, priority: TaskPriority) -> None:
        """Request a priority change. Selecting the current value is a no-op."""
        if self.task_id is None or priority == self._priority:
            return
        self.priority_change_requested.emit(self.task_id, priority.value)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Show context menu for editing, priority, or deleting this task."""
        menu = self._create_context_menu()
        menu.exec(event.globalPos())
        event.accept()
        menu.deleteLater()
