"""Qt-native daily-activity bar chart (Phase 7F).

One stacked bar per day (completed bottom, incomplete top), chronological
left-to-right regardless of layout direction. Paints only the data it was
given via :meth:`set_data` -- never queries, never animates, no timers.
Repaints only when the data object actually changes.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.core.daily_reports import DailyReport

_BAR_MIN_WIDTH = 8
_BAR_MAX_WIDTH = 26
_BAR_GAP = 6
_AXIS_HEIGHT = 18
_TOP_PAD = 8

__all__ = ["DailyChart"]


class DailyChart(QWidget):
    """Stacked completed/incomplete bars for a date range."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardChart")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(110)
        self.setMaximumHeight(170)
        self.setMouseTracking(True)
        self.setAccessibleName("مخطط النشاط اليومي")
        self._data: List[DailyReport] = []

    def set_data(self, daily_reports: Sequence[DailyReport]) -> None:
        """Replace the chart data (no-op, no repaint, when identical)."""
        incoming = list(daily_reports)
        if incoming == self._data:
            return
        self._data = incoming
        self.setAccessibleDescription(f"نشاط {len(incoming)} أيام")
        self.update()

    def chart_data(self) -> List[DailyReport]:
        """Stored rows in display (chronological) order (tests/diagnostics)."""
        return list(self._data)

    def bar_tooltip(self, index: int) -> str:
        """Tooltip text for one bar: date + completed/total (stored metadata)."""
        if not 0 <= index < len(self._data):
            return ""
        row = self._data[index]
        return (
            f"{row.date} • مكتملة {row.completed} من {row.total} "
            f"• {row.completion_percentage}٪"
        )

    def _index_at_x(self, x: float) -> int:
        """Bar index under horizontal position ``x`` (clamped, -1 when empty)."""
        count = len(self._data)
        if count <= 0 or self.width() <= 0:
            return -1
        return max(0, min(count - 1, int(x // (self.width() / count))))

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        """Per-bar tooltip from in-memory data (no queries, no timers)."""
        self.setToolTip(self.bar_tooltip(self._index_at_x(event.position().x())))
        super().mouseMoveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            width, height = self.width(), self.height()
            plot_h = max(10, height - _AXIS_HEIGHT - _TOP_PAD)
            count = len(self._data)
            if count == 0:
                return
            slot = width / count
            bar_w = max(_BAR_MIN_WIDTH, min(_BAR_MAX_WIDTH, int(slot - _BAR_GAP)))
            ceiling = max([row.total for row in self._data] + [1])
            day_font = QFont(painter.font())
            day_font.setPixelSize(9)
            painter.setFont(day_font)
            for index, row in enumerate(self._data):
                x = int(index * slot + (slot - bar_w) / 2)
                base = _TOP_PAD + plot_h
                if row.total <= 0:
                    # Zero-task day: quiet empty slot, still visible.
                    painter.setPen(QPen(QColor("#242F42"), 1))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRoundedRect(x, _TOP_PAD, bar_w, plot_h, 2, 2)
                else:
                    done_h = int(round(plot_h * row.completed / ceiling))
                    todo_h = int(round(plot_h * (row.total - row.completed) / ceiling))
                    if todo_h > 0:
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.setBrush(QColor("#3A465C"))
                        painter.drawRoundedRect(x, base - done_h - todo_h, bar_w, todo_h, 2, 2)
                    if done_h > 0:
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.setBrush(QColor("#4F7CAC"))
                        painter.drawRoundedRect(x, base - done_h, bar_w, done_h, 2, 2)
                # Day-of-month label under each bar.
                painter.setPen(QColor("#98A2B3"))
                try:
                    day_text = str(int(row.date.split("-")[2]))
                except (IndexError, ValueError):
                    day_text = ""
                painter.drawText(x - 4, base + 2, bar_w + 8, _AXIS_HEIGHT - 2,
                                 Qt.AlignmentFlag.AlignHCenter, day_text)
        finally:
            painter.end()
