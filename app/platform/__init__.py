"""OS-specific desktop integration boundary.

Provides abstract platform protocols, fallback implementations for non-Windows
environments, and a centralized factory provider.
"""
from app.platform.interfaces import (
    DesktopWindowController,
    PlatformAdapter,
    StartupManager,
    SystemTrayController,
)
from app.platform.provider import get_platform_adapter, reset_platform_adapter
from app.platform.unsupported import (
    NoOpDesktopWindowController,
    NoOpStartupManager,
    NoOpSystemTrayController,
    UnsupportedPlatformAdapter,
)

__all__ = [
    "DesktopWindowController",
    "StartupManager",
    "SystemTrayController",
    "PlatformAdapter",
    "get_platform_adapter",
    "reset_platform_adapter",
    "NoOpDesktopWindowController",
    "NoOpStartupManager",
    "NoOpSystemTrayController",
    "UnsupportedPlatformAdapter",
]
