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
        self.setObjectName("taskInputField")
        # Explicit widget API (not only QSS qproperty): QLineEdit text is
        # anchored by its alignment property (default AlignLeft), while
        # QWidget layout direction does NOT control text layout (Qt docs).
        # AlignRight keeps Arabic, English, mixed, and numeric input starting
        # from the right in this RTL interface; bidi ordering inside each
        # run is untouched.
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setPlaceholderText("+ اكتب مهمة جديدة ثم اضغط Enter...")
        self.setAccessibleName("حقل إدخال مهمة جديدة")
        self.setAccessibleDescription("اكتب نص المهمة واضغط زر الإدخال لإضافتها")
        self.returnPressed.connect(self._on_return_pressed)

    def _on_return_pressed(self) -> None:
        text = self.text()
        # Coordinator manages clearing upon confirmed persistence
        self.task_submitted.emit(text)
