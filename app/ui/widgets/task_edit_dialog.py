"""Dialog for editing an existing task's text and priority (Phase 5I / 6D).

Ensures proper Arabic RTL layout, styled inputs, and validation.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.models import TaskPriority
from app.ui.widgets.priority_selector import PrioritySelector


class TaskEditDialog(QDialog):
    """Modal dialog for editing a task's text and priority."""

    def __init__(
        self,
        initial_text: str,
        parent: Optional[QWidget] = None,
        initial_priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("تعديل المهمة")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setModal(True)
        self.resize(320, 180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title_label = QLabel("نص المهمة:", self)
        title_label.setObjectName("taskEditLabel")
        layout.addWidget(title_label)

        self._input_field = QLineEdit(self)
        self._input_field.setObjectName("taskInputField")
        self._input_field.setText(initial_text)
        self._input_field.selectAll()
        layout.addWidget(self._input_field)

        priority_label = QLabel("الأولوية:", self)
        priority_label.setObjectName("taskEditLabel")
        layout.addWidget(priority_label)

        self._priority_selector = PrioritySelector(self)
        # Opens with the task's current priority already selected.
        self._priority_selector.set_priority(initial_priority)
        layout.addWidget(self._priority_selector)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self._save_btn = QPushButton("حفظ", self)
        self._save_btn.setObjectName("saveButton")
        self._save_btn.clicked.connect(self.accept)

        self._cancel_btn = QPushButton("إلغاء", self)
        self._cancel_btn.setObjectName("cancelButton")
        self._cancel_btn.clicked.connect(self.reject)

        button_row.addStretch(1)
        button_row.addWidget(self._save_btn)
        button_row.addWidget(self._cancel_btn)

        layout.addLayout(button_row)
        self._input_field.returnPressed.connect(self.accept)

    def get_text(self) -> str:
        """Return the trimmed edited text."""
        return self._input_field.text().strip()

    def get_priority(self) -> TaskPriority:
        """Return the priority chosen in the dialog."""
        return self._priority_selector.selected_priority()
