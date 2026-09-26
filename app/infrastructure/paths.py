"""Application-data and bundled resource path resolution.

Centralizes path handling for both source-development runs and packaged
PyInstaller environments (via sys._MEIPASS or executable directory).
Guarantees user data is cleanly separated from read-only bundled assets.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_FOLDER_NAME = "DailySticky"


def get_bundle_dir() -> Path:
    """Return the base directory for bundled read-only application resources.

    - Under PyInstaller: sys._MEIPASS (one-file) or executable directory (one-folder).
    - Under source development: project repository root.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def get_app_data_dir() -> Path:
    """Return the directory Daily Sticky should store its mutable data in.

    Windows: %LOCALAPPDATA%\\DailySticky
    Fallback: ~/.dailysticky (covers non-Windows dev environments).
    """
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_FOLDER_NAME
    return Path.home() / ".dailysticky"


def get_database_path() -> Path:
    """Return the absolute path to the SQLite user database."""
    data_dir = get_app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "daily_sticky.db"


def get_quotes_path() -> Path:
    """Return the path to the bundled data/quotes.txt seed file."""
    return get_bundle_dir() / "data" / "quotes.txt"


def get_fonts_dir() -> Path:
    """Return the path to the bundled fonts directory."""
    return get_bundle_dir() / "fonts" / "thmanyah"


def get_logo_path() -> Path:
    """Return the path to the bundled application logo image."""
    return get_bundle_dir() / "assets" / "logo.png"

