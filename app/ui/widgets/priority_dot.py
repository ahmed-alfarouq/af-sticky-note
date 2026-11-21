"""Small filled circle showing a priority's color."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

__all__ = ["PriorityDot", "DOT_SIZE"]

DOT_SIZE = 8


class PriorityDot(QWidget):
    """An 8 px dot painted directly (no QSS)."""

    def __init__(self, color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(QSize(DOT_SIZE, DOT_SIZE))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._color)
            painter.drawEllipse(self.rect())
        finally:
            painter.end()