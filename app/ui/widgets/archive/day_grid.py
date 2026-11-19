"""A month as a grid of day cells (with weekday headings), painted directly.

Only days that can be opened are active. Colors follow the design: openable
days on a soft fill, the chosen day in blue, today with a thin ring, and
everything else dimmed. The first column follows the layout direction, so in
RTL the first weekday is rightmost.
"""

from __future__ import annotations

from typing import FrozenSet, List, Optional

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.ui.archive_calendar import month_grid, short_weekday, weekday_columns
from app.ui.styles.archive_style import (
    CELL_DAY_PX,
    CELL_FILL,
    CELL_HEIGHT,
    CELL_RADIUS,
    CELL_SELECTED_FILL,
    CELL_TEXT,
    CELL_TEXT_OFF,
    GRID_COLUMNS,
    GRID_GAP,
    MUTED,
    TODAY_RING,
    TODAY_RING_WIDTH,
    WEEKDAY_HEIGHT,
    WEEKDAY_PX,
)
from app.ui.styles.screen_style import FOCUS_COLOR, FOCUS_WIDTH

__all__ = ["DayGrid"]

_MIN_CELL_WIDTH = 34
_SELECT_KEYS = (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter)


class DayGrid(QWidget):
    """Weekday headings and the days of one month."""

    #: An openable day was chosen (the day number).
    day_selected = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._cells: List[Optional[int]] = []
        self._columns: List[int] = []
        self._enabled: FrozenSet[int] = frozenset()
        self._today: Optional[int] = None
        self._selected: Optional[int] = None
        self._cursor: Optional[int] = None  # the day the keyboard is on

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    # -- Content ------------------------------------------------------------

    def set_month(
        self,
        year: int,
        month: int,
        week_start: int,
        enabled_days: FrozenSet[int],
        today_day: Optional[int],
        selected_day: Optional[int],
    ) -> None:
        self._cells = month_grid(year, month, week_start)
        self._columns = weekday_columns(week_start)
        self._enabled = enabled_days
        self._today = today_day
        self._selected = selected_day
        self._cursor = selected_day if selected_day in enabled_days else self._first_enabled()

        self.setFixedHeight(self.sizeHint().height())
        self.update()

    def set_selected(self, day: Optional[int]) -> None:
        self._selected = day
        self.update()

    def _first_enabled(self) -> Optional[int]:
        return min(self._enabled) if self._enabled else None

    # -- Geometry -----------------------------------------------------------

    def _rows(self) -> int:
        return -(-len(self._cells) // GRID_COLUMNS)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        rows = self._rows()
        height = WEEKDAY_HEIGHT + rows * CELL_HEIGHT + max(0, rows - 1) * GRID_GAP
        return QSize(GRID_COLUMNS * _MIN_CELL_WIDTH + (GRID_COLUMNS - 1) * GRID_GAP, height)

    def _cell_width(self) -> float:
        return (self.width() - (GRID_COLUMNS - 1) * GRID_GAP) / GRID_COLUMNS

    def _column_rect(self, column: int, top: float, height: float) -> QRectF:
        width = self._cell_width()
        left = column * (width + GRID_GAP)
        if self.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            left = self.width() - left - width
        return QRectF(left, top, width, height)

    def _day_rect(self, day: int) -> QRectF:
        slot = self._cells.index(day)
        row, column = divmod(slot, GRID_COLUMNS)
        top = WEEKDAY_HEIGHT + row * (CELL_HEIGHT + GRID_GAP)
        return self._column_rect(column, top, CELL_HEIGHT)

    # -- Painting -----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self._paint_headings(painter)
            for day in (d for d in self._cells if d is not None):
                self._paint_day(painter, day)
        finally:
            painter.end()

    def _font(self, pixels: int, *, bold: bool = False) -> QFont:
        font = QFont(self.font())
        font.setPixelSize(pixels)
        font.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
        return font

    def _paint_headings(self, painter: QPainter) -> None:
        painter.setFont(self._font(WEEKDAY_PX))
        painter.setPen(QColor(MUTED))
        for column, weekday in enumerate(self._columns):
            rect = self._column_rect(column, 0, WEEKDAY_HEIGHT)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, short_weekday(weekday))

    def _paint_day(self, painter: QPainter, day: int) -> None:
        rect = self._day_rect(day)
        openable = day in self._enabled

        if day == self._selected and openable:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(CELL_SELECTED_FILL))
            painter.drawRoundedRect(rect, CELL_RADIUS, CELL_RADIUS)
        elif openable:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(CELL_FILL))
            painter.drawRoundedRect(rect, CELL_RADIUS, CELL_RADIUS)

        if day == self._today:
            self._paint_ring(painter, rect, QColor(TODAY_RING), TODAY_RING_WIDTH)
        if self.hasFocus() and day == self._cursor:
            self._paint_ring(painter, rect, QColor(FOCUS_COLOR), FOCUS_WIDTH)

        painter.setFont(self._font(CELL_DAY_PX, bold=openable))
        painter.setPen(QColor(CELL_TEXT if openable else CELL_TEXT_OFF))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(day))

    @staticmethod
    def _paint_ring(painter: QPainter, rect: QRectF, color: QColor, width: float) -> None:
        painter.setPen(QPen(color, width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inset = width / 2
        painter.drawRoundedRect(rect.adjusted(inset, inset, -inset, -inset), CELL_RADIUS, CELL_RADIUS)

    # -- Mouse and keyboard ---------------------------------------------------

    def _day_at(self, point) -> Optional[int]:
        for day in (d for d in self._cells if d is not None):
            if self._day_rect(day).contains(point):
                return day
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        day = self._day_at(event.position())
        if day is not None and day in self._enabled:
            self._cursor = day
            self.day_selected.emit(day)
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt naming
        key = event.key()
        if key in _SELECT_KEYS:
            if self._cursor is not None:
                self.day_selected.emit(self._cursor)
            event.accept()
            return

        step = self._step_for(key)
        if step is None:
            super().keyPressEvent(event)
            return
        self._move_cursor(step)
        event.accept()

    def _step_for(self, key: int) -> Optional[int]:
        """Days to move for an arrow key (visual left is later in RTL)."""
        rtl = self.layoutDirection() == Qt.LayoutDirection.RightToLeft
        steps: dict[int, int] = {
            Qt.Key.Key_Left.value: 1 if rtl else -1,
            Qt.Key.Key_Right.value: -1 if rtl else 1,
            Qt.Key.Key_Up.value: -GRID_COLUMNS,
            Qt.Key.Key_Down.value: GRID_COLUMNS,
        }
        return steps.get(key)

    def _move_cursor(self, step: int) -> None:
        """Move to the next openable day in the direction of ``step``."""
        if self._cursor is None:
            return
        day = self._cursor + step
        last = max(d for d in self._cells if d is not None)
        while 1 <= day <= last:
            if day in self._enabled:
                self._cursor = day
                self.update()
                return
            day += step

    def focusInEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().focusOutEvent(event)
        self.update()