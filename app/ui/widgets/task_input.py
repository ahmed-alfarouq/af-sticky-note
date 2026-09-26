"""Task input row: text field plus a compact priority selector."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QWidget

from app.core.models import TaskPriority
from app.ui.priority_presentation import populate_priority_combo, priority_from_combo


class TaskInput(QWidget):
    """Bottom input row for adding a task.

    MEDIUM (عادي) is the initial selection. Enter in the text field submits
    the current text together with the selected priority. The selector is a
    compact accessory; it does not turn the row into a form.
    """

    # raw text, TaskPriority value ("LOW" / "MEDIUM" / "HIGH")
    task_submitted = Signal(str, str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("taskInputRow")
        # Widget direction, not layout.setLayoutDirection().
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setAutoFillBackground(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._line_edit = QLineEdit(self)
        self._line_edit.setObjectName("taskInputField")
        self._line_edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._line_edit.setPlaceholderText("+ اكتب مهمة جديدة...")
        self._line_edit.setAccessibleName("حقل إدخال مهمة جديدة")
        self._line_edit.setAccessibleDescription("اكتب نص المهمة واضغط زر الإدخال لإضافتها")
        self._line_edit.returnPressed.connect(self._on_return_pressed)

        self._priority_combo = QComboBox(self)
        self._priority_combo.setAccessibleName("أولوية المهمة الجديدة")
        self._priority_combo.setAccessibleDescription("اختر عاجل أو عادي أو منخفض. الافتراضي عادي")
        self._priority_combo.setToolTip("أولوية المهمة")
        populate_priority_combo(self._priority_combo, TaskPriority.MEDIUM, compact=True)
        # After the user picks a priority, return to the text field so Enter submits.
        self._priority_combo.activated.connect(self._return_focus_to_text)

        # RTL: first widget sits on the physical right (the typing field).
        # The compact selector is the accessory on the physical left.
        layout.addWidget(self._line_edit, 1)
        layout.addWidget(self._priority_combo, 0)

    def _on_return_pressed(self) -> None:
        self.task_submitted.emit(self.text(), self.priority().value)

    def _return_focus_to_text(self, _index: int = 0) -> None:
        self._line_edit.setFocus()

    def text(self) -> str:
        return self._line_edit.text()

    def setText(self, text: str) -> None:  # noqa: N802 — Qt naming
        self._line_edit.setText(text)

    def clear(self) -> None:
        """Clear entered text. Priority selection is left unchanged."""
        self._line_edit.clear()

    def priority(self) -> TaskPriority:
        return priority_from_combo(self._priority_combo)

    def set_priority(self, priority: TaskPriority) -> None:
        populate_priority_combo(self._priority_combo, priority, compact=True)

    def reset_priority(self) -> None:
        """Return the selector to the neutral default."""
        self.set_priority(TaskPriority.MEDIUM)

    def setFocus(self, reason: Qt.FocusReason = Qt.FocusReason.OtherFocusReason) -> None:  # noqa: N802
        self._line_edit.setFocus(reason)
