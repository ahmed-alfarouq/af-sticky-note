"""Sticky window geometry persistence (Phase 5G-A).

Provides clean saving, loading, and validation of the sticky note's
position and size using QSettings (standard lightweight INI storage).
Validates restored coordinates against visible screen work areas so the
window is never restored off-screen.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

try:
    from PySide6.QtCore import QPoint, QRect, QSettings, QSize
    from PySide6.QtGui import QGuiApplication
except ImportError:
    # Graceful fallback when running in non-GUI / headless backend test runners
    QSettings = None  # type: ignore
    QGuiApplication = None  # type: ignore
    QRect = None  # type: ignore

from app.config.settings import APP_NAME, ORG_NAME

logger = logging.getLogger(__name__)

# Default geometry fallbacks
DEFAULT_WIDTH = 380
DEFAULT_HEIGHT = 560
MIN_WIDTH = 320
MIN_HEIGHT = 420


class WindowGeometryManager:
    """Manages window position and size persistence across application sessions."""

    SETTINGS_GROUP = "WindowGeometry"
    KEY_X = "x"
    KEY_Y = "y"
    KEY_WIDTH = "width"
    KEY_HEIGHT = "height"

    def __init__(self, settings: Optional[Any] = None) -> None:
        if settings is not None:
            self._settings = settings
        elif QSettings is not None:
            self._settings = QSettings(ORG_NAME, APP_NAME)
        else:
            self._settings = None

    def save_geometry(self, x: int, y: int, width: int, height: int) -> None:
        """Persist window position and size to settings."""
        if self._settings is None:
            return
        try:
            self._settings.beginGroup(self.SETTINGS_GROUP)
            self._settings.setValue(self.KEY_X, x)
            self._settings.setValue(self.KEY_Y, y)
            self._settings.setValue(self.KEY_WIDTH, width)
            self._settings.setValue(self.KEY_HEIGHT, height)
            self._settings.endGroup()
            if hasattr(self._settings, "sync"):
                self._settings.sync()
            logger.debug("Saved window geometry: x=%d, y=%d, w=%d, h=%d", x, y, width, height)
        except Exception as exc:
            logger.error("Failed to save window geometry: %s", exc)

    def load_geometry(self) -> Optional[Tuple[int, int, int, int]]:
        """Retrieve persisted geometry from settings, if available."""
        if self._settings is None:
            return None
        try:
            self._settings.beginGroup(self.SETTINGS_GROUP)
            has_x = self._settings.contains(self.KEY_X)
            has_y = self._settings.contains(self.KEY_Y)
            has_w = self._settings.contains(self.KEY_WIDTH)
            has_h = self._settings.contains(self.KEY_HEIGHT)

            if not (has_x and has_y and has_w and has_h):
                self._settings.endGroup()
                return None

            x = int(self._settings.value(self.KEY_X))
            y = int(self._settings.value(self.KEY_Y))
            w = int(self._settings.value(self.KEY_WIDTH))
            h = int(self._settings.value(self.KEY_HEIGHT))
            self._settings.endGroup()

            return (x, y, w, h)
        except Exception as exc:
            logger.error("Failed to load window geometry: %s", exc)
            return None

    def get_validated_geometry(self) -> Tuple[int, int, int, int]:
        """Return valid geometry for window startup.

        Validates against visible screen work areas. If saved geometry is
        missing or completely off-screen, returns a safe default placement
        (top-right work area or (100, 100)).
        """
        saved = self.load_geometry()
        if saved is not None:
            x, y, w, h = saved
            # Enforce minimum size boundaries
            w = max(w, MIN_WIDTH)
            h = max(h, MIN_HEIGHT)

            if self.is_geometry_visible(x, y, w, h):
                logger.info("Restoring validated geometry: x=%d, y=%d, w=%d, h=%d", x, y, w, h)
                return (x, y, w, h)
            else:
                logger.warning("Saved geometry (%d, %d, %d, %d) is off-screen; falling back to default", x, y, w, h)

        return self.get_default_geometry()

    @staticmethod
    def get_default_geometry() -> Tuple[int, int, int, int]:
        """Compute default top-right work area placement or fallback."""
        if QGuiApplication is not None:
            app = QGuiApplication.instance()
            if app is not None and hasattr(app, "primaryScreen"):
                screen = app.primaryScreen()
                if screen is not None:
                    work_area = screen.availableGeometry()
                    # Place in top-right with margin
                    w = DEFAULT_WIDTH
                    h = DEFAULT_HEIGHT
                    margin = 40
                    x = work_area.right() - w - margin
                    y = work_area.top() + margin
                    return (max(work_area.left(), x), max(work_area.top(), y), w, h)

        return (100, 100, DEFAULT_WIDTH, DEFAULT_HEIGHT)

    @staticmethod
    def is_geometry_visible(x: int, y: int, w: int, h: int) -> bool:
        """Check whether a meaningful portion (at least 60x60) of the window
        intersects an available screen work area."""
        if QGuiApplication is None or QRect is None:
            return True

        app = QGuiApplication.instance()
        if app is None or not hasattr(app, "screens"):
            return True

        screens = app.screens()
        if not screens:
            return True

        rect = QRect(x, y, w, h)
        for screen in screens:
            available = screen.availableGeometry()
            intersection = available.intersected(rect)
            # Ensure at least a usable header bar area is visible (60x60 px)
            if intersection.width() >= 60 and intersection.height() >= 60:
                return True

        return False
