"""Meta line under a task title: priority dot + "priority · category"."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QWidget

from app.core.models import TaskPriority
from app.ui.priority_presentation import (
    DEFAULT_TASK_PRIORITY,
    PRIORITY_COLORS,
    PRIORITY_LABELS,
)
from app.ui.styles.task_item_style import (
    META_DOT_GAP,
    META_PX,
    repolish,
)
from app.ui.widgets.priority_dot import PriorityDot
from app.ui.widgets.task_item.elided_label import ElidedLabel

__all__ = ["TaskMetaLine"]

UNFINISHED_TEXT = "لم تكتمل"


class TaskMetaLine(QWidget):
    """Dot + text row (RTL: the dot is rightmost, 6 px before the text)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("taskMeta")

        self._dot = PriorityDot(PRIORITY_COLORS[DEFAULT_TASK_PRIORITY], self)
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
        self._dot.set_color(PRIORITY_COLORS[priority])
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