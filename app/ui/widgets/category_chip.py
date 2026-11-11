"""Category chip (category icon + label).

Shows the category chosen for the next task, with that category's icon. The
chip only holds the selection; the window presents the category sheet when
the chip asks (``open_requested``). It never queries the database: the
caller supplies the categories once, mirroring :class:`CategorySelector`
conventions (silent programmatic selection, default fallback).
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from app.core.models import DEFAULT_CATEGORY_ID, Category
from app.ui.category_icons import CategoryIconProvider
from app.ui.category_presentation import category_label, sort_categories
from app.ui.icons import icon as vector_icon
from app.ui.styles.add_task_bar_style import CHIP_ICON_SIZE
from app.ui.widgets.picker_chip import PickerChip

__all__ = ["CategoryChip"]

_FALLBACK_ICON_COLOR = "#98A2B3"


class CategoryChip(PickerChip):
    """Category icon + label + caret button exposing stable category ids.

    The current selection is always the category's stable ``id`` string --
    never an index and never the display name -- so callers persist identity
    directly, exactly like :class:`CategorySelector`.
    """

    def __init__(
        self,
        categories: Sequence[Category] = (),
        parent: Optional[QWidget] = None,
        icon_provider: Optional[CategoryIconProvider] = None,
    ) -> None:
        icon = QLabel()
        icon.setFixedSize(CHIP_ICON_SIZE, CHIP_ICON_SIZE)
        super().__init__("categoryChip", "الفئة", icon, parent)
        self._icon = icon
        self._icon_provider = icon_provider
        self._categories: List[Category] = []
        self._selected_id = DEFAULT_CATEGORY_ID
        self.set_categories(categories)

    # -- Model --------------------------------------------------------------

    def set_categories(self, categories: Sequence[Category]) -> None:
        """Replace the offered categories (active, sort_order-respecting).

        Keeps the current selection when it still exists; otherwise falls
        back to the canonical default. No signals, no DB access.
        """
        previous = self._selected_id if self._categories else DEFAULT_CATEGORY_ID
        self._categories = [c for c in sort_categories(categories) if c.is_active]
        self.set_category(previous or DEFAULT_CATEGORY_ID)

    def categories(self) -> List[Category]:
        """The offered categories, in display order."""
        return list(self._categories)

    def categories_count(self) -> int:
        return len(self._categories)

    def category_ids(self) -> List[str]:
        """Stable ids in display order."""
        return [c.id for c in self._categories]

    def selected_category_id(self) -> str:
        """Stable id of the current choice (default when unreadable/empty)."""
        if self._find(self._selected_id) is not None:
            return self._selected_id
        return DEFAULT_CATEGORY_ID

    def selected_label(self) -> str:
        """Arabic display name of the current choice."""
        selected = self._find(self.selected_category_id())
        return category_label(selected) if selected else self.selected_category_id()

    def set_category(self, category_id: Optional[str]) -> None:
        """Select ``category_id``; unknown/None -> default. No signals."""
        target = category_id if isinstance(category_id, str) and category_id else DEFAULT_CATEGORY_ID
        if self._find(target) is None:
            target = DEFAULT_CATEGORY_ID
        self._selected_id = target
        self._refresh()

    def reset_to_default(self) -> None:
        self.set_category(DEFAULT_CATEGORY_ID)

    # -- Presentation -------------------------------------------------------

    def _find(self, category_id: str) -> Optional[Category]:
        return next((c for c in self._categories if c.id == category_id), None)

    def _refresh(self) -> None:
        label = self.selected_label()
        self._set_text(label)
        self.setToolTip(label)
        self._icon.setPixmap(self._icon_pixmap())

    def _icon_pixmap(self) -> QPixmap:
        """The selected category's icon (a generic tag without a provider)."""
        selected = self._find(self.selected_category_id())
        if self._icon_provider is not None and selected is not None:
            icon = self._icon_provider.icon_for_category(selected)
        else:
            icon = vector_icon("tag", _FALLBACK_ICON_COLOR)
        return icon.pixmap(CHIP_ICON_SIZE, CHIP_ICON_SIZE)