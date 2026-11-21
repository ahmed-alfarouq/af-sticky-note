"""Green banner shown when every task of today is done."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QWidget

from app.ui.styles.task_list_style import (
    BANNER_GAP,
    BANNER_ICON_COLOR,
    BANNER_ICON_SIZE,
    BANNER_PADDING,
)

__all__ = ["AllDoneBanner"]

BANNER_TEXT = "أنجزت كل مهام اليوم. أحسنت!"

# Check mark vertices inside the 22 px icon box.
_CHECK_POINTS = ((4.0, 11.5), (9.0, 16.0), (18.0, 6.0))


class _CheckIcon(QWidget):
    """22 px check mark, painted directly."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(QSize(BANNER_ICON_SIZE, BANNER_ICON_SIZE))

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            path = QPainterPath()
            for index, (x, y) in enumerate(_CHECK_POINTS):
                if index == 0:
                    path.moveTo(QPointF(x, y))
                else:
                    path.lineTo(QPointF(x, y))

            pen = QPen(QColor(BANNER_ICON_COLOR), 2.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(path)
        finally:
            painter.end()


class AllDoneBanner(QFrame):
    """Check icon (rightmost in RTL) followed by the congratulation text."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("allDoneBanner")
        self.setAccessibleName(BANNER_TEXT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        text = QLabel(BANNER_TEXT, self)
        text.setObjectName("allDoneText")
        text.setWordWrap(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(*(BANNER_PADDING,) * 4)
        layout.setSpacing(BANNER_GAP)
        layout.addWidget(_CheckIcon(self), 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(text, 1)
