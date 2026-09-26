"""Task input row: dominant text field plus a compact priority control."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from app.core.models import TaskPriority
from app.ui.layout_metrics import INPUT_GAP
from app.ui.widgets.priority_selector import PrioritySelector


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
        self.setObjectName("taskInputRow")
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setAutoFillBackground(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(INPUT_GAP)

        self._line_edit = QLineEdit(self)
        self._line_edit.setObjectName("taskInputField")
        self._line_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._line_edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        # Physical right padding. Not mirrored by stylesheet RTL.
        self._line_edit.setTextMargins(12, 0, 14, 0)
        self._line_edit.setPlaceholderText("اكتب مهمة جديدة...")
        self._line_edit.setAccessibleName("حقل إدخال مهمة جديدة")
        self._line_edit.setAccessibleDescription("اكتب نص المهمة واضغط زر الإدخال لإضافتها")
        self._line_edit.returnPressed.connect(self._on_return_pressed)

        self._priority_selector = PrioritySelector(TaskPriority.MEDIUM, self)
        self._priority_selector.menu().triggered.connect(self._return_focus_to_text)

        # Physical left → right: selector, then the dominant field.
        layout.addWidget(self._priority_selector, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._line_edit, 1)

        self.setTabOrder(self._line_edit, self._priority_selector)

    def _on_return_pressed(self) -> None:
        self.task_submitted.emit(self.text(), self.priority().value)

    def _return_focus_to_text(self, *_args) -> None:
        self._line_edit.setFocus()

    def text(self) -> str:
        return self._line_edit.text()

    def setText(self, text: str) -> None:  # noqa: N802 — Qt naming
        self._line_edit.setText(text)

    def clear(self) -> None:
        """Clear entered text. Priority selection is left unchanged."""
        self._line_edit.clear()

    def priority(self) -> TaskPriority:
        return self._priority_selector.priority()

    def set_priority(self, priority: TaskPriority) -> None:
        self._priority_selector.set_priority(priority)

    def reset_priority(self) -> None:
        """Return the selector to the neutral default."""
        self.set_priority(TaskPriority.MEDIUM)

    def setFocus(self, reason: Qt.FocusReason = Qt.FocusReason.OtherFocusReason) -> None:  # noqa: N802
        self._line_edit.setFocus(reason)
