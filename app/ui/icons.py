"""Vector icon utility: Phosphor glyphs via qtawesome (v3 §1.4).

Colors are applied in code so one glyph serves every state. Icons are built
once per ``(key, color)`` and cached; never call :func:`icon` inside
``paintEvent``. Category PNGs and ``CategoryIconProvider`` are untouched by
this module (category migration is a later phase).
"""
from __future__ import annotations

import os

# Binding selection mirrors app/main.py for direct imports (tests, tools):
# qtawesome resolves its Qt binding through qtpy on first import.
os.environ.setdefault("QT_API", "pyside6")

from functools import lru_cache

import qtawesome as qta
from PySide6.QtGui import QIcon

GLYPHS = {
    "pin": "ph.push-pin-bold",
    "pin_active": "ph.push-pin-fill",
    "archive": "ph.archive-bold",
    "settings": "ph.gear-six-bold",
    "close": "ph.x-bold",
    "trash": "ph.trash-bold",
    "check": "ph.check-bold",
    "tag": "ph.tag-bold",
    "caret_down": "ph.caret-down-bold",
    "caret_left": "ph.caret-left-bold",
    "plus": "ph.plus-bold",
}

__all__ = ["GLYPHS", "icon"]


@lru_cache(maxsize=None)
def icon(key: str, color: str) -> QIcon:
    """Return the cached icon for ``key`` rendered in ``color``.

    Raises :exc:`KeyError` for unknown keys (fail loudly, never substitute).
    """
    return qta.icon(GLYPHS[key], color=color)
