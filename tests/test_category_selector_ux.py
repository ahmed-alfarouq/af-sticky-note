"""Phase 7B: CategorySelector widget tests.

Qt tests no-op (rather than fail) when PySide6 is unavailable, following the
project's UI-test convention.
"""
from __future__ import annotations

from pathlib import Path

try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


def _categories(db_connection):
    from app.core.services.category_service import CategoryService
    from app.database.category_repository import CategoryRepository

    return CategoryService(CategoryRepository(db_connection)).list_active_categories()


def _provider():
    from app.ui.category_icons import CategoryIconProvider

    return CategoryIconProvider(Path(__file__).resolve().parent.parent / "assets" / "icons")


def test_selector_shows_icon_plus_name_in_sort_order(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.category_selector import CategorySelector

    selector = CategorySelector(_categories(db_connection), _provider())
    assert selector.category_ids() == ["religion", "work", "life", "general"]
    assert [selector.itemText(i) for i in range(selector.count())] == [
        "دين", "عمل", "حياة", "عام",
    ]
    for i in range(selector.count()):
        assert not selector.itemIcon(i).isNull()


def test_selector_defaults_to_general(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.category_selector import CategorySelector

    selector = CategorySelector(_categories(db_connection), _provider())
    assert selector.selected_category_id() == "general"


def test_selector_set_and_get_round_trip(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.category_selector import CategorySelector

    selector = CategorySelector(_categories(db_connection), _provider())
    selector.set_category("work")
    assert selector.selected_category_id() == "work"
    selector.set_category("nope")
    assert selector.selected_category_id() == "general"
    selector.set_category("life")
    selector.reset_to_default()
    assert selector.selected_category_id() == "general"


def test_selector_is_right_to_left(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.category_selector import CategorySelector

    selector = CategorySelector(_categories(db_connection), _provider())
    assert selector.layoutDirection() == Qt.LayoutDirection.RightToLeft


def test_selector_without_provider_shows_names_only(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.category_selector import CategorySelector

    selector = CategorySelector(_categories(db_connection))
    assert selector.category_ids() == ["religion", "work", "life", "general"]
    assert selector.itemIcon(0).isNull()
    assert selector.selected_category_id() == "general"


def test_selector_refresh_keeps_selection_when_possible(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.category_selector import CategorySelector

    selector = CategorySelector(_categories(db_connection), _provider())
    selector.set_category("work")
    selector.set_categories(_categories(db_connection))
    assert selector.selected_category_id() == "work"


def test_empty_selector_falls_back_to_default_safely():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.category_selector import CategorySelector

    selector = CategorySelector(())
    assert selector.categories_count() == 0
    assert selector.selected_category_id() == "general"
    selector.set_category("work")  # must not crash
    assert selector.selected_category_id() == "general"
