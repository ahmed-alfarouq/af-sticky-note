"""Compact circular daily-progress indicator (Phase 7D).

A fixed-size, timer-free, animation-free ring: track + progress arc + center
percentage, repainted only when the value actually changes. The statistics
themselves come from :func:`compute_daily_stats` (source of truth); this
widget only draws them.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

RING_SIZE = 52
RING_WIDTH = 5

__all__ = ["ProgressRing", "RING_SIZE"]


class ProgressRing(QWidget):
    """52px ring showing ``completed/total`` as an arc + center percent."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("progressRing")
        self.setFixedSize(RING_SIZE, RING_SIZE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._completed = 0
        self._total = 0
        self.setAccessibleName("تقدم مهام اليوم")

    def set_progress(self, completed: int, total: int) -> None:
        """Update the ring; no-op (no repaint) when nothing changed."""
        completed = max(0, completed)
        total = max(0, total)
        if (completed, total) == (self._completed, self._total):
            return
        self._completed = completed
        self._total = total
        percent = round((completed / total) * 100) if total else 0
        self.setToolTip(f"التقدم: {completed} من {total} مكتملة • {percent}٪")
        self.setAccessibleDescription(f"{completed} من {total} مهام مكتملة")
        self.update()

    def progress_value(self) -> tuple:
        """Current ``(completed, total)`` (tests / diagnostics)."""
        return (self._completed, self._total)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        side = min(self.width(), self.height())
        inset = RING_WIDTH + 3
        diameter = side - inset * 2
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            rect = painter.viewport()
            cx = rect.center()
            # Track: full quiet circle.
            track = QPen(QColor("#242F42"), RING_WIDTH)
            track.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(track)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(cx.x() - diameter // 2, cx.y() - diameter // 2, diameter, diameter)
            # Arc: trust blue, success green at 100%.
            fraction = (self._completed / self._total) if self._total else 0.0
            if fraction <= 0.0:
                return
            color = "#6FAF8F" if fraction >= 1.0 else "#4F7CAC"
            arc = QPen(QColor(color), RING_WIDTH)
            arc.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc)
            painter.drawArc(
                cx.x() - diameter // 2, cx.y() - diameter // 2, diameter, diameter,
                90 * 16, -int(round(fraction * 360)) * 16,
            )
            # Center percentage.
            painter.setPen(QColor("#F2F5F8"))
            font = QFont(painter.font())
            font.setPixelSize(11)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{round(fraction * 100)}٪")
        finally:
            painter.end()
