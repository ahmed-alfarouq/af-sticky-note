"""Progress ring: completion circle for the date hero (v3 §5.2).

A fixed 44px ring: track + clockwise progress arc + ``done/total`` center
text forced left-to-right. Repaints on value change and during the single
bounded 350 ms ease-out transition that follows a change -- never
continuously while idle. Statistics come from :func:`compute_daily_stats`
(source of truth); this widget only draws them.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.ui import theme

RING_SIZE = 44
RING_WIDTH = 4

#: Default sweep animation (v3 §1.3/§5.2). Tests construct with 0 for
#: deterministic snapshots. No OS animation-preference detection exists in
#: Qt portably; always-on animation here is a documented limitation.
DEFAULT_SWEEP_MS = 350

__all__ = ["ProgressRing", "RING_SIZE"]


class ProgressRing(QWidget):
    """44px ring showing ``done/total`` as an arc + center count."""

    def __init__(self, parent: Optional[QWidget] = None, animated_ms: int = DEFAULT_SWEEP_MS) -> None:
        super().__init__(parent)
        self.setObjectName("progressRing")
        self.setFixedSize(RING_SIZE, RING_SIZE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # The center count must never mirror to "total/done": force LTR so
        # the bidi algorithm cannot reorder the digits around the slash.
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._completed = 0
        self._total = 0
        self._displayed = 0.0
        self._animated_ms = animated_ms
        self._animation: Optional[QVariantAnimation] = None
        self.setAccessibleName("تقدم مهام اليوم")

    def set_progress(self, completed: int, total: int) -> None:
        """Update the ring; no-op (no repaint) when nothing changed."""
        completed = max(0, completed)
        total = max(0, total)
        if (completed, total) == (self._completed, self._total):
            return
        self._completed = completed
        self._total = total
        self.setToolTip(f"أُنجز {completed} من {total}")
        self.setAccessibleName(f"أُنجز {completed} من {total}")
        self.setAccessibleDescription(f"أُنجز {completed} من {total}")
        target = (completed / total) if total else 0.0
        if self._animated_ms <= 0:
            self._displayed = target
            self.update()
            return
        if self._animation is not None:
            self._animation.stop()
        animation = QVariantAnimation(self)
        animation.setDuration(self._animated_ms)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.setStartValue(self._displayed)
        animation.setEndValue(target)
        animation.valueChanged.connect(self._on_sweep_frame)
        self._animation = animation
        animation.start()

    def _on_sweep_frame(self, value: object) -> None:
        self._displayed = float(value)
        self.update()

    def progress_value(self) -> tuple:
        """Current ``(completed, total)`` (tests / diagnostics)."""
        return (self._completed, self._total)

    def displayed_fraction(self) -> float:
        """Arc fraction currently painted (tests / diagnostics)."""
        return self._displayed

    def center_text(self) -> str:
        """The ``done/total`` count shown in the ring center."""
        return f"{self._completed}/{self._total}"

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
            track = QPen(QColor(theme.BORDER), RING_WIDTH)
            track.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(track)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(cx.x() - diameter // 2, cx.y() - diameter // 2, diameter, diameter)
            # Arc: trust blue, success green at 100%. Zero progress draws
            # no arc but still falls through to the center count.
            fraction = self._displayed
            color = theme.SUCCESS if fraction >= 1.0 else theme.TRUST
            arc = QPen(QColor(color), RING_WIDTH)
            arc.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc)
            painter.drawArc(
                cx.x() - diameter // 2, cx.y() - diameter // 2, diameter, diameter,
                90 * 16, -int(round(fraction * 360)) * 16,
            )
            # Center count, always left-to-right.
            painter.setPen(QColor(theme.TEXT))
            font = QFont(painter.font())
            font.setPixelSize(12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.center_text())
        finally:
            painter.end()
