"""Font discovery and application registration helper for Thmanyah fonts."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def load_application_fonts(fonts_dir: Path) -> List[int]:
    """Discover and register all font files (.woff2, .ttf, .otf) in fonts_dir.

    Uses PySide6.QtGui.QFontDatabase.
    Gracefully logs and continues on error; does NOT crash startup if fonts fail.
    Returns the list of registered font IDs.
    """
    if not fonts_dir.exists() or not fonts_dir.is_dir():
        logger.warning("Fonts directory does not exist: %s", fonts_dir)
        return []

    try:
        from PySide6.QtGui import QFontDatabase
    except ImportError:
        logger.warning("PySide6.QtGui is not available; skipping font registration.")
        return []

    font_files = sorted(
        p for p in fonts_dir.iterdir()
        if p.is_file() and p.suffix.lower() in (".woff2", ".ttf", ".otf")
    )

    registered_ids = []
    for font_path in font_files:
        try:
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id == -1:
                logger.warning("QFontDatabase failed to load font: %s", font_path.name)
            else:
                registered_ids.append(font_id)
                families = QFontDatabase.applicationFontFamilies(font_id)
                logger.debug("Loaded font %s -> families: %s", font_path.name, families)
        except Exception as exc:
            logger.warning("Unexpected error loading font %s: %s", font_path.name, exc)

    logger.info("Successfully registered %d font files from %s", len(registered_ids), fonts_dir)
    return registered_ids


def get_default_font_family() -> str:
    """Return the preferred font family string with sensible fallbacks."""
    return '"Thmanyah Sans", "Thmanyah Serif Text", "Segoe UI", "Tahoma", "Arial", sans-serif'
