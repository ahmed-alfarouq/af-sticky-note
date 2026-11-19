"""A read-only task row for the archive: the task plus category and priority badges."""

from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from app.core.models import Category, Task, TaskPriority
from app.ui.category_icons import CategoryIconProvider
from app.ui.category_presentation import category_label
from app.ui.icons import icon as vector_icon
from app.ui.priority_presentation import PRIORITY_COLORS, priority_label
from app.ui.styles.archive_style import BADGE_FILL, BADGE_ICON, BADGE_RADIUS, BADGE_SIZE
from app.ui.widgets.task_item import TaskItem

__all__ = ["ArchiveTaskRow"]

_FALLBACK_ICON_COLOR = "#8f9bb0"


class _IconBadge(QWidget):
    """A small rounded square holding one icon."""

    def __init__(self, pixmap: QPixmap, description: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._pixmap = pixmap
        self.setFixedSize(QSize(BADGE_SIZE, BADGE_SIZE))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setToolTip(description)
        self.setAccessibleName(description)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(BADGE_FILL))
            painter.drawRoundedRect(QRectF(self.rect()), BADGE_RADIUS, BADGE_RADIUS)

            ratio = self._pixmap.devicePixelRatio() or 1.0
            left = (self.width() - self._pixmap.width() / ratio) / 2
            top = (self.height() - self._pixmap.height() / ratio) / 2
            painter.drawPixmap(round(left), round(top), self._pixmap)
        finally:
            painter.end()


class ArchiveTaskRow(TaskItem):
    """A past day's task: the read-only row plus its category and priority badges."""

    def __init__(
        self,
        task: Task,
        categories: Sequence[Category],
        icon_provider: CategoryIconProvider,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(task, parent, categories, icon_provider, read_only=True)

        row = self.layout()
        if not isinstance(row, QHBoxLayout):
            raise RuntimeError("a task row is laid out horizontally")
        row.addWidget(self._category_badge(task, categories, icon_provider), 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._priority_badge(task.priority), 0, Qt.AlignmentFlag.AlignVCenter)

    @staticmethod
    def _category_badge(
        task: Task,
        categories: Sequence[Category],
        icon_provider: CategoryIconProvider,
    ) -> _IconBadge:
        category = next((c for c in categories if c.id == task.category_id), None)
        if category is not None:
            icon = icon_provider.icon_for_category(category)
            name = category_label(category)
        else:
            icon = vector_icon("tag", _FALLBACK_ICON_COLOR)
            name = task.category_id
        return _IconBadge(icon.pixmap(BADGE_ICON, BADGE_ICON), f"التصنيف: {name}")

    @staticmethod
    def _priority_badge(priority: TaskPriority) -> _IconBadge:
        key = "flag_filled" if priority is TaskPriority.HIGH else "flag"
        icon = vector_icon(key, PRIORITY_COLORS[priority])
        return _IconBadge(
            icon.pixmap(BADGE_ICON, BADGE_ICON), f"الأولوية: {priority_label(priority)}"
        )