"""Animated on/off switch (46x28 pill with a sliding knob)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QWidget

from app.ui.styles.settings_style import (
    FOCUS_COLOR,
    FOCUS_WIDTH,
    SWITCH_HEIGHT,
    SWITCH_KNOB,
    SWITCH_KNOB_COLOR,
    SWITCH_MS,
    SWITCH_OFF,
    SWITCH_ON,
    SWITCH_PAD,
    SWITCH_PRESS_MS,
    SWITCH_SQUEEZE,
    SWITCH_WIDTH,
)
from app.ui.widgets.settings.blend import blend

__all__ = ["ToggleSwitch"]


class ToggleSwitch(QAbstractButton):
    """Checkable switch. Off: knob on the left; on: knob on the right.

    The knob slides while the track color blends from grey to blue, and the
    knob stretches slightly while pressed. Geometry is always left-to-right,
    whatever the layout direction.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(SWITCH_WIDTH, SWITCH_HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._progress = 0.0   # 0 = off, 1 = on
        self._squeeze = 0.0    # 0 = at rest, 1 = pressed

        self._slide = self._make_animation(b"progress", SWITCH_MS)
        self._press = self._make_animation(b"squeeze", SWITCH_PRESS_MS)

        self.toggled.connect(self._slide_to)
        self.pressed.connect(lambda: self._squeeze_to(1.0))
        self.released.connect(lambda: self._squeeze_to(0.0))

    def _make_animation(self, name: bytes, duration: int) -> QPropertyAnimation:
        animation = QPropertyAnimation(self, name, self)
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        return animation

    # -- Animated properties ------------------------------------------------

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        self._progress = value
        self.update()

    progress = Property(float, _get_progress, _set_progress)

    def _get_squeeze(self) -> float:
        return self._squeeze

    def _set_squeeze(self, value: float) -> None:
        self._squeeze = value
        self.update()

    squeeze = Property(float, _get_squeeze, _set_squeeze)

    # -- State --------------------------------------------------------------

    def set_checked_silently(self, checked: bool, *, animate: bool) -> None:
        """Set the state without emitting ``toggled`` (slides when ``animate``)."""
        was_blocked = self.blockSignals(True)
        self.setChecked(checked)
        self.blockSignals(was_blocked)

        if animate:
            self._slide_to(checked)
        else:
            self._slide.stop()
            self._set_progress(1.0 if checked else 0.0)

    def _slide_to(self, checked: bool) -> None:
        self._run(self._slide, self._progress, 1.0 if checked else 0.0)

    def _squeeze_to(self, target: float) -> None:
        self._run(self._press, self._squeeze, target)

    @staticmethod
    def _run(animation: QPropertyAnimation, current: float, target: float) -> None:
        """Animate from the current value, so a mid-flight change never jumps."""
        animation.stop()
        animation.setStartValue(current)
        animation.setEndValue(target)
        animation.start()

    # -- Painting -----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            track = QRectF(self.rect())
            radius = track.height() / 2

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(blend(QColor(SWITCH_OFF), QColor(SWITCH_ON), self._progress))
            painter.drawRoundedRect(track, radius, radius)

            painter.setBrush(QColor(SWITCH_KNOB_COLOR))
            painter.drawRoundedRect(self._knob_rect(), SWITCH_KNOB / 2, SWITCH_KNOB / 2)

            if self.hasFocus():
                painter.setPen(QPen(QColor(FOCUS_COLOR), FOCUS_WIDTH))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                inset = FOCUS_WIDTH / 2
                painter.drawRoundedRect(
                    track.adjusted(inset, inset, -inset, -inset), radius, radius
                )
        finally:
            painter.end()

    def _knob_rect(self) -> QRectF:
        stretch = SWITCH_SQUEEZE * self._squeeze
        travel = SWITCH_WIDTH - 2 * SWITCH_PAD - SWITCH_KNOB
        # The knob grows toward the inside: its outer edge stays put.
        left = SWITCH_PAD + self._progress * travel - stretch * self._progress
        return QRectF(left, SWITCH_PAD, SWITCH_KNOB + stretch, SWITCH_KNOB)