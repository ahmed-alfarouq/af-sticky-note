"""Centered empty-day block: dashed "+" circle, title, helper line."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from app.ui.styles.task_list_style import (
    EMPTY_CIRCLE_COLOR,
    EMPTY_CIRCLE_SIZE,
    EMPTY_PLUS_COLOR,
    EMPTY_PLUS_SIZE,
)

__all__ = ["EmptyState"]

EMPTY_TITLE = "يومك فارغ"
EMPTY_BODY = "ابدأ بمهمة واحدة، ثم اضغط Enter لإضافة التالية."

_STROKE = 2.0


class _DashedPlus(QWidget):
    """Dashed circle with a centered "+"."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(QSize(EMPTY_CIRCLE_SIZE, EMPTY_CIRCLE_SIZE))

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            circle_pen = QPen(QColor(EMPTY_CIRCLE_COLOR), _STROKE)
            circle_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(circle_pen)
            inset = _STROKE / 2
            painter.drawEllipse(QRectF(self.rect()).adjusted(inset, inset, -inset, -inset))

            plus_pen = QPen(QColor(EMPTY_PLUS_COLOR), _STROKE)
            plus_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(plus_pen)
            center = QPointF(self.rect().center()) + QPointF(0.5, 0.5)
            half = EMPTY_PLUS_SIZE / 2
            painter.drawLine(center - QPointF(half, 0), center + QPointF(half, 0))
            painter.drawLine(center - QPointF(0, half), center + QPointF(0, half))
        finally:
            painter.end()


class EmptyState(QWidget):
    """Vertically and horizontally centered empty-day content."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("emptyState")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        title = QLabel(EMPTY_TITLE, self)
        title.setObjectName("emptyStateTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)

        body = QLabel(EMPTY_BODY, self)
        body.setObjectName("emptyStateBody")
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)
        layout.addStretch(1)
        layout.addWidget(_DashedPlus(self), 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addStretch(1)
