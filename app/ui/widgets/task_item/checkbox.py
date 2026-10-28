"""Circular completion checkbox for task rows."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton, QWidget

from app.ui.styles.task_item_style import (
    CHECK_DONE_FILL,
    CHECK_DONE_MARK,
    CHECK_ICON_SIZE,
    CHECK_OUTLINE_COLOR,
    CHECK_PAST_COLOR,
    CHECK_PAST_MARK,
    CHECK_PAST_OPEN_OPACITY,
    CHECK_STROKE,
    CHECKBOX_OUTLINE,
    CHECKBOX_SIZE,
    FOCUS_COLOR,
)

__all__ = ["CompletionCheckbox"]

_LABEL_COMPLETE = "إكمال المهمة"
_LABEL_UNDO = "إلغاء الإكمال"

# Check mark vertices inside the 16 px icon box.
_CHECK_POINTS = ((3.0, 8.5), (6.5, 12.0), (13.0, 4.5))


class CompletionCheckbox(QAbstractButton):
    """A 28 px circle: outline when open, filled with a check when done.

    Read-only (past-day) rows use dimmer colors and are disabled.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._read_only = False

        self.setObjectName("taskCheckBox")
        self.setCheckable(True)
        self.setFixedSize(CHECKBOX_SIZE, CHECKBOX_SIZE)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_accessibility()

    def sync(self, checked: bool, read_only: bool) -> None:
        """Apply state from the row without emitting ``toggled``."""
        was_blocked = self.blockSignals(True)
        self.setChecked(checked)
        self.blockSignals(was_blocked)

        self._read_only = read_only
        self.setEnabled(not read_only)
        self.setCursor(
            Qt.CursorShape.ArrowCursor
            if read_only
            else Qt.CursorShape.PointingHandCursor
        )
        self._refresh_accessibility()
        self.update()

    def _refresh_accessibility(self) -> None:
        self.setAccessibleName(_LABEL_UNDO if self.isChecked() else _LABEL_COMPLETE)

    # -- Painting -----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            circle = QRectF(self.rect())

            if self.isChecked():
                self._paint_done(painter, circle)
            else:
                self._paint_open(painter, circle)

            if self.hasFocus():
                self._paint_focus_ring(painter, circle)
        finally:
            painter.end()

    def _paint_open(self, painter: QPainter, circle: QRectF) -> None:
        color = QColor(CHECK_PAST_COLOR if self._read_only else CHECK_OUTLINE_COLOR)
        if self._read_only:
            color.setAlphaF(CHECK_PAST_OPEN_OPACITY)

        painter.setPen(QPen(color, CHECKBOX_OUTLINE))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inset = CHECKBOX_OUTLINE / 2
        painter.drawEllipse(circle.adjusted(inset, inset, -inset, -inset))

    def _paint_done(self, painter: QPainter, circle: QRectF) -> None:
        fill = CHECK_PAST_COLOR if self._read_only else CHECK_DONE_FILL
        mark = CHECK_PAST_MARK if self._read_only else CHECK_DONE_MARK

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(fill))
        painter.drawEllipse(circle)

        origin = circle.center() - QPointF(CHECK_ICON_SIZE / 2, CHECK_ICON_SIZE / 2)
        path = QPainterPath()
        for index, (x, y) in enumerate(_CHECK_POINTS):
            point = origin + QPointF(x, y)
            if index == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)

        pen = QPen(QColor(mark), CHECK_STROKE)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    def _paint_focus_ring(self, painter: QPainter, circle: QRectF) -> None:
        painter.setPen(QPen(QColor(FOCUS_COLOR), CHECKBOX_OUTLINE))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inset = CHECKBOX_OUTLINE / 2
        painter.drawEllipse(circle.adjusted(inset, inset, -inset, -inset))