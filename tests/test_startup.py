"""Tests for startup integration (Phase 5H-B)."""
from unittest.mock import MagicMock
import pytest

from app.platform.interfaces import PlatformAdapter, StartupManager
from app.platform.provider import get_platform_adapter, reset_platform_adapter
from app.platform.unsupported import NoOpStartupManager, UnsupportedPlatformAdapter
from app.platform.windows.startup import WindowsStartupManager, get_default_executable_command


class MockWinregKey:
    def __init__(self, storage: dict):
        self.storage = storage

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockWinregModule:
    """Mock winreg module providing isolated in-memory registry testing."""
    HKEY_CURRENT_USER = "HKEY_CURRENT_USER"
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self):
        self.keys = {}

    def OpenKey(self, root, subkey, reserved, access):
        if subkey not in self.keys:
            self.keys[subkey] = {}
        return MockWinregKey(self.keys[subkey])

    def SetValueEx(self, key_obj, name, reserved, reg_type, val):
        key_obj.storage[name] = val

    def QueryValueEx(self, key_obj, name):
        if name not in key_obj.storage:
            raise FileNotFoundError(f"Key {name} not found")
        return key_obj.storage[name], self.REG_SZ

    def DeleteValue(self, key_obj, name):
        if name not in key_obj.storage:
            raise FileNotFoundError(f"Key {name} not found")
        del key_obj.storage[name]


def test_unsupported_startup_manager_contract():
    """Verify NoOpStartupManager satisfies interface safely without errors."""
    mgr = NoOpStartupManager()
    assert isinstance(mgr, StartupManager)
    assert not mgr.is_enabled()
    assert not mgr.enable()
    assert not mgr.disable()


def test_windows_startup_manager_contract():
    """Verify WindowsStartupManager implements StartupManager protocol."""
    mgr = WindowsStartupManager()
    assert isinstance(mgr, StartupManager)


def test_windows_startup_enable_disable_lifecycle():
    """Verify enable, query, and disable cycle using isolated mock winreg."""
    mock_reg = MockWinregModule()
    mgr = WindowsStartupManager(
        app_name="DailyStickyTest",
        command=r'"C:\Program Files\DailySticky\DailySticky.exe"',
        winreg_module=mock_reg,
    )

    # Initial state: not enabled
    assert not mgr.is_enabled()

    # Enable
    res = mgr.enable()
    assert res is True
    assert mgr.is_enabled()

    # Verify stored command
    run_key = mock_reg.keys[r"Software\Microsoft\Windows\CurrentVersion\Run"]
    assert run_key["DailyStickyTest"] == r'"C:\Program Files\DailySticky\DailySticky.exe"'

    # Idempotent enable
    assert mgr.enable() is True
    assert mgr.is_enabled()

    # Disable
    res_dis = mgr.disable()
    assert res_dis is True
    assert not mgr.is_enabled()

    # Idempotent disable
    assert mgr.disable() is True
    assert not mgr.is_enabled()


def test_executable_command_resolution():
    """Verify get_default_executable_command generates non-empty quoted string."""
    cmd = get_default_executable_command()
    assert isinstance(cmd, str)
    assert len(cmd) > 0
    assert cmd.startswith('"')


def test_platform_adapter_exposes_startup_manager():
    """Verify platform provider exposes startup manager on adapter."""
    reset_platform_adapter()
    adapter = get_platform_adapter(force_platform="linux")
    assert isinstance(adapter, PlatformAdapter)
    assert hasattr(adapter, "startup_manager")
    assert isinstance(adapter.startup_manager, StartupManager)
