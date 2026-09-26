"""Dialog for editing an existing task's text and priority.

Arabic RTL layout. Enter saves, Escape cancels, and empty text is rejected
without writing anything.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.models import TaskPriority
from app.ui.priority_presentation import populate_priority_combo, priority_from_combo
from app.ui.styles.app_style import get_application_stylesheet


class TaskEditDialog(QDialog):
    """Modal dialog for editing a task's text and priority together."""

    def __init__(
        self,
        initial_text: str,
        initial_priority: TaskPriority = TaskPriority.MEDIUM,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("taskEditDialog")
        self.setWindowTitle("تعديل المهمة")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setModal(True)
        self.setMinimumWidth(340)
        self.setStyleSheet(get_application_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title_label = QLabel("نص المهمة:", self)
        title_label.setObjectName("taskEditLabel")
        layout.addWidget(title_label)

        self._input_field = QLineEdit(self)
        self._input_field.setObjectName("taskInputField")
        self._input_field.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._input_field.setText(initial_text)
        self._input_field.setAccessibleName("نص المهمة")
        self._input_field.selectAll()
        layout.addWidget(self._input_field)

        priority_label = QLabel("الأولوية:", self)
        priority_label.setObjectName("taskEditLabel")

        self._priority_combo = QComboBox(self)
        self._priority_combo.setAccessibleName("أولوية المهمة")
        self._priority_combo.setToolTip("أولوية المهمة")
        populate_priority_combo(self._priority_combo, initial_priority, compact=False)

        priority_row = QHBoxLayout()
        priority_row.setSpacing(8)
        priority_row.addWidget(priority_label)
        priority_row.addWidget(self._priority_combo)
        priority_row.addStretch(1)
        layout.addLayout(priority_row)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self._save_btn = QPushButton("حفظ", self)
        self._save_btn.setObjectName("saveButton")
        self._save_btn.setDefault(True)
        self._save_btn.setAutoDefault(True)
        self._save_btn.clicked.connect(self.accept)

        self._cancel_btn = QPushButton("إلغاء", self)
        self._cancel_btn.setObjectName("cancelButton")
        self._cancel_btn.setAutoDefault(False)
        self._cancel_btn.clicked.connect(self.reject)

        button_row.addStretch(1)
        button_row.addWidget(self._save_btn)
        button_row.addWidget(self._cancel_btn)
        layout.addLayout(button_row)

        self._input_field.returnPressed.connect(self.accept)
        self.adjustSize()

    def accept(self) -> None:
        """Save only when the text is non-empty. Otherwise keep the dialog open."""
        if not self.get_text():
            self._input_field.setFocus()
            self._input_field.selectAll()
            return
        super().accept()

    def get_text(self) -> str:
        """Return the trimmed edited text."""
        return self._input_field.text().strip()

    def get_priority(self) -> TaskPriority:
        """Return the priority currently selected in the dialog."""
        return priority_from_combo(self._priority_combo)
