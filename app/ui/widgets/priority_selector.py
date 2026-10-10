"""The Qt widget for choosing a task priority.

The Arabic labels themselves live in :mod:`app.ui.priority_presentation`, which
is Qt-free, so the enum -> label mapping has exactly one home and can be tested
without a GUI toolkit.
"""
from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QComboBox, QSizePolicy, QWidget

from app.core.models import TaskPriority
from app.ui.priority_presentation import PRIORITY_LABELS, PRIORITY_ORDER, priority_label
from app.ui.widgets.combo_popup import fit_popup_to_contents

__all__ = [
    "PrioritySelector",
    "PRIORITY_LABELS",
    "PRIORITY_ORDER",
    "priority_label",
    "priority_dot_icon",
]

_DOT_ICON_CACHE: Dict[str, QIcon] = {}


def _dot_icon(color_hex: str) -> QIcon:
    """12px filled dot used as a dropdown decoration (cached per color)."""
    cached = _DOT_ICON_CACHE.get(color_hex)
    if cached is not None:
        return cached
    pixmap = QPixmap(12, 12)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color_hex))
        painter.drawEllipse(1, 1, 10, 10)
    finally:
        painter.end()
    icon = QIcon(pixmap)
    _DOT_ICON_CACHE[color_hex] = icon
    return icon


def priority_dot_icon(priority: TaskPriority) -> QIcon:
    """Cached dropdown dot icon: red HIGH, calm blue MEDIUM, blue-gray LOW."""
    colors = {
        TaskPriority.HIGH: "#E57373",
        TaskPriority.MEDIUM: "#4F7CAC",
        TaskPriority.LOW: "#98A2B3",
    }
    return _dot_icon(colors.get(priority, "#98A2B3"))


class PrioritySelector(QComboBox):
    """Compact combo box for choosing a task priority.

    Exposes and accepts :class:`TaskPriority` values only -- never an index and
    never a raw string -- so callers never have to convert anything themselves.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("prioritySelector")
        self.setAccessibleName("أولوية المهمة")
        self.setAccessibleDescription("اختر أولوية المهمة: عاجل أو عادي أو منخفض")
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        # Compact: never wider than its own contents, so it cannot compete
        # with the task text for space.
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        for priority in PRIORITY_ORDER:
            self.addItem(priority_label(priority), priority)

        # HIGH reads red in the dropdown. NOTE: item.data() without a role
        # returns the DisplayRole (label text); the TaskPriority lives under
        # UserRole as set by addItem(text, userData).
        model = self.model()
        for row in range(model.rowCount()):
            item = model.item(row)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == TaskPriority.HIGH:
                item.setForeground(QColor("#E57373"))  # Red
            item.setIcon(priority_dot_icon(PRIORITY_ORDER[row]))

        self.setCurrentIndex(self._index_of(TaskPriority.MEDIUM))

    def showPopup(self) -> None:  # noqa: N802 - Qt naming
        """Widen the popup view to fit the widest item before showing."""
        fit_popup_to_contents(self)
        super().showPopup()

    # ------------------------------------------------------------------
    # Value access
    # ------------------------------------------------------------------
    def _index_of(self, priority: TaskPriority) -> int:
        for index in range(self.count()):
            if self.itemData(index) == priority:
                return index
        return 0

    def selected_priority(self) -> TaskPriority:
        """Return the currently chosen priority (MEDIUM when unreadable)."""
        data = self.currentData()
        if isinstance(data, TaskPriority):
            return data
        try:
            return TaskPriority(data)
        except (ValueError, TypeError):
            return TaskPriority.MEDIUM

    def set_priority(self, priority: Optional[TaskPriority]) -> None:
        """Select ``priority`` silently -- no signals, no side effects."""
        target = priority if isinstance(priority, TaskPriority) else TaskPriority.MEDIUM
        index = self._index_of(target)
        if index == self.currentIndex():
            return
        self.blockSignals(True)
        try:
            self.setCurrentIndex(index)
        finally:
            self.blockSignals(False)
