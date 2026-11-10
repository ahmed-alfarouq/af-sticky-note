"""Shared mechanics of the dock picker chips (category, priority).

A compact button: leading marker + label + caret. It holds no options and
opens nothing itself: pressing it (click, Space, Enter, Down) emits
``open_requested`` and the window presents the sheet. Hover, focus and
open states are code-driven properties styled in ``option_sheet_style``.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from app.ui.icons import icon as vector_icon

__all__ = ["PickerChip"]

_CARET_COLOR = "#98A2B3"
_OPEN_KEYS = (Qt.Key.Key_Space, Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Down)


class PickerChip(QWidget):
    """Leading marker, label, caret; emits ``open_requested`` when pressed."""

    open_requested = Signal()

    def __init__(
        self,
        object_name: str,
        accessible_name: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setProperty("pickerChip", True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAccessibleName(accessible_name)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Compact: never wider than its contents.
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(32)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(8)

        self._leading = self._passive_label()
        row.addWidget(self._leading)

        self._text = self._passive_label()
        row.addWidget(self._text, 1)

        caret = self._passive_label()
        caret.setPixmap(vector_icon("caret_down", _CARET_COLOR).pixmap(16, 16))
        row.addWidget(caret)

    def _passive_label(self) -> QLabel:
        label = QLabel(self)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        return label

    # -- For subclasses -----------------------------------------------------

    def _set_leading(self, pixmap: QPixmap) -> None:
        self._leading.setPixmap(pixmap)

    def _set_text(self, text: str) -> None:
        self._text.setText(text)

    # -- State --------------------------------------------------------------

    def set_open(self, is_open: bool) -> None:
        """Style the chip as pressed while its sheet is showing."""
        self._set_state("open", is_open)

    def _set_state(self, name: str, value: bool) -> None:
        self.setProperty(name, value)
        style = self.style()
        style.unpolish(self)
        style.polish(self)

    # -- Interaction --------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt naming
        if event.key() in _OPEN_KEYS:
            self.open_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._set_state("hover", True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._set_state("hover", False)
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._set_state("focused", True)
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._set_state("focused", False)
        super().focusOutEvent(event)