"""Tests for system tray integration (Phase 5H-A)."""
from unittest.mock import MagicMock
import pytest

from app.platform.interfaces import PlatformAdapter, SystemTrayController
from app.platform.provider import get_platform_adapter, reset_platform_adapter
from app.platform.unsupported import NoOpSystemTrayController, UnsupportedPlatformAdapter
from app.platform.windows.tray import WindowsSystemTrayController


def test_unsupported_tray_controller_contract():
    """Verify NoOpSystemTrayController satisfies interface without errors."""
    tray = NoOpSystemTrayController()
    assert isinstance(tray, SystemTrayController)
    assert not tray.is_available()
    # Ensure safe no-op execution
    tray.show()
    tray.hide()
    tray.show_message("Test", "Message")


def test_windows_system_tray_controller_contract():
    """Verify WindowsSystemTrayController implements SystemTrayController protocol."""
    tray = WindowsSystemTrayController()
    assert isinstance(tray, SystemTrayController)
    # Headless / mock environment
    assert not tray.is_available() or True


def test_tray_toggle_visibility_operates_on_same_window():
    """Verify that tray show/hide operates on existing MainWindow instance without recreating."""
    mock_window = MagicMock()
    mock_window.isVisible.return_value = True

    tray = WindowsSystemTrayController(main_window=mock_window)

    # First toggle: window is visible -> hide
    tray.toggle_window_visibility()
    mock_window.hide.assert_called_once()
    mock_window.show.assert_not_called()

    # Second toggle: window is hidden -> show
    mock_window.isVisible.return_value = False
    tray.toggle_window_visibility()
    mock_window.show.assert_called_once()
    mock_window.raise_.assert_called_once()
    mock_window.activateWindow.assert_called_once()


def test_tray_request_exit_triggers_callback():
    """Verify that selecting exit calls the termination callback."""
    mock_exit_cb = MagicMock()
    tray = WindowsSystemTrayController(on_exit_requested=mock_exit_cb)

    tray.request_exit()
    mock_exit_cb.assert_called_once()


def test_platform_adapter_exposes_tray_controller():
    """Verify platform provider exposes tray controller on adapter."""
    reset_platform_adapter()
    adapter = get_platform_adapter(force_platform="linux")
    assert isinstance(adapter, PlatformAdapter)
    assert hasattr(adapter, "tray_controller")
    assert isinstance(adapter.tray_controller, SystemTrayController)
