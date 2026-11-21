"""Round "+" button that submits the typed task."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QWidget

from app.ui.styles.add_task_bar_style import (
    FOCUS_COLOR,
    FOCUS_WIDTH,
    PLUS_FILL,
    PLUS_GLYPH_COLOR,
    PLUS_GLYPH_HALF,
    PLUS_GLYPH_STROKE,
    PLUS_LOCKED_FILL,
    PLUS_SIZE,
)

__all__ = ["PlusButton"]

_ACTIVATE_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter)


class PlusButton(QAbstractButton):
    """36 px blue circle with a white "+"; grey while disabled (locked)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("taskAddButton")
        self.setFixedSize(PLUS_SIZE, PLUS_SIZE)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("إضافة المهمة")
        self.setToolTip("إضافة المهمة")

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt naming
        if event.key() in _ACTIVATE_KEYS:
            self.click()
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            circle = QRectF(self.rect())

            fill = PLUS_FILL if self.isEnabled() else PLUS_LOCKED_FILL
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(fill))
            painter.drawEllipse(circle)

            self._paint_plus(painter, circle.center())
            if self.hasFocus():
                self._paint_focus_ring(painter, circle)
        finally:
            painter.end()

    @staticmethod
    def _paint_plus(painter: QPainter, center: QPointF) -> None:
        pen = QPen(QColor(PLUS_GLYPH_COLOR), PLUS_GLYPH_STROKE)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        half = PLUS_GLYPH_HALF
        painter.drawLine(center - QPointF(half, 0), center + QPointF(half, 0))
        painter.drawLine(center - QPointF(0, half), center + QPointF(0, half))

    @staticmethod
    def _paint_focus_ring(painter: QPainter, circle: QRectF) -> None:
        painter.setPen(QPen(QColor(FOCUS_COLOR), FOCUS_WIDTH))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inset = FOCUS_WIDTH / 2
        painter.drawEllipse(circle.adjusted(inset, inset, -inset, -inset))