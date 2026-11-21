"""Shared mechanics of the picker chips (category, priority).

A flat pill: a leading marker and a label. It holds no options and opens
nothing itself: pressing it (click, Space, Enter, Down) emits
``open_requested`` and the window presents the sheet. Look (fill, radius,
label color) lives in ``add_task_bar_style``; only the keyboard focus ring
is drawn here.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from app.ui.styles.add_task_bar_style import (
    CHIP_GAP,
    CHIP_HEIGHT,
    CHIP_PAD_H,
    CHIP_RADIUS,
    FOCUS_COLOR,
    FOCUS_WIDTH,
)

__all__ = ["PickerChip"]

_OPEN_KEYS = (Qt.Key.Key_Space, Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Down)


class PickerChip(QWidget):
    """Leading marker + label; emits ``open_requested`` when pressed."""

    open_requested = Signal()

    def __init__(
        self,
        object_name: str,
        accessible_name: str,
        leading: QWidget,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setProperty("pickerChip", True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAccessibleName(accessible_name)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Compact: never wider than its contents.
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(CHIP_HEIGHT)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._text = QLabel(self)
        self._text.setObjectName("pickerChipText")

        row = QHBoxLayout(self)
        row.setContentsMargins(CHIP_PAD_H, 0, CHIP_PAD_H, 0)
        row.setSpacing(CHIP_GAP)
        row.addWidget(leading, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._text, 0, Qt.AlignmentFlag.AlignVCenter)

        # Presses belong to the chip, never to its inner widgets.
        for child in (leading, self._text):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def _set_text(self, text: str) -> None:
        self._text.setText(text)

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

    # -- Focus ring ---------------------------------------------------------

    def focusInEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().focusOutEvent(event)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if not self.hasFocus():
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(QPen(QColor(FOCUS_COLOR), FOCUS_WIDTH))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            inset = FOCUS_WIDTH / 2
            area = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
            painter.drawRoundedRect(area, CHIP_RADIUS, CHIP_RADIUS)
        finally:
            painter.end()