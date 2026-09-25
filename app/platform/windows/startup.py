"""Windows startup manager implementation using Windows Registry (Phase 5H-B).

Manages per-user automatic startup under HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
Requires no administrator privileges, supports packaged PyInstaller executables (sys.frozen),
and provides graceful no-op behavior outside Windows or in development tests.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional

from app.config.settings import APP_NAME
from app.platform.interfaces import StartupManager

logger = logging.getLogger(__name__)

# Registry subkey for per-user autorun
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_default_executable_command() -> str:
    """Determine the launch command appropriate for packaged and development execution.

    - If packaged (PyInstaller frozen executable), returns the quoted sys.executable path.
    - If running under Python interpreter in dev, returns formatted sys.executable and entry point.
    """
    if getattr(sys, "frozen", False):
        # Packaged single-file or directory executable
        exe_path = os.path.abspath(sys.executable)
        return f'"{exe_path}"'

    # Development fallback
    main_script = os.path.abspath(sys.argv[0])
    return f'"{sys.executable}" "{main_script}"'


class WindowsStartupManager(StartupManager):
    """Manages auto-start on logon via HKCU Run registry key."""

    def __init__(
        self,
        app_name: str = APP_NAME,
        command: Optional[str] = None,
        winreg_module: Optional[object] = None,
    ) -> None:
        self._app_name = app_name
        self._command = command
        # Allow injecting mock winreg module for test isolation without touching real registry
        self._winreg = winreg_module

    def _get_winreg(self) -> Optional[object]:
        if self._winreg is not None:
            return self._winreg
        if sys.platform != "win32":
            return None
        try:
            import winreg
            return winreg
        except ImportError:
            return None

    def _get_command(self) -> str:
        if self._command is not None:
            return self._command
        return get_default_executable_command()

    def is_enabled(self) -> bool:
        """Check if application entry exists in HKCU\\...\\Run matching our command."""
        reg = self._get_winreg()
        if reg is None:
            return False

        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, reg.KEY_READ) as key:
                val, _ = reg.QueryValueEx(key, self._app_name)
                # Verify that value exists and matches current command or executable
                return bool(val)
        except (FileNotFoundError, OSError):
            return False
        except Exception as exc:
            logger.debug("Failed to query HKCU Run registry key: %s", exc)
            return False

    def enable(self) -> bool:
        """Register application in HKCU\\...\\Run. Returns True if successful."""
        reg = self._get_winreg()
        if reg is None:
            logger.debug("winreg is not available; cannot enable startup.")
            return False

        cmd = self._get_command()
        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, reg.KEY_SET_VALUE) as key:
                reg.SetValueEx(key, self._app_name, 0, reg.REG_SZ, cmd)
                logger.info("Registered startup command for '%s': %s", self._app_name, cmd)
                return True
        except Exception as exc:
            logger.error("Failed to enable Windows startup for '%s': %s", self._app_name, exc)
            return False

    def disable(self) -> bool:
        """Remove application from HKCU\\...\\Run. Returns True if successful."""
        reg = self._get_winreg()
        if reg is None:
            logger.debug("winreg is not available; cannot disable startup.")
            return False

        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, reg.KEY_SET_VALUE) as key:
                try:
                    reg.DeleteValue(key, self._app_name)
                    logger.info("Removed startup command for '%s'", self._app_name)
                except FileNotFoundError:
                    # Key value already does not exist (idempotent)
                    pass
                return True
        except Exception as exc:
            logger.error("Failed to disable Windows startup for '%s': %s", self._app_name, exc)
            return False
