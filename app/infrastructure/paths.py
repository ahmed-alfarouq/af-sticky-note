"""Application-data path resolution.

Minimal placeholder for Phase 2: resolves a per-user data directory
without hardcoding machine-specific paths. A dedicated platform layer
will formalize packaged-vs-dev path handling in a later phase.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_FOLDER_NAME = "DailySticky"


def get_app_data_dir() -> Path:
    """Return the directory Daily Sticky should store its data in.

    Windows: %LOCALAPPDATA%\\DailySticky
    Fallback: ~/.dailysticky (covers non-Windows dev environments).
    """
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_FOLDER_NAME
    return Path.home() / ".dailysticky"


def get_database_path() -> Path:
    data_dir = get_app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "daily_sticky.db"