"""Task input row: dominant text field plus a compact priority control."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from app.core.models import TaskPriority
from app.ui.layout_metrics import INPUT_GAP
from app.ui.widgets.priority_selector import PrioritySelector

__all__ = ["TaskInput", "PLACEHOLDER_TEXT"]

PLACEHOLDER_TEXT = "اكتب مهمة جديدة..."


class TaskInput(QWidget):
    """Bottom entry row.

    Physical placement is explicit and independent of application RTL:
    the text field is on the right, the priority control is the compact
    accessory on the left. The field itself is RTL so Arabic placeholder
    and typed text start on the right.
    """

    # raw text, TaskPriority value ("LOW" / "MEDIUM" / "HIGH")
    task_submitted = Signal(str, str)

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
