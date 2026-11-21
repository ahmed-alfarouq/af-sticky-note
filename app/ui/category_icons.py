"""Cached, filesystem-backed provider for category icons.

Icons live under ``assets/icons/<icon_key>.png`` (resolved through
:func:`get_bundle_dir`, so frozen builds work); SQLite stores only the
``icon_key``, never a path. All file reads happen here, once per key --
widgets reuse the cached ``QIcon`` and never touch the filesystem or paint
icons themselves. A missing/corrupt asset yields a graceful drawn fallback
instead of a crash.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtCore import Qt

from app.core.models import Category
from app.infrastructure.paths import get_bundle_dir
from app.ui.category_presentation import category_icon_key

logger = logging.getLogger(__name__)

ICONS_DIRNAME = "icons"
ICON_FILENAME_SUFFIX = ".png"
ICON_FILE_SIZE = 64

#: Only conservative keys may become file paths; anything else (including a
#: future user-supplied key with separators) falls back instead of escaping
#: the icons directory.
_SAFE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

__all__ = [
    "CategoryIconProvider",
    "ICONS_DIRNAME",
    "ICON_FILENAME_SUFFIX",
    "get_category_icons_dir",
]


def get_category_icons_dir() -> Path:
    """Absolute directory holding the ``<icon_key>.png`` category assets."""
    return get_bundle_dir() / "assets" / ICONS_DIRNAME


class CategoryIconProvider:
    """Resolve + cache one ``QIcon`` per category icon key."""

    def __init__(self, icons_dir: Optional[Path] = None) -> None:
        self._icons_dir = Path(icons_dir) if icons_dir is not None else get_category_icons_dir()
        self._cache: Dict[str, QIcon] = {}

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------
    def icon_path_for_key(self, icon_key: str) -> Optional[Path]:
        """Filesystem path for ``icon_key``, or None when unsafe/missing."""
        if not isinstance(icon_key, str) or not _SAFE_KEY_RE.match(icon_key):
            return None
        candidate = self._icons_dir / f"{icon_key}{ICON_FILENAME_SUFFIX}"
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            return None
        return None

    # ------------------------------------------------------------------
    # Icons (cached)
    # ------------------------------------------------------------------
    def icon_for_key(self, icon_key: str) -> QIcon:
        """Return the cached icon for ``icon_key`` (fallback when missing).

        Repeated calls for the same key return the identical ``QIcon``
        object: at most one filesystem read per key per provider lifetime.
        """
        key = icon_key if isinstance(icon_key, str) and icon_key else ""
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        icon = self._load_or_fallback(key)
        self._cache[key] = icon
        return icon

    def icon_for_category(self, category: Category) -> QIcon:
        """Icon for a :class:`Category` via its normalized icon key."""
        return self.icon_for_key(category_icon_key(category))

    def clear_cache(self) -> None:
        """Drop cached icons (tests / theme reload hooks)."""
        self._cache.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _load_or_fallback(self, key: str) -> QIcon:
        path = self.icon_path_for_key(key)
        if path is not None:
            try:
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    return QIcon(pixmap)
                logger.warning("Category icon is unreadable, using fallback: %s", path)
            except Exception as exc:  # pragma: no cover - Qt errors are platform specific
                logger.warning("Failed to load category icon %s: %s", path, exc)
        else:
            logger.debug("Category icon asset missing for key %r, using fallback", key)
        return self._fallback_icon()

    @staticmethod
    def _fallback_icon() -> QIcon:
        """Small neutral dot in the app palette; never touches the disk."""
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(QPen(QColor("#8FB8D8"), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(7, 7, 18, 18)
        finally:
            painter.end()
        return QIcon(pixmap)
