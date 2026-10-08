"""Application service for task categories.

Qt-free and SQL-free: the UI asks this service (never the repository) for
the selectable categories and for category-ID validation, preserving the
UI -> service -> repository -> SQLite layering.
"""
from __future__ import annotations

from typing import List, Optional

from app.core.models import DEFAULT_CATEGORY_ID, Category
from app.database.category_repository import CategoryRepository


class CategoryService:
    def __init__(self, category_repo: CategoryRepository) -> None:
        self._category_repo = category_repo

    def list_active_categories(self) -> List[Category]:
        """Categories the UI may offer, in deterministic sort_order."""
        return self._category_repo.list_active()

    def get_category(self, category_id: str) -> Optional[Category]:
        """Return the category for a stable id, or None when unknown."""
        if not isinstance(category_id, str) or not category_id:
            return None
        return self._category_repo.get_by_id(category_id)

    def resolve_category_id(self, category_id: Optional[str]) -> str:
        """Return a validated category id, defaulting to DEFAULT_CATEGORY_ID.

        ``None`` (omitted) means the default. Anything else must be a
        non-empty string identifying a known category -- otherwise ValueError.
        Explicitly invalid ids are never silently replaced; only omission
        yields the default.
        """
        if category_id is None:
            return DEFAULT_CATEGORY_ID
        if not isinstance(category_id, str) or not category_id:
            raise ValueError(f"Invalid task category: {category_id!r}")
        if self._category_repo.get_by_id(category_id) is None:
            raise ValueError(f"Unknown task category: {category_id!r}")
        return category_id
