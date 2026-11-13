"""Staggered entrance: blocks fade in and rise one after another."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, cast

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QSequentialAnimationGroup,
)
from PySide6.QtWidgets import QGraphicsEffect, QGraphicsOpacityEffect, QWidget

from app.ui.styles.settings_style import REVEAL_MS, REVEAL_RISE, REVEAL_STAGGER_MS

__all__ = ["Reveal"]


class Reveal(QObject):
    """Plays the entrance for ``blocks`` (call :meth:`start` once they are laid out).

    Blocks move only while the animation runs; afterwards they are back at the
    positions the layout gave them and carry no graphics effect.
    """

    def __init__(self, blocks: Sequence[QWidget], parent: QObject) -> None:
        super().__init__(parent)
        self._blocks: List[QWidget] = list(blocks)
        self._rests: Dict[QWidget, QPoint] = {}
        self._group: Optional[QParallelAnimationGroup] = None

    def start(self) -> None:
        self.finish()

        group = QParallelAnimationGroup(self)
        for index, block in enumerate(self._blocks):
            rest = block.pos()
            self._rests[block] = rest

            effect = QGraphicsOpacityEffect(block)
            effect.setOpacity(0.0)
            block.setGraphicsEffect(effect)
            lowered = rest + QPoint(0, REVEAL_RISE)
            block.move(lowered)

            rise = QPropertyAnimation(block, b"pos")
            rise.setStartValue(lowered)
            rise.setEndValue(rest)
            fade = QPropertyAnimation(effect, b"opacity")
            fade.setStartValue(0.0)
            fade.setEndValue(1.0)

            together = QParallelAnimationGroup()
            for animation in (rise, fade):
                animation.setDuration(REVEAL_MS)
                animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                together.addAnimation(animation)

            delayed = QSequentialAnimationGroup()
            delayed.addPause(index * REVEAL_STAGGER_MS)
            delayed.addAnimation(together)
            group.addAnimation(delayed)

        group.finished.connect(self.finish)
        self._group = group
        group.start()

    def finish(self) -> None:
        """Stop now and put every block back in its final state."""
        group, self._group = self._group, None
        if group is not None:
            group.stop()
            group.deleteLater()

        for block, rest in self._rests.items():
            block.move(rest)
            block.setGraphicsEffect(cast(QGraphicsEffect, None))
        self._rests.clear()