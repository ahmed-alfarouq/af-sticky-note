"""Screen-to-screen transition painted from snapshots.

Instead of animating live widgets (which flickers when graphics effects
stack on a translucent window), each screen is captured once as a pixmap and
this overlay paints those pixmaps at an offset that changes over time.
Nothing live moves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

__all__ = ["PageTransition", "Sprite"]


@dataclass(frozen=True)
class Sprite:
    """One snapshot and how it moves.

    ``origin`` is where the snapshot rests, in the host's coordinates. Over
    ``duration_ms`` it moves from the first to the second ``offset`` (relative
    to ``origin``), following ``curve``.
    """

    pixmap: QPixmap
    origin: QPoint
    offset: Tuple[QPoint, QPoint]
    duration_ms: int
    curve: QEasingCurve.Type


def _mix(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


class PageTransition(QWidget):
    """Transparent overlay that plays a list of :class:`Sprite` animations."""

    #: Every sprite reached its final state; the overlay hides right after.
    finished = Signal()

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self._sprites: List[Sprite] = []
        self._elapsed_ms = 0

        self._clock = QVariantAnimation(self)
        self._clock.setEasingCurve(QEasingCurve.Type.Linear)
        self._clock.valueChanged.connect(self._on_tick)
        self._clock.finished.connect(self._on_finished)

        host.installEventFilter(self)  # keep covering the host when it resizes
        self.hide()

    def play(self, sprites: Sequence[Sprite]) -> None:
        self._clock.stop()
        self._sprites = list(sprites)
        self._elapsed_ms = 0

        total = max((s.duration_ms for s in self._sprites), default=1)
        self._clock.setStartValue(0)
        self._clock.setEndValue(total)
        self._clock.setDuration(total)

        self._cover_host()
        self.raise_()
        self.show()
        self._clock.start()

    def _on_tick(self, value) -> None:
        self._elapsed_ms = int(value)
        self.update()

    def _on_finished(self) -> None:
        self.finished.emit()  # the caller shows the real screen first...
        self.hide()           # ...then the overlay goes, in the same turn

    # -- Covering the host --------------------------------------------------

    def _cover_host(self) -> None:
        host = self.parentWidget()
        if host is not None:
            self.setGeometry(host.rect())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._cover_host()
        return super().eventFilter(watched, event)

    # -- Painting and input -------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            for sprite in self._sprites:
                self._paint_sprite(painter, sprite)
        finally:
            painter.end()

    def _paint_sprite(self, painter: QPainter, sprite: Sprite) -> None:
        raw = self._elapsed_ms / max(1, sprite.duration_ms)
        progress = QEasingCurve(sprite.curve).valueForProgress(max(0.0, min(1.0, raw)))

        start, end = sprite.offset
        position = QPointF(
            sprite.origin.x() + _mix(start.x(), end.x(), progress),
            sprite.origin.y() + _mix(start.y(), end.y(), progress),
        )

        painter.drawPixmap(position, sprite.pixmap)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        event.accept()  # input is ignored while the screens swap

    def contextMenuEvent(self, event) -> None:  # noqa: N802 - Qt naming
        event.accept()