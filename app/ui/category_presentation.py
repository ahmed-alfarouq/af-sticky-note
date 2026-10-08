"""Category presentation helpers -- with no Qt dependency at all.

The database-backed :class:`Category` object is the single source of truth
for ids, Arabic names, icon keys, and ordering. This module only *formats*
what it is given (plus deterministic ordering), so adding a future category
never touches widget code. It deliberately contains no label/icon/order
tables; see ``TaskService``/``CategoryService`` for validation.
"""
from __future__ import annotations

from typing import List, Sequence

from app.core.models import Category


def category_label(category: Category) -> str:
    """Arabic display name, falling back to the stable id when blank."""
    if category.name_ar and category.name_ar.strip():
        return category.name_ar
    return category.id


def category_icon_key(category: Category) -> str:
    """Asset key for this category, falling back to the stable id."""
    if category.icon_key and category.icon_key.strip():
        return category.icon_key.strip()
    return category.id


def sort_categories(categories: Sequence[Category]) -> List[Category]:
    """Deterministic UI order: sort_order first, stable id second.

    The repository already returns this order; sorting here as well keeps
    every selector and menu correct no matter who built the list.
    """
    return sorted(categories, key=lambda c: (c.sort_order, c.id))
