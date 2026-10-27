"""Reusable daily progress ring with Arabic labels.

The widget displays a ring and a two-line text column. It inherits the
application's layout direction: in the application's RTL layout, text is
on the physical left and the ring is on the physical right.

Daily task statistics must be supplied by the caller.
"""

from __future__ import annotations

import math
from typing import cast

from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation
from PySide6.QtGui import QPainter, QPaintEvent
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.progress_ring_state import (
    ProgressSnapshot,
    create_progress_snapshot,
    progress_caption,
)

__all__ = [
    "ProgressRing",
    "RING_SIZE",
    "RING_WIDTH",
    "DEFAULT_SWEEP_MS",
    "RING_SIZES",
]

RING_SIZE = 44
RING_WIDTH = 4.5
DEFAULT_SWEEP_MS = 350
RING_SIZES = (40, 44, 52)

TRACK_COLOR = "#2c3649"
PROGRESS_COLOR = "#6fcfa3"
PAST_DAY_COLOR = "#8f9bb0"
COMPLETE_DISC_COLOR = "#6fcfa3"
COMPLETE_MARK_COLOR = "#1d3530"
TEXT_COLOR = "#ffffff"
CAPTION_COLOR = "#a3aec2"
COMPLETE_CAPTION_COLOR = "#b5e8d0"

_EMPTY_TRACK_DASH = "3 4"
_RING_PADDING = 2
_CHECK_STROKE_RATIO = 0.055
_CHECK_MIN_STROKE = 2.0
# Checkmark vertices as (x, y) offsets from center, in units of ring size.
_CHECK_POINTS = ((-0.15, 0.0), (-0.035, 0.12), (0.20, -0.12))

_FRACTION_STYLE = f"color: {TEXT_COLOR}; font-size: 16px; font-weight: 600;"
_CAPTION_STYLE = "color: {color}; font-size: 13px;"

_RING_ACCESSIBLE_NAME = "تقدم مهام اليوم"
_GRAPHIC_ACCESSIBLE_NAME = "تقدم المهام"


class _RingGraphic(QWidget):
    """SVG-rendered circular progress indicator."""

    def __init__(self, size: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._size = size
        self._snapshot = create_progress_snapshot(0, 0)
        self._fraction = 0.0

        self._renderer = QSvgRenderer(self)
        self._renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)

        self.setObjectName("progressRingGraphic")
        self.setFixedSize(size, size)
        self.setAccessibleName(_GRAPHIC_ACCESSIBLE_NAME)

        self._reload_svg()

    def set_state(
        self,
        snapshot: ProgressSnapshot,
        displayed_fraction: float,
    ) -> None:
        """Update the displayed state, rebuilding the SVG only on change."""
        fraction = max(0.0, min(1.0, displayed_fraction))

        if snapshot == self._snapshot and math.isclose(fraction, self._fraction):
            return

        self._snapshot = snapshot
        self._fraction = fraction
        self._reload_svg()

    def _reload_svg(self) -> None:
        self._renderer.load(self._build_svg())
        self.update()

    # -- SVG construction -------------------------------------------------

    def _build_svg(self) -> bytes:
        size = self._size
        center = size / 2
        radius = center - RING_WIDTH / 2 - _RING_PADDING

        # Mirror only the ring geometry for RTL; the center mark is never
        # mirrored.
        ring = (
            f'<g transform="translate({size} 0) scale(-1 1)">'
            f"{self._track_svg(center, radius)}"
            f"{self._arc_svg(center, radius)}</g>"
        )

        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">'
            f"{ring}{self._center_mark_svg(center, radius)}</svg>"
        )
        return svg.encode("utf-8")

    def _track_svg(self, center: float, radius: float) -> str:
        # The empty state keeps a visibly dashed track.
        dash = (
            f' stroke-dasharray="{_EMPTY_TRACK_DASH}"'
            if self._snapshot.is_empty
            else ""
        )
        return (
            f'<circle cx="{center:.2f}" cy="{center:.2f}" '
            f'r="{radius:.2f}" fill="none" stroke="{TRACK_COLOR}" '
            f'stroke-width="{RING_WIDTH:.2f}"{dash}/>'
        )

    def _arc_svg(self, center: float, radius: float) -> str:
        snapshot = self._snapshot

        if snapshot.is_empty or snapshot.is_complete or self._fraction <= 0:
            return ""

        color = PAST_DAY_COLOR if snapshot.is_past_day else PROGRESS_COLOR
        circumference = 2 * math.pi * radius
        offset = circumference * (1.0 - self._fraction)

        return (
            f'<circle cx="{center:.2f}" cy="{center:.2f}" '
            f'r="{radius:.2f}" fill="none" stroke="{color}" '
            f'stroke-width="{RING_WIDTH:.2f}" stroke-linecap="round" '
            f'stroke-dasharray="{circumference:.3f}" '
            f'stroke-dashoffset="{offset:.3f}" '
            f'transform="rotate(-90 {center:.2f} {center:.2f})"/>'
        )

    def _center_mark_svg(self, center: float, radius: float) -> str:
        # Only the complete state has a center mark; no text is ever drawn.
        if self._snapshot.is_complete:
            return self._checkmark_svg(center, radius)
        return ""

    def _checkmark_svg(self, center: float, radius: float) -> str:
        size = self._size
        points = " L ".join(
            f"{center + dx * size:.2f} {center + dy * size:.2f}"
            for dx, dy in _CHECK_POINTS
        )
        stroke = max(_CHECK_MIN_STROKE, size * _CHECK_STROKE_RATIO)

        return (
            f'<circle cx="{center:.2f}" cy="{center:.2f}" '
            f'r="{radius + RING_WIDTH / 2:.2f}" '
            f'fill="{COMPLETE_DISC_COLOR}"/>'
            f'<path d="M {points}" fill="none" '
            f'stroke="{COMPLETE_MARK_COLOR}" stroke-width="{stroke:.2f}" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
        )

    # -- Painting ---------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        if not self._renderer.isValid():
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self._renderer.render(painter, self.rect())
        finally:
            painter.end()


