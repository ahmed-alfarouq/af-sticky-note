"""Meta line under a task title: priority dot + "priority · category"."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from app.core.models import TaskPriority
from app.ui.priority_presentation import PRIORITY_LABELS
from app.ui.styles.task_item_style import (
    META_DOT_GAP,
    META_DOT_SIZE,
    META_PX,
    PRIORITY_LOW_COLOR,
    PRIORITY_NORMAL_COLOR,
    PRIORITY_URGENT_COLOR,
    repolish,
)
from app.ui.widgets.task_item.elided_label import ElidedLabel

__all__ = ["TaskMetaLine"]

PRIORITY_DOT_COLORS = {
    TaskPriority.HIGH: PRIORITY_URGENT_COLOR,
    TaskPriority.MEDIUM: PRIORITY_NORMAL_COLOR,
    TaskPriority.LOW: PRIORITY_LOW_COLOR,
}

UNFINISHED_TEXT = "لم تكتمل"


class _PriorityDot(QWidget):
    """Filled circle painted directly (no QSS), fixed at 8 px."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._color = QColor(PRIORITY_NORMAL_COLOR)
        self.setFixedSize(QSize(META_DOT_SIZE, META_DOT_SIZE))
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


class TaskMetaLine(QWidget):
    """Dot + text row (RTL: the dot is rightmost, 6 px before the text)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("taskMeta")

        self._dot = _PriorityDot(self)
        self._text = ElidedLabel(parent=self)
        self._text.setObjectName("taskMetaText")
        font = self._text.font()
        font.setPixelSize(META_PX)
        self._text.setFont(font)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(META_DOT_GAP)
        layout.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._text, 1)

    def show_priority(self, priority: TaskPriority, category_name: str) -> None:
        """Open row: colored dot + "priority · category"."""
        self._dot.set_color(PRIORITY_DOT_COLORS[priority])
        self._dot.setVisible(True)
        label = PRIORITY_LABELS[priority]
        self._set_text(f"{label} · {category_name}", warning=False)

    def show_unfinished(self) -> None:
        """Past-day unfinished row: amber text, no dot."""
        self._dot.setVisible(False)
        self._set_text(UNFINISHED_TEXT, warning=True)

    def _set_text(self, text: str, *, warning: bool) -> None:
        self._text.set_full_text(text)
        self._text.setProperty("tone", "warning" if warning else "normal")
        repolish(self._text)