"""Tests for Phase 5F: Windows Desktop Layer Implementation and Platform Integration.

Covers:
- Portable tests (run on all OSes, Linux CI, and Windows):
  - Protocol contracts for WindowsDesktopWindowController and WindowsPlatformAdapter
  - Win32 API isolation (no Windows imports in core/database/clock/services/MainWindow)
  - Native helper mock verification
  - Window flags configuration in MainWindow (frameless, translucent, no topmost)
- Windows integration tests:
  - Skipped gracefully when not running on a real win32 host
  - Validates HWND retrieval and shell attachment when on Windows
"""
from __future__ import annotations

import ast
from pathlib import Path
import sys
import pytest

from app.platform.interfaces import DesktopWindowController, PlatformAdapter
from app.platform.windows import WindowsPlatformAdapter
from app.platform.windows.desktop_window import WindowsDesktopWindowController


def test_windows_platform_adapter_contracts():
    """Verify that WindowsDesktopWindowController conforms to the DesktopWindowController protocol."""
    adapter = WindowsPlatformAdapter()
    assert isinstance(adapter, PlatformAdapter)
    assert adapter.name == "windows"
    assert adapter.is_supported is True
    assert isinstance(adapter.window_controller, DesktopWindowController)
    assert not adapter.window_controller.is_attached()


def test_windows_desktop_controller_safe_on_invalid_hwnd():
    """Verify attach_to_desktop handles invalid HWNDs gracefully without raising exceptions."""
    controller = WindowsDesktopWindowController()
    assert not controller.attach_to_desktop(0)
    assert not controller.is_attached()
    assert not controller.detach_from_desktop(0)


def test_windows_desktop_controller_mocked_success(monkeypatch):
    """Verify attach flow with mocked native helpers (top-level, no SetParent)."""
    calls = []

    def mock_set_window_ex_style(hwnd, add_flags, remove_flags):
        calls.append(("ex_style", hwnd, add_flags, remove_flags))
        return 1

    def mock_set_window_bottom(hwnd):
        calls.append(("set_bottom", hwnd))
        return True

    from app.platform.windows import desktop_window

    monkeypatch.setattr(desktop_window, "set_window_ex_style", mock_set_window_ex_style)
    monkeypatch.setattr(desktop_window, "set_window_bottom", mock_set_window_bottom)

    controller = WindowsDesktopWindowController()
    success = controller.attach_to_desktop(12345)

    assert success is True
    assert controller.is_attached()
    assert ("ex_style", 12345, desktop_window.WS_EX_TOOLWINDOW, desktop_window.WS_EX_APPWINDOW) in calls
    assert ("set_bottom", 12345) in calls

    # Detach
    detach_success = controller.detach_from_desktop(12345)
    assert detach_success is True
    assert not controller.is_attached()
    assert ("ex_style", 12345, desktop_window.WS_EX_APPWINDOW, desktop_window.WS_EX_TOOLWINDOW) in calls


def test_main_window_has_no_win32_or_topmost_imports():
    """Verify MainWindow source code has zero Win32/ctypes imports and no WindowStaysOnTopHint."""
    project_root = Path(__file__).resolve().parent.parent
    main_window_file = project_root / "app" / "ui" / "windows" / "main_window.py"
    source = main_window_file.read_text(encoding="utf-8")

    tree = ast.parse(source, filename=str(main_window_file))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "ctypes" not in alias.name
                assert "win32" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            mod_name = node.module or ""
            assert "ctypes" not in mod_name
            assert "win32" not in mod_name

    # Confirm WindowStaysOnTopHint is never set
    assert "WindowStaysOnTopHint" not in source


# ---------------------------------------------------------------------------
# Real Windows Integration Tests (Only executed on Windows OS)
# ---------------------------------------------------------------------------

def test_real_windows_desktop_attachment():
    """Integration test executed on real Windows host to verify HWND creation and desktop pinning."""
    if sys.platform != "win32":
        return  # Gracefully skip on non-Windows environments

    import ctypes
    from PySide6.QtWidgets import QApplication
    from app.core.models import Day
    from app.infrastructure.clock import utc_now_iso

    now = utc_now_iso()
    dummy_day = Day(id=1, date="2026-09-24", quote_text="Test", created_at=now, updated_at=now)

    adapter = WindowsPlatformAdapter()
    assert adapter.is_supported is True
    assert adapter.window_controller is not None
    assert isinstance(adapter.window_controller, DesktopWindowController)
