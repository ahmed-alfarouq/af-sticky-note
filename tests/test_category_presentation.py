"""Phase 7B: Qt-free category presentation helpers and CategoryService.

Backend-only (stdlib, no Qt, no GUI). The Category database record stays the
single source of truth; these tests pin the formatting/ordering/validation
behavior that widgets rely on.
"""
import pytest

from app.core.models import DEFAULT_CATEGORY_ID, Category
from app.core.services.category_service import CategoryService
from app.database.category_repository import CategoryRepository
from app.ui.category_presentation import (
    category_icon_key,
    category_label,
    sort_categories,
)


def _category(id="work", name_ar="عمل", icon_key="work", sort_order=20, is_active=True):
    return Category(
        id=id,
        name_ar=name_ar,
        icon_key=icon_key,
        sort_order=sort_order,
        is_active=is_active,
        created_at="t",
        updated_at="t",
    )


# ------------------------------------------------------------ presentation

def test_label_uses_arabic_name_not_id():
    assert category_label(_category(id="work", name_ar="عمل")) == "عمل"


def test_label_falls_back_to_id_when_name_blank():
    assert category_label(_category(id="work", name_ar="  ")) == "work"


def test_icon_key_is_passthrough_not_a_registry():
    assert category_icon_key(_category(id="x", icon_key="x-custom")) == "x-custom"
    assert category_icon_key(_category(id="x", icon_key="")) == "x"


def test_sort_follows_sort_order_then_id():
    unordered = [_category(id="b", sort_order=20), _category(id="a", sort_order=20),
                 _category(id="c", sort_order=10)]
    assert [c.id for c in sort_categories(unordered)] == ["c", "a", "b"]


def test_presentation_module_has_no_hardcoded_category_registry():
    """The DB record is the only source of names/keys/order: this module must
    not grow its own label table."""
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "app" / "ui" / "category_presentation.py")
    text = source.read_text(encoding="utf-8")
    for arabic in ("دين", "عمل", "حياة", "عام"):
        assert arabic not in text


# ------------------------------------------------------------ service

def test_service_lists_active_categories_in_order(db_connection):
    service = CategoryService(CategoryRepository(db_connection))
    assert [c.id for c in service.list_active_categories()] == [
        "religion", "work", "life", "general",
    ]


def test_service_excludes_inactive_from_active_list(db_connection):
    repo = CategoryRepository(db_connection)
    repo.set_active("life", False)
    service = CategoryService(repo)
    assert [c.id for c in service.list_active_categories()] == ["religion", "work", "general"]


def test_service_get_category(db_connection):
    service = CategoryService(CategoryRepository(db_connection))
    category = service.get_category("work")
    assert category is not None
    assert category.name_ar == "عمل"
    assert service.get_category("nope") is None
    assert service.get_category("") is None


def test_service_resolve_defaults_and_rejects(db_connection):
    service = CategoryService(CategoryRepository(db_connection))
    assert service.resolve_category_id(None) == DEFAULT_CATEGORY_ID
    with pytest.raises(ValueError):
        service.resolve_category_id("")
    with pytest.raises(ValueError):
        service.resolve_category_id(123)  # type: ignore


def test_service_resolve_validates_existence(db_connection):
    service = CategoryService(CategoryRepository(db_connection))
    assert service.resolve_category_id("religion") == "religion"
    with pytest.raises(ValueError):
        service.resolve_category_id("nope")
