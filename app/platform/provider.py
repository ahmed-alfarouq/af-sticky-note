"""Centralized platform factory and provider.

Resolves the appropriate PlatformAdapter implementation at composition time.
All platform resolution logic is strictly centralized here.
"""
from __future__ import annotations

import logging
import sys
from typing import Optional

from app.platform.interfaces import PlatformAdapter
from app.platform.unsupported import UnsupportedPlatformAdapter

logger = logging.getLogger(__name__)

# Cached adapter singleton
_CURRENT_PLATFORM_ADAPTER: Optional[PlatformAdapter] = None


def get_platform_adapter(force_platform: Optional[str] = None) -> PlatformAdapter:
    """Obtain the PlatformAdapter appropriate for the host OS.

    Parameters:
        force_platform: Optional platform identifier override (useful for testing).

    Returns:
        PlatformAdapter instance implementing platform protocols.
    """
    global _CURRENT_PLATFORM_ADAPTER

    # Return cached singleton if no override is requested
    if force_platform is None and _CURRENT_PLATFORM_ADAPTER is not None:
        return _CURRENT_PLATFORM_ADAPTER

    target_os = force_platform if force_platform is not None else sys.platform

    adapter: PlatformAdapter
    if target_os == "win32":
        # Windows desktop implementation is scheduled for Phase 5F.
        # Fall back gracefully until the Windows package is introduced.
        try:
            from app.platform.windows import WindowsPlatformAdapter
            adapter = WindowsPlatformAdapter()
        except ImportError:
            logger.info("Windows platform implementation not present; using fallback adapter.")
            adapter = UnsupportedPlatformAdapter(platform_name="win32 (pending Phase 5F)")
    else:
        logger.info("Running on non-Windows platform (%s); using unsupported fallback adapter.", target_os)
        adapter = UnsupportedPlatformAdapter(platform_name=target_os)

    if force_platform is None:
        _CURRENT_PLATFORM_ADAPTER = adapter

    return adapter


def reset_platform_adapter() -> None:
    """Reset the cached platform adapter (for test isolation)."""
    global _CURRENT_PLATFORM_ADAPTER
    _CURRENT_PLATFORM_ADAPTER = None
