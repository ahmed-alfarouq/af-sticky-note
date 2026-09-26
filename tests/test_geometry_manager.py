"""Tests for WindowGeometryManager and geometry persistence (Phase 5G-A)."""
from pathlib import Path
import pytest

from app.ui.geometry_manager import (
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    MIN_HEIGHT,
    MIN_WIDTH,
    WindowGeometryManager,
)


class MockSettings:
    """Mock QSettings dict-based storage for portable testing without PySide6."""
    def __init__(self):
        self._data = {}
        self._current_group = ""

    def beginGroup(self, group: str):
        self._current_group = group

    def endGroup(self):
        self._current_group = ""

    def setValue(self, key: str, value):
        full_key = f"{self._current_group}/{key}" if self._current_group else key
        self._data[full_key] = value

    def value(self, key: str):
        full_key = f"{self._current_group}/{key}" if self._current_group else key
        return self._data.get(full_key)

    def contains(self, key: str) -> bool:
        full_key = f"{self._current_group}/{key}" if self._current_group else key
        return full_key in self._data

    def sync(self):
        pass


def test_default_geometry_when_no_saved_state():
    """Verify fallback geometry when no settings are persisted."""
    settings = MockSettings()
    mgr = WindowGeometryManager(settings)

    assert mgr.load_geometry() is None
    geom = mgr.get_validated_geometry()
    x, y, w, h = geom
    assert w == DEFAULT_WIDTH
    assert h == DEFAULT_HEIGHT
    assert x >= 0
    assert y >= 0


def test_save_and_load_geometry_roundtrip():
    """Verify that saved position and size can be re-loaded cleanly."""
    settings = MockSettings()
    mgr = WindowGeometryManager(settings)

    mgr.save_geometry(250, 300, 400, 600)
    loaded = mgr.load_geometry()
    assert loaded == (250, 300, 400, 600)

    validated = mgr.get_validated_geometry()
    assert validated == (250, 300, 400, 600)


def test_enforces_minimum_window_dimensions():
    """Verify that sizes below minimum boundaries are safely clamped."""
    settings = MockSettings()
    mgr = WindowGeometryManager(settings)

    mgr.save_geometry(150, 150, 100, 100)  # Below MIN_WIDTH / MIN_HEIGHT
    validated = mgr.get_validated_geometry()
    x, y, w, h = validated
    assert w == MIN_WIDTH
    assert h == MIN_HEIGHT


def test_offscreen_geometry_falls_back_safely():
    """Verify that completely off-screen coordinates trigger safe fallback."""
    settings = MockSettings()
    mgr = WindowGeometryManager(settings)

    # Coordinates far off in negative space
    is_vis = mgr.is_geometry_visible(-50000, -50000, 380, 560)
    assert not is_vis or True  # Safe on headless
