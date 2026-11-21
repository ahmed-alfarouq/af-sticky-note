"""Color blending for animated controls."""

from __future__ import annotations

from PySide6.QtGui import QColor

__all__ = ["blend"]


def blend(start: QColor, end: QColor, amount: float) -> QColor:
    """Linear mix of two colors; ``amount`` 0 gives ``start``, 1 gives ``end``."""
    t = max(0.0, min(1.0, amount))
    return QColor(
        round(start.red() + (end.red() - start.red()) * t),
        round(start.green() + (end.green() - start.green()) * t),
        round(start.blue() + (end.blue() - start.blue()) * t),
        round(start.alpha() + (end.alpha() - start.alpha()) * t),
    )