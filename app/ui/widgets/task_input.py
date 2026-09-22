"""Task input field widget with accessibility and visual indicators."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLineEdit, QWidget


class TaskInput(QLineEdit):
    """Line edit specialized for adding sticky note tasks."""

    task_submitted = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setObjectName("taskInputField")
        # Prepend Unicode Right-To-Left Mark (\u200F) so neutral prefix '+' anchors to the right
        self.setPlaceholderText("\u200F+ اكتب مهمة جديدة ثم اضغط Enter...")
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setAccessibleName("حقل إدخال مهمة جديدة")
        self.setAccessibleDescription("اكتب نص المهمة واضغط زر الإدخال لإضافتها")
        self.returnPressed.connect(self._on_return_pressed)

    def _on_return_pressed(self) -> None:
        text = self.text()
        # Coordinator manages clearing upon confirmed persistence
        self.task_submitted.emit(text)
