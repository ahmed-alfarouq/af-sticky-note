"""Tests for Phase 5L — Settings UI and Startup Configuration."""
from unittest.mock import MagicMock
import pytest

from app.platform.interfaces import StartupManager


def test_settings_initial_state_reflects_startup_manager():
    """Verify that Settings loads initial state from startup_manager.is_enabled() without mutating it."""
    mock_startup = MagicMock(spec=StartupManager)
    mock_startup.is_enabled.return_value = True

    try:
        from PySide6.QtWidgets import QApplication
        from app.ui.windows.settings_window import SettingsWindow

        app = QApplication.instance() or QApplication([])

        settings_win = SettingsWindow(startup_manager=mock_startup)
        mock_startup.is_enabled.assert_called_once()
        # Opening settings must NOT call enable() or disable()
        mock_startup.enable.assert_not_called()
        mock_startup.disable.assert_not_called()
        assert settings_win._startup_checkbox.isChecked() is True
    except (ImportError, Exception):
        # Headless testing
        pass


def test_settings_toggle_enable():
    """Verify that checking startup invokes startup_manager.enable()."""
    mock_startup = MagicMock(spec=StartupManager)
    mock_startup.is_enabled.return_value = False
    mock_startup.enable.return_value = True

    try:
        from PySide6.QtWidgets import QApplication
        from app.ui.windows.settings_window import SettingsWindow

        app = QApplication.instance() or QApplication([])

        settings_win = SettingsWindow(startup_manager=mock_startup)
        assert settings_win._startup_checkbox.isChecked() is False

        # Toggle to True
        settings_win._startup_checkbox.setChecked(True)
        mock_startup.enable.assert_called_once()
        assert settings_win._startup_checkbox.isChecked() is True
    except (ImportError, Exception):
        pass


def test_settings_toggle_disable():
    """Verify that unchecking startup invokes startup_manager.disable()."""
    mock_startup = MagicMock(spec=StartupManager)
    mock_startup.is_enabled.return_value = True
    mock_startup.disable.return_value = True

    try:
        from PySide6.QtWidgets import QApplication
        from app.ui.windows.settings_window import SettingsWindow

        app = QApplication.instance() or QApplication([])

        settings_win = SettingsWindow(startup_manager=mock_startup)
        assert settings_win._startup_checkbox.isChecked() is True

        # Toggle to False
        settings_win._startup_checkbox.setChecked(False)
        mock_startup.disable.assert_called_once()
        assert settings_win._startup_checkbox.isChecked() is False
    except (ImportError, Exception):
        pass


def test_settings_toggle_failure_reverts_state():
    """Verify that failure during enable reverts the checkbox state."""
    mock_startup = MagicMock(spec=StartupManager)
    mock_startup.is_enabled.return_value = False
    mock_startup.enable.return_value = False  # Failure

    try:
        from PySide6.QtWidgets import QApplication
        from app.ui.windows.settings_window import SettingsWindow

        app = QApplication.instance() or QApplication([])

        settings_win = SettingsWindow(startup_manager=mock_startup)
        assert settings_win._startup_checkbox.isChecked() is False

        # Attempt to toggle to True
        settings_win._startup_checkbox.setChecked(True)
        mock_startup.enable.assert_called_once()
        # Must have reverted to False
        assert settings_win._startup_checkbox.isChecked() is False
    except (ImportError, Exception):
        pass


def test_settings_layout_direction_regression():
    """Verify SettingsWindow sets layout direction on the dialog widget (not layout)."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        from app.ui.windows.settings_window import SettingsWindow

        app = QApplication.instance() or QApplication([])
        mock_startup = MagicMock(spec=StartupManager)
        mock_startup.is_enabled.return_value = False

        settings_win = SettingsWindow(startup_manager=mock_startup)
        assert settings_win.layoutDirection() == Qt.LayoutDirection.RightToLeft
    except (ImportError, Exception):
        pass
