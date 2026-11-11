"""Task input field widget with accessibility and visual indicators."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLineEdit, QWidget

__all__ = ["TaskInput", "PLACEHOLDER_TEXT"]

PLACEHOLDER_TEXT = "اكتب مهمة جديدة..."


class TaskInput(QLineEdit):
    """Line edit specialized for adding sticky note tasks."""

    task_submitted = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("taskInputField")
        self.setPlaceholderText(PLACEHOLDER_TEXT)
        self.setAccessibleName("مهمة جديدة")
        self.setAccessibleDescription("اكتب نص المهمة واضغط زر الإدخال لإضافتها")
        self.returnPressed.connect(self._on_return_pressed)

    def _on_return_pressed(self) -> None:
        # The coordinator clears the field only after the task is persisted.
        self.task_submitted.emit(self.text())