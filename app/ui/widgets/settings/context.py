"""What the settings screen needs from the rest of the app."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from app.core.models import Category
from app.platform.interfaces import StartupManager
from app.ui.user_preferences import UserPreferences

__all__ = ["SettingsContext"]


@dataclass(frozen=True)
class SettingsContext:
    """Collaborators of the settings screen (it owns no state of its own)."""

    startup_manager: StartupManager
    preferences: UserPreferences
    categories: Sequence[Category]               # active categories, display order
    is_pinned: Callable[[], bool]
    set_pinned: Callable[[bool], bool]           # True when the change was applied