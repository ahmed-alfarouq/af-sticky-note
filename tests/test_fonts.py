"""Tests for font loading and path discovery helpers."""
from pathlib import Path
import tempfile

from app.infrastructure.fonts import get_default_font_family, load_application_fonts
from app.infrastructure.paths import get_fonts_dir


def test_fonts_directory_exists_and_contains_thmanyah_fonts():
    fonts_dir = get_fonts_dir()
    assert fonts_dir.exists()
    assert fonts_dir.is_dir()

    # The repository bundles 15 Thmanyah font files (otf or woff2)
    font_files = list(fonts_dir.glob("*.otf")) + list(fonts_dir.glob("*.woff2"))
    assert len(font_files) == 15
    for font_path in font_files:
        assert font_path.stat().st_size > 0


def test_load_application_fonts_graceful_on_missing_dir():
    missing_dir = Path("/nonexistent/directory/for/fonts")
    registered = load_application_fonts(missing_dir)
    assert registered == []


def test_load_application_fonts_graceful_on_empty_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        registered = load_application_fonts(Path(tmp_dir))
        assert registered == []


def test_default_font_family_contains_fallbacks():
    family = get_default_font_family()
    assert "Thmanyah Sans" in family
    assert "sans-serif" in family
