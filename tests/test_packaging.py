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
