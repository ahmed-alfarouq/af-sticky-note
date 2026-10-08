"""Compact combo box for choosing a task category.

Shows ``[icon] Arabic name`` per row from database-backed :class:`Category`
objects -- it never contains SQL, a connection, or a hardcoded category
list. The caller supplies the categories (typically
``CategoryService.list_active_categories()``) once; ordering follows each
category's ``sort_order``. Mirrors :class:`PrioritySelector` conventions
(compact sizing, silent programmatic selection, default fallback).
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QSizePolicy, QWidget

from app.core.models import DEFAULT_CATEGORY_ID, Category
from app.ui.category_icons import CategoryIconProvider
from app.ui.category_presentation import category_label, sort_categories

__all__ = ["CategorySelector"]


class CategorySelector(QComboBox):
    """Icon + Arabic-name combo exposing stable category ids.

    The current data item is always the category's stable ``id`` string --
    never an index and never the display name -- so callers persist identity
    directly.
    """

    def __init__(
        self,
        categories: Sequence[Category] = (),
        icon_provider: Optional[CategoryIconProvider] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("categorySelector")
        self.setAccessibleName("فئة المهمة")
        self.setAccessibleDescription("اختر فئة المهمة من القائمة")
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        # Compact like the priority selector: never wider than its contents.
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._icon_provider = icon_provider
        self.set_categories(categories)

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------
    def set_categories(self, categories: Sequence[Category]) -> None:
        """Replace the offered categories (active, sort_order-respecting).

        Keeps the current selection when it still exists; otherwise falls
        back to the canonical default. No signals, no DB access.
        """
        previous = self.selected_category_id()
        self.blockSignals(True)
        try:
            self.clear()
            for category in sort_categories(categories):
                if self._icon_provider is not None:
                    self.addItem(
                        self._icon_provider.icon_for_category(category),
                        category_label(category),
                        category.id,
                    )
                else:
                    self.addItem(category_label(category), category.id)
        finally:
            self.blockSignals(False)
        self.set_category(previous if previous else DEFAULT_CATEGORY_ID)

    def categories_count(self) -> int:
        """Number of categories currently offered."""
        return self.count()

    # ------------------------------------------------------------------
    # Value access
    # ------------------------------------------------------------------
    def _index_of(self, category_id: str) -> int:
        for index in range(self.count()):
            if self.itemData(index) == category_id:
                return index
        return -1

    def selected_category_id(self) -> str:
        """Stable id of the current choice (default when unreadable/empty)."""
        data = self.currentData()
        if isinstance(data, str) and data:
            return data
        return DEFAULT_CATEGORY_ID

    def set_category(self, category_id: Optional[str]) -> None:
        """Select ``category_id`` silently; unknown/None -> default."""
        target = category_id if isinstance(category_id, str) and category_id else DEFAULT_CATEGORY_ID
        index = self._index_of(target)
        if index == -1:
            index = self._index_of(DEFAULT_CATEGORY_ID)
        if index == -1 or index == self.currentIndex():
            return
        self.blockSignals(True)
        try:
            self.setCurrentIndex(index)
        finally:
            self.blockSignals(False)

    def reset_to_default(self) -> None:
        """Return the selector to the canonical default silently."""
        self.set_category(DEFAULT_CATEGORY_ID)

    def category_ids(self) -> List[str]:
        """Stable ids in display order (tests / diagnostics)."""
        return [self.itemData(i) for i in range(self.count())]
