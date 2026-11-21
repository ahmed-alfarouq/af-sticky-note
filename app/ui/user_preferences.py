"""The user's saved preferences (settings screen), stored in QSettings.

Same mechanism as the window geometry and pin state. Every setter validates,
saves only when the value really changed, and emits ``changed(key)`` so the
parts of the app that show the preference can update at once.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import QObject, QSettings, Signal

from app.config.settings import APP_NAME, ORG_NAME
from app.core.models import DEFAULT_CATEGORY_ID, TaskPriority
from app.ui.date_presentation import CalendarKind
from app.ui.priority_presentation import DEFAULT_TASK_PRIORITY

__all__ = ["UserPreferences", "DEFAULT_WEEK_START"]

logger = logging.getLogger(__name__)

#: Saturday, as a Python weekday (Monday = 0 ... Sunday = 6).
DEFAULT_WEEK_START = 5


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1")
    return default if value is None else bool(value)


class UserPreferences(QObject):
    """Typed access to the saved preferences."""

    #: A preference changed; the argument is one of the ``KEY`` names below.
    changed = Signal(str)

    SETTINGS_GROUP = "Preferences"
    CALENDAR = "calendar"
    WEEK_START = "week_start"
    DEFAULT_CATEGORY = "default_category"
    DEFAULT_PRIORITY = "default_priority"
    DAILY_MESSAGE = "daily_message"

    def __init__(
        self,
        settings: Optional[QSettings] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings if settings is not None else QSettings(ORG_NAME, APP_NAME)

    # -- Storage ------------------------------------------------------------

    def _read(self, key: str, default: Any) -> Any:
        try:
            self._settings.beginGroup(self.SETTINGS_GROUP)
            try:
                return self._settings.value(key, default)
            finally:
                self._settings.endGroup()
        except Exception as exc:
            logger.warning("Failed to read preference %s: %s", key, exc)
            return default

    def _write(self, key: str, value: Any) -> None:
        try:
            self._settings.beginGroup(self.SETTINGS_GROUP)
            try:
                self._settings.setValue(key, value)
            finally:
                self._settings.endGroup()
        except Exception as exc:
            logger.warning("Failed to save preference %s: %s", key, exc)

    def _update(self, key: str, current: Any, new: Any, stored: Any) -> None:
        """Save ``stored`` and announce the change, unless nothing changed."""
        if new == current:
            return
        self._write(key, stored)
        self.changed.emit(key)

    # -- Calendar -----------------------------------------------------------

    @property
    def calendar(self) -> CalendarKind:
        try:
            return CalendarKind(str(self._read(self.CALENDAR, CalendarKind.HIJRI.value)))
        except ValueError:
            return CalendarKind.HIJRI

    def set_calendar(self, calendar: CalendarKind) -> None:
        self._update(self.CALENDAR, self.calendar, calendar, calendar.value)

    # -- First day of the week ----------------------------------------------

    @property
    def week_start(self) -> int:
        """First day of the week as a Python weekday (Monday = 0 ... Sunday = 6)."""
        try:
            value = int(self._read(self.WEEK_START, DEFAULT_WEEK_START))
        except (TypeError, ValueError):
            return DEFAULT_WEEK_START
        return value if 0 <= value <= 6 else DEFAULT_WEEK_START

    def set_week_start(self, weekday: int) -> None:
        if not 0 <= weekday <= 6:
            raise ValueError(f"weekday must be 0..6, got {weekday}")
        self._update(self.WEEK_START, self.week_start, weekday, weekday)

    # -- Defaults for a new task ---------------------------------------------

    @property
    def default_category_id(self) -> str:
        value = str(self._read(self.DEFAULT_CATEGORY, DEFAULT_CATEGORY_ID) or "")
        return value or DEFAULT_CATEGORY_ID

    def set_default_category_id(self, category_id: str) -> None:
        if not category_id:
            raise ValueError("category_id must not be empty")
        self._update(self.DEFAULT_CATEGORY, self.default_category_id, category_id, category_id)

    @property
    def default_priority(self) -> TaskPriority:
        try:
            return TaskPriority(str(self._read(self.DEFAULT_PRIORITY, DEFAULT_TASK_PRIORITY.value)))
        except ValueError:
            return DEFAULT_TASK_PRIORITY

    def set_default_priority(self, priority: TaskPriority) -> None:
        self._update(self.DEFAULT_PRIORITY, self.default_priority, priority, priority.value)

    # -- Daily message ---------------------------------------------------------

    @property
    def daily_message(self) -> bool:
        return _as_bool(self._read(self.DAILY_MESSAGE, True), True)

    def set_daily_message(self, enabled: bool) -> None:
        self._update(self.DAILY_MESSAGE, self.daily_message, bool(enabled), bool(enabled))