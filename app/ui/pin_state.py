"""Pinned-state persistence for the sticky note window (v3 §4.1, §12).

The pinned flag is plain UI state stored in QSettings (same mechanism as
geometry): ``True`` = desktop-widget mode (spec default, matching the
historical Tool-window behavior), ``False`` = normal window. Session-only
states (completed-group expansion, last-used category) are deliberately not
handled here.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

try:
    from PySide6.QtCore import QSettings
except ImportError:
    QSettings = None  # type: ignore

from app.config.settings import APP_NAME, ORG_NAME

logger = logging.getLogger(__name__)


class PinStateManager:
    """Loads and stores the pinned flag; injectable settings for tests."""

    SETTINGS_GROUP = "WindowState"
    KEY_PINNED = "pinned"

    def __init__(self, settings: Optional[Any] = None) -> None:
        if settings is not None:
            self._settings = settings
        elif QSettings is not None:
            self._settings = QSettings(ORG_NAME, APP_NAME)
        else:
            self._settings = None

    def is_pinned(self) -> bool:
        """Current persisted state; pinned when unknown (historical behavior)."""
        if self._settings is None:
            return True
        try:
            self._settings.beginGroup(self.SETTINGS_GROUP)
            try:
                value = self._settings.value(self.KEY_PINNED, True)
            finally:
                self._settings.endGroup()
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1")
            return bool(value)
        except Exception as exc:
            logger.warning("Failed to read pin state: %s", exc)
            return True

    def save_pinned(self, pinned: bool) -> None:
        """Persist the state after it was successfully applied."""
        if self._settings is None:
            return
        try:
            self._settings.beginGroup(self.SETTINGS_GROUP)
            try:
                self._settings.setValue(self.KEY_PINNED, bool(pinned))
            finally:
                self._settings.endGroup()
        except Exception as exc:
            logger.warning("Failed to save pin state: %s", exc)