class ProgressRing(QWidget):
    """Progress ring with a fraction and caption beside it."""

    def __init__(
        self,
        parent: QWidget | None = None,
        animated_ms: int = DEFAULT_SWEEP_MS,
        size: int = RING_SIZE,
    ) -> None:
        super().__init__(parent)

        if size <= 0:
            raise ValueError("size must be greater than zero")
        if animated_ms < 0:
            raise ValueError("animated_ms cannot be negative")

        self.setObjectName("progressRing")
        self.setAccessibleName(_RING_ACCESSIBLE_NAME)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )

        self._animated_ms = animated_ms
        self._snapshot = create_progress_snapshot(0, 0)
        self._displayed = 0.0
        self._animation: QVariantAnimation | None = None

        self._graphic = _RingGraphic(size, self)

        self._fraction_label = QLabel(self)
        self._fraction_label.setObjectName("progressFraction")
        self._fraction_label.setWordWrap(False)
        self._fraction_label.setStyleSheet(_FRACTION_STYLE)

        self._caption_label = QLabel(self)
        self._caption_label.setObjectName("progressCaption")
        self._caption_label.setWordWrap(True)
        self._caption_label.setMinimumWidth(0)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.addWidget(self._fraction_label)
        text_layout.addWidget(self._caption_label)

        # Inherit the RTL direction: ring on the right, text on the left.
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._graphic, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(text_layout, 1)

        self._refresh_all()

    # -- Public API -------------------------------------------------------

    def set_progress(self, completed: int, total: int) -> None:
        """Update task counts and animate the displayed fraction."""
        snapshot = create_progress_snapshot(
            completed,
            total,
            past_day=self._snapshot.is_past_day,
        )

        if snapshot == self._snapshot:
            return

        self._snapshot = snapshot
        self._refresh_text()

        target = snapshot.fraction
        self._stop_animation()

        # The completed state draws a disc, so no arc sweep is needed.
        if self._animated_ms == 0 or snapshot.is_complete:
            self._displayed = target
            self._refresh_graphic()
            return

        animation = QVariantAnimation(self)
        animation.setDuration(self._animated_ms)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.setStartValue(self._displayed)
        animation.setEndValue(target)
        animation.valueChanged.connect(self._on_sweep_frame)
        animation.finished.connect(
            lambda current=animation: self._on_animation_finished(current)
        )

        self._animation = animation
        animation.start()

    def set_past_day(self, is_past_day: bool = True) -> None:
        """Switch between current-day and historical-record presentation."""
        snapshot = create_progress_snapshot(
            self._snapshot.completed,
            self._snapshot.total,
            past_day=is_past_day,
        )

        if snapshot == self._snapshot:
            return

        self._stop_animation()
        self._snapshot = snapshot
        self._displayed = snapshot.fraction
        self._refresh_all()

    def is_past_day(self) -> bool:
        return self._snapshot.is_past_day

    def is_complete(self) -> bool:
        return self._snapshot.is_complete

    def progress_value(self) -> tuple[int, int]:
        """Return normalized (completed, total) task counts."""
        return self._snapshot.completed, self._snapshot.total

    def displayed_fraction(self) -> float:
        """Return the fraction currently shown by the progress arc."""
        return self._displayed

    def fraction_text(self) -> str:
        """Return the visible Arabic fraction label (empty if no tasks)."""
        if self._snapshot.is_empty:
            return ""
        return f"{self._snapshot.completed} من {self._snapshot.total}"

    def caption_text(self) -> str:
        """Return the Arabic caption for the current state."""
        return progress_caption(self._snapshot)

    # -- Refresh helpers --------------------------------------------------

    def _refresh_all(self) -> None:
        self._refresh_text()
        self._refresh_graphic()

    def _refresh_text(self) -> None:
        """Sync labels, accessibility text, and the pastDay property."""
        snapshot = self._snapshot
        fraction = self.fraction_text()
        caption = self.caption_text()

        self.setProperty("pastDay", snapshot.is_past_day)

        self._fraction_label.setVisible(bool(fraction))
        self._fraction_label.setText(fraction)

        caption_color = (
            COMPLETE_CAPTION_COLOR if snapshot.is_complete else CAPTION_COLOR
        )
        self._caption_label.setText(caption)
        self._caption_label.setStyleSheet(
            _CAPTION_STYLE.format(color=caption_color)
        )

        description = f"{fraction}. {caption}" if fraction else caption
        self.setAccessibleDescription(description)
        self.setToolTip(description)

        self._graphic.setAccessibleName(fraction or caption)
        self._graphic.setAccessibleDescription(caption)

    def _refresh_graphic(self) -> None:
        self._graphic.set_state(self._snapshot, self._displayed)

    # -- Animation --------------------------------------------------------

    def _on_sweep_frame(self, value: object) -> None:
        self._displayed = max(0.0, min(1.0, float(cast(float, value))))
        self._refresh_graphic()

    def _on_animation_finished(self, animation: QVariantAnimation) -> None:
        """Finalize only the currently active animation."""
        if animation is not self._animation:
            return

        self._animation = None
        animation.deleteLater()
        self._displayed = self._snapshot.fraction
        self._refresh_graphic()

    def _stop_animation(self) -> None:
        animation, self._animation = self._animation, None

        if animation is not None:
            animation.stop()
            animation.deleteLater()