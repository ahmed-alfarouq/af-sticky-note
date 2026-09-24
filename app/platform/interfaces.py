"""Platform-independent abstractions and contracts for OS-specific desktop integration.

These protocols define WHAT the application requires from the operating system
without exposing HOW specific platforms (such as Win32) implement it.

Core, services, database, and UI widgets interact only with these contracts.
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class DesktopWindowController(Protocol):
    """Controls OS-level window placement and desktop layering.

    The implementation handles pinning the window to the desktop wallpaper level
    (e.g., WorkerW/Progman on Windows) and ensuring appropriate OS window styles.
    """

    def attach_to_desktop(self, window_handle: int) -> bool:
        """Attach or layer the window to the desktop background.

        Returns True if successfully attached or pinned, False otherwise.
        """
        ...

    def detach_from_desktop(self, window_handle: int) -> bool:
        """Detach or restore the window from desktop background layering."""
        ...

    def is_attached(self) -> bool:
        """Check if the window is currently attached to the desktop layer."""
        ...


@runtime_checkable
class StartupManager(Protocol):
    """Manages application auto-start on user logon."""

    def is_enabled(self) -> bool:
        """Check if auto-start on logon is currently configured."""
        ...

    def enable(self) -> bool:
        """Enable auto-start on logon. Returns True if successful."""
        ...

    def disable(self) -> bool:
        """Disable auto-start on logon. Returns True if successful."""
        ...


@runtime_checkable
class SystemTrayController(Protocol):
    """Manages OS system tray integration and notifications."""

    def is_available(self) -> bool:
        """Check if system tray is supported in the current OS environment."""
        ...

    def show(self) -> None:
        """Display the system tray icon."""
        ...

    def hide(self) -> None:
        """Hide the system tray icon."""
        ...

    def show_message(self, title: str, message: str) -> None:
        """Display a system notification/toast from the tray."""
        ...


@runtime_checkable
class PlatformAdapter(Protocol):
    """Composite platform integration bundle providing access to all OS subsystems."""

    @property
    def name(self) -> str:
        """Platform identifier name (e.g., 'windows', 'unsupported')."""
        ...

    @property
    def is_supported(self) -> bool:
        """Whether the current platform is fully supported for desktop integration."""
        ...

    @property
    def window_controller(self) -> DesktopWindowController:
        """Controller for desktop window placement."""
        ...

    @property
    def startup_manager(self) -> StartupManager:
        """Manager for auto-start settings."""
        ...

    @property
    def tray_controller(self) -> SystemTrayController:
        """Controller for system tray."""
        ...
