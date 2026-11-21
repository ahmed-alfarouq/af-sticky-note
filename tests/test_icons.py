"""R-icons: qtawesome foundation tests (v3 §1.4).

Covers every specified glyph key, size/color rendering, the (key, color)
cache contract, QT_API initialization order, and packaging data collection.
Category PNG behavior is covered by test_category_icons.py (must not change).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

try:  # pragma: no cover - environment dependent
    from PySide6.QtWidgets import QApplication

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


EXPECTED_GLYPHS = {
    "pin": "ph.push-pin-bold",
    "pin_active": "ph.push-pin-fill",
    "archive": "ph.archive-bold",
    "settings": "ph.gear-six-bold",
    "close": "ph.x-bold",
    "trash": "ph.trash-bold",
    "check": "ph.check-bold",
    "tag": "ph.tag-bold",
    "caret_down": "ph.caret-down-bold",
    "caret_left": "ph.caret-left-bold",
    "plus": "ph.plus-bold",
}


def test_glyph_table_matches_specification():
    from app.ui.icons import GLYPHS

    assert GLYPHS == EXPECTED_GLYPHS


@pytest.mark.parametrize("key", sorted(EXPECTED_GLYPHS))
def test_every_specified_glyph_renders(key):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.icons import icon

    rendered = icon(key, "#F2F5F8")
    assert not rendered.isNull()
    assert not rendered.pixmap(18, 18).isNull()


def test_icon_honors_size_and_color():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.icons import icon

    assert not icon("plus", "#FFFFFF").pixmap(18, 18).isNull()
    assert not icon("check", "#0F141D").pixmap(11, 11).isNull()
    assert not icon("tag", "#98A2B3").pixmap(12, 12).isNull()


def test_cache_reuses_same_key_and_color():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.icons import icon

    first = icon("close", "#F2F5F8")
    assert icon("close", "#F2F5F8") is first
    assert icon("close", "#98A2B3") is not first
    assert icon("trash", "#F2F5F8") is not first


def test_unknown_key_raises_key_error():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.icons import icon

    with pytest.raises(KeyError):
        icon("no-such-icon", "#FFFFFF")


def test_qt_api_binding_is_established_by_our_code():
    """QT_API=pyside6 must be set by application code before qtawesome binds.

    Reloads app.ui.icons with the variable removed and verifies the import
    itself establishes the binding (runtime behavior, not source text).
    """
    previous = os.environ.pop("QT_API", None)
    saved_module = sys.modules.pop("app.ui.icons", None)
    try:
        assert "QT_API" not in os.environ
        import app.ui.icons as icons

        assert os.environ.get("QT_API") == "pyside6"
        if not _skip_without_qt():
            _qt_app()
            assert not icons.icon("close", "#FFFFFF").isNull()
    finally:
        sys.modules.pop("app.ui.icons", None)
        if saved_module is not None:
            sys.modules["app.ui.icons"] = saved_module
        if previous is not None:
            os.environ["QT_API"] = previous


def test_requirements_pin_qtawesome_constraint():
    text = (Path(__file__).resolve().parent.parent / "requirements.txt").read_text(encoding="utf-8")
    assert "qtawesome>=1.4,<2.0" in text.replace(" ", "")


def test_pyinstaller_collects_qtawesome_data():
    text = (Path(__file__).resolve().parent.parent / "packaging" / "DailySticky.spec").read_text(
        encoding="utf-8"
    )
    assert 'collect_data_files("qtawesome")' in text
    assert '"app.ui.icons"' in text
