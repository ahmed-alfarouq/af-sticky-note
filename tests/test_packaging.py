"""Tests for Packaging, Bundled Resource Paths, and Versioning (Phase 5O)."""
import os
import sys
from pathlib import Path
import pytest

from app.config.settings import APP_NAME, APP_VERSION
from app.infrastructure.paths import (
    get_app_data_dir,
    get_bundle_dir,
    get_database_path,
    get_fonts_dir,
    get_quotes_path,
)
from app.platform.windows.startup import get_default_executable_command


def test_version_and_metadata_configured():
    """Verify application version and name are properly defined."""
    assert APP_NAME == "Daily Sticky"
    assert APP_VERSION == "0.5.0"


def test_resource_paths_point_to_valid_files():
    """Verify quotes file, fonts directory, and logo resolve correctly in dev environment."""
    quotes_file = get_quotes_path()
    assert quotes_file.exists()
    assert quotes_file.is_file()

    fonts_dir = get_fonts_dir()
    assert fonts_dir.exists()
    assert fonts_dir.is_dir()

    from app.infrastructure.paths import get_logo_path
    logo_file = get_logo_path()
    assert logo_file.exists()
    assert logo_file.is_file()
    assert logo_file.name == "logo.png"


def test_bundle_dir_meipass_override():
    """Verify get_bundle_dir resolves to sys._MEIPASS when frozen under PyInstaller."""
    fake_temp = Path("/tmp/fake_meipass_dir")
    original = getattr(sys, "_MEIPASS", None)
    try:
        sys._MEIPASS = str(fake_temp)
        resolved = get_bundle_dir()
        assert resolved == fake_temp
    finally:
        if original is not None:
            sys._MEIPASS = original
        else:
            delattr(sys, "_MEIPASS")


def test_user_data_path_independent_of_bundle():
    """Verify mutable user data (database) is completely isolated from the read-only bundle directory."""
    bundle_dir = get_bundle_dir()
    data_dir = get_app_data_dir()
    db_path = get_database_path()

    # User data path must never be inside bundle directory
    assert not str(db_path).startswith(str(bundle_dir))
    assert db_path.name == "daily_sticky.db"


def test_startup_command_packaged_compatibility():
    """Verify that when sys.frozen is True, get_default_executable_command uses the executable path."""
    orig_frozen = getattr(sys, "frozen", None)
    orig_exe = sys.executable
    try:
        sys.frozen = True
        fake_exe = "/opt/DailySticky/DailySticky"
        sys.executable = fake_exe

        cmd = get_default_executable_command()
        assert cmd == f'"{os.path.abspath(fake_exe)}"'
        # Must NOT contain 'python' or source script paths
        assert "run.py" not in cmd
        assert "main.py" not in cmd
    finally:
        if orig_frozen is not None:
            sys.frozen = orig_frozen
        else:
            if hasattr(sys, "frozen"):
                delattr(sys, "frozen")
        sys.executable = orig_exe


def _read_spec_text():
    spec_path = Path(__file__).resolve().parent.parent / "packaging" / "DailySticky.spec"
    assert spec_path.is_file(), "packaging/DailySticky.spec must exist"
    return spec_path.read_text(encoding="utf-8")


def test_spec_bundles_migrations_directory():
    """The migrations folder (not individual files) is bundled, so new
    migrations like 005 are packaged without spec edits."""
    assert "app/database/migrations" in _read_spec_text()


def test_all_migration_files_exist_and_follow_convention():
    """Every migration file matches NNN_description.sql and the category
    migration is present."""
    import re

    migrations_dir = Path(__file__).resolve().parent.parent / "app" / "database" / "migrations"
    files = sorted(migrations_dir.glob("*.sql"))
    assert len(files) >= 5
    for path in files:
        assert re.match(r"^\d+_.*\.sql$", path.name), path.name
    assert (migrations_dir / "005_task_categories.sql").is_file()


def test_spec_hiddenimports_cover_category_repository():
    """The category repository module must be importable in the frozen app."""
    assert "app.database.category_repository" in _read_spec_text()


def test_spec_bundles_category_icons_directory():
    """Category icon assets must ship inside the packaged build."""
    assert '"assets/icons"' in _read_spec_text() or "'assets/icons'" in _read_spec_text()
    assert "assets" in _read_spec_text() and "icons" in _read_spec_text()


def test_spec_hiddenimports_cover_category_ui_modules():
    """New Phase 7B service/UI modules must be importable frozen."""
    spec = _read_spec_text()
    for module in (
        "app.core.services.category_service",
        "app.ui.category_icons",
        "app.ui.category_presentation",
        "app.ui.widgets.category_selector",
    ):
        assert module in spec, f"{module} missing from spec hiddenimports"


def test_all_required_category_icon_assets_exist():
    """Every initial category id resolves to a real icon file."""
    icons_dir = Path(__file__).resolve().parent.parent / "assets" / "icons"
    assert icons_dir.is_dir()
    for key in ("religion", "work", "life", "general"):
        path = icons_dir / f"{key}.png"
        assert path.is_file(), f"missing icon asset for category {key!r}"
        assert path.stat().st_size > 0
