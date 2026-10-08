"""Phase 7B: CategoryIconProvider tests.

Qt tests no-op (rather than fail) when PySide6 is unavailable, following the
project's UI-test convention.
"""
from __future__ import annotations

from pathlib import Path

try:  # pragma: no cover - environment dependent
    from PySide6.QtWidgets import QApplication

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


def _repo_icons_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "icons"


def test_all_four_initial_category_icons_exist():
    icons = _repo_icons_dir()
    for key in ("religion", "work", "life", "general"):
        path = icons / f"{key}.png"
        assert path.is_file(), f"missing category icon asset: {path}"
        assert path.stat().st_size > 0


def test_existing_icon_resolves_and_loads():
    if _skip_without_qt():
        return
    _qt_app()
    from PySide6.QtGui import QPixmap

    from app.ui.category_icons import CategoryIconProvider

    provider = CategoryIconProvider(_repo_icons_dir())
    path = provider.icon_path_for_key("work")
    assert path is not None and path.is_file()
    assert not QPixmap(str(path)).isNull()
    assert not provider.icon_for_key("work").isNull()


def test_cache_returns_the_identical_object():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.category_icons import CategoryIconProvider

    provider = CategoryIconProvider(_repo_icons_dir())
    first = provider.icon_for_key("religion")
    assert provider.icon_for_key("religion") is first


def test_missing_icon_falls_back_without_crashing():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.category_icons import CategoryIconProvider

    provider = CategoryIconProvider(_repo_icons_dir())
    assert provider.icon_path_for_key("no-such-category") is None
    fallback = provider.icon_for_key("no-such-category")
    assert not fallback.isNull()
    # Cached too: still the same object, still no crash.
    assert provider.icon_for_key("no-such-category") is fallback


def test_unsafe_keys_never_become_paths():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.category_icons import CategoryIconProvider

    provider = CategoryIconProvider(_repo_icons_dir())
    for evil in ("../logo", "/abs", "", "a b", "x.svg", ".."):
        assert provider.icon_path_for_key(evil) is None
        assert not provider.icon_for_key(evil).isNull()


def test_provider_resolves_packaged_relative_paths(tmp_path):
    """Simulate a frozen bundle: icons must resolve under any bundle dir."""
    if _skip_without_qt():
        return
    _qt_app()
    import sys

    from app.ui.category_icons import CategoryIconProvider, get_category_icons_dir

    fake_bundle = tmp_path / "bundle"
    icons = fake_bundle / "assets" / "icons"
    icons.mkdir(parents=True)
    (icons / "work.png").write_bytes((_repo_icons_dir() / "work.png").read_bytes())

    original = getattr(sys, "_MEIPASS", None)
    try:
        sys._MEIPASS = str(fake_bundle)
        assert get_category_icons_dir() == icons
        provider = CategoryIconProvider()
        assert provider.icon_path_for_key("work") == icons / "work.png"
        assert not provider.icon_for_key("work").isNull()
    finally:
        if original is not None:
            sys._MEIPASS = original
        else:
            delattr(sys, "_MEIPASS")


def test_icon_for_category_uses_its_icon_key(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.database.category_repository import CategoryRepository
    from app.ui.category_icons import CategoryIconProvider

    provider = CategoryIconProvider(_repo_icons_dir())
    category = CategoryRepository(db_connection).get_by_id("life")
    assert category is not None
    assert provider.icon_for_category(category) is provider.icon_for_key("life")
