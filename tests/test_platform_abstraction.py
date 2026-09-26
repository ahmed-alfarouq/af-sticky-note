"""Tests for Phase 5E: Platform abstraction, interfaces, factory provider, and isolation."""
from __future__ import annotations

import ast
from pathlib import Path
import pytest

from app.platform import (
    DesktopWindowController,
    NoOpDesktopWindowController,
    NoOpStartupManager,
    NoOpSystemTrayController,
    PlatformAdapter,
    StartupManager,
    SystemTrayController,
    UnsupportedPlatformAdapter,
    get_platform_adapter,
    reset_platform_adapter,
)


def test_platform_protocols_contracts():
    """Verify that NoOp implementations fulfill runtime_checkable protocols."""
    win_ctrl = NoOpDesktopWindowController()
    assert isinstance(win_ctrl, DesktopWindowController)
    assert not win_ctrl.is_attached()
    assert not win_ctrl.attach_to_desktop(12345)
    assert not win_ctrl.detach_from_desktop(12345)

    startup_mgr = NoOpStartupManager()
    assert isinstance(startup_mgr, StartupManager)
    assert not startup_mgr.is_enabled()
    assert not startup_mgr.enable()
    assert not startup_mgr.disable()

    tray_ctrl = NoOpSystemTrayController()
    assert isinstance(tray_ctrl, SystemTrayController)
    assert not tray_ctrl.is_available()
    tray_ctrl.show()  # Should not raise
    tray_ctrl.hide()  # Should not raise
    tray_ctrl.show_message("Test", "Message")  # Should not raise

    adapter = UnsupportedPlatformAdapter(platform_name="linux")
    assert isinstance(adapter, PlatformAdapter)
    assert adapter.name == "linux"
    assert not adapter.is_supported
    assert isinstance(adapter.window_controller, DesktopWindowController)
    assert isinstance(adapter.startup_manager, StartupManager)
    assert isinstance(adapter.tray_controller, SystemTrayController)


def test_platform_factory_resolution_and_singleton():
    """Verify provider returns consistent adapter and supports test overrides."""
    reset_platform_adapter()

    # Default host OS resolution (on Linux test runner, resolves to UnsupportedPlatformAdapter)
    adapter1 = get_platform_adapter()
    assert isinstance(adapter1, PlatformAdapter)
    adapter2 = get_platform_adapter()
    assert adapter1 is adapter2  # Cached singleton

    # Force platform override
    adapter_darwin = get_platform_adapter(force_platform="darwin")
    assert adapter_darwin.name == "darwin"
    assert not adapter_darwin.is_supported

    # Force win32 (returns WindowsPlatformAdapter in Phase 5F)
    adapter_win = get_platform_adapter(force_platform="win32")
    assert adapter_win.name == "windows"
    assert adapter_win.is_supported is True

    reset_platform_adapter()


def test_custom_platform_mock_injection():
    """Verify that a custom implementation can be plugged into the interface."""
    class CustomMockAdapter:
        @property
        def name(self) -> str:
            return "mock"

        @property
        def is_supported(self) -> bool:
            return True

        @property
        def window_controller(self) -> DesktopWindowController:
            return NoOpDesktopWindowController()

        @property
        def startup_manager(self) -> StartupManager:
            return NoOpStartupManager()

        @property
        def tray_controller(self) -> SystemTrayController:
            return NoOpSystemTrayController()

    mock = CustomMockAdapter()
    assert isinstance(mock, PlatformAdapter)
    assert mock.is_supported is True


def test_architectural_isolation_no_leaked_os_imports():
    """Static inspection verifying core, database, and services contain zero OS-specific imports."""
    forbidden_modules = {
        "ctypes",
        "win32gui",
        "win32api",
        "win32con",
        "win32process",
        "win32event",
        "pywin32",
    }

    project_root = Path(__file__).resolve().parent.parent
    checked_dirs = [
        project_root / "app" / "core",
        project_root / "app" / "database",
        project_root / "app" / "infrastructure" / "clock.py",
    ]

    files_to_check = []
    for target in checked_dirs:
        if target.is_file():
            files_to_check.append(target)
        elif target.is_dir():
            files_to_check.extend(target.rglob("*.py"))

    assert len(files_to_check) > 0

    for py_file in files_to_check:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden_modules, (
                        f"Forbidden OS import '{alias.name}' in {py_file.relative_to(project_root)}"
                    )
            elif isinstance(node, ast.ImportFrom):
                mod_name = node.module or ""
                assert mod_name not in forbidden_modules, (
                    f"Forbidden OS import '{mod_name}' in {py_file.relative_to(project_root)}"
                )
                assert not any(mod_name.startswith(f"{f}.") for f in forbidden_modules), (
                    f"Forbidden OS import '{mod_name}' in {py_file.relative_to(project_root)}"
                )
