"""Dock category chip opening the custom dropdown (v3 §8.2, §9).

A compact button showing the current category (tag glyph + Arabic label +
caret) for the next task. Click, Space, Enter, or Down-arrow opens the
:class:`CategoryPopup` above the dock; choosing updates the held selection
used at task submission. The chip never queries the database: the caller
supplies categories once, mirroring :class:`CategorySelector` conventions
(compact sizing, silent programmatic selection, default fallback).
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from app.core.models import DEFAULT_CATEGORY_ID, Category
from app.ui.category_presentation import category_label, sort_categories
from app.ui.icons import icon as vector_icon
from app.ui.widgets.category_popup import CategoryPopup

__all__ = ["CategoryChip"]


class CategoryChip(QWidget):
    """Tag + label + caret button exposing stable category ids.

    The current data item is always the category's stable ``id`` string --
    never an index and never the display name -- so callers persist identity
    directly, exactly like :class:`CategorySelector`.
    """

    def __init__(
        self,
        categories: Sequence[Category] = (),
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("categoryChip")
        self.setAccessibleName("الفئة")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Compact like the selectors it replaces in the dock.
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(32)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(8)

        self._tag_label = QLabel(self)
        self._tag_label.setPixmap(vector_icon("tag", "#98A2B3").pixmap(16, 16))
        self._tag_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(self._tag_label)

        self._name_label = QLabel(self)
        self._name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(self._name_label, 1)

        self._caret_label = QLabel(self)
        self._caret_label.setPixmap(vector_icon("caret_down", "#98A2B3").pixmap(16, 16))
        self._caret_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(self._caret_label)

        self._categories: List[Category] = []
        self._selected_id = DEFAULT_CATEGORY_ID
        self._popup: Optional[CategoryPopup] = None
        self._open = False
        self.set_categories(categories)

    # ------------------------------------------------------------------
    # Popup lifecycle (single instance, parented here: dies with the chip)
    # ------------------------------------------------------------------
    def _ensure_popup(self) -> CategoryPopup:
        if self._popup is None:
            self._popup = CategoryPopup(self)
            self._popup.category_chosen.connect(self._on_popup_chosen)
            self._popup.popup_closed.connect(self._on_popup_closed)
        return self._popup

    def is_popup_open(self) -> bool:
        """Whether the dropdown is currently shown."""
        return self._open and self._popup is not None and self._popup.isVisible()

    def open_popup(self) -> bool:
        """Show the dropdown above the dock; False when nothing to offer."""
        if self.is_popup_open():
            self._ensure_popup().hide()
            return False
        popup = self._ensure_popup()
        if not popup.open_for(self._categories, self._selected_id, self, prefer_above=True):
            return False
        self._set_open(True)
        return True

    def _on_popup_chosen(self, category_id: str) -> None:
        self.set_category(category_id)
        self._set_open(False)

    def _on_popup_closed(self) -> None:
        self._set_open(False)

    def _set_open(self, open: bool) -> None:
        self._open = open
        self.setProperty("open", open)
        self.style().unpolish(self)
        self.style().polish(self)

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_popup()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt naming
        key = event.key()
        if key in (Qt.Key.Key_Space, Qt.Key.Key_Enter, Qt.Key.Key_Return,
                   Qt.Key.Key_Down):
            self.open_popup()
            event.accept()
            return
        super().keyPressEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.setProperty("hover", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.setProperty("hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.setProperty("focused", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.setProperty("focused", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().focusOutEvent(event)

    # ------------------------------------------------------------------
    # Model (mirrors CategorySelector semantics)
    # ------------------------------------------------------------------
    def set_categories(self, categories: Sequence[Category]) -> None:
        """Replace the offered categories (active, sort_order-respecting).

        Keeps the current selection when it still exists; otherwise falls
        back to the canonical default. No signals, no DB access. An open
        popup is refreshed in place rather than rebuilt.
        """
        previous = self._selected_id if self._categories else DEFAULT_CATEGORY_ID
        self._categories = [c for c in sort_categories(categories) if c.is_active]
        self.set_category(previous if previous else DEFAULT_CATEGORY_ID)
        if self._popup is not None and self._popup.isVisible():
            self._popup.set_categories(self._categories)

    def categories_count(self) -> int:
        """Number of categories currently offered."""
        return len(self._categories)

    def category_ids(self) -> List[str]:
        """Stable ids in display order (tests / diagnostics)."""
        return [c.id for c in self._categories]

    def selected_category_id(self) -> str:
        """Stable id of the current choice (default when unreadable/empty)."""
        if any(c.id == self._selected_id for c in self._categories):
            return self._selected_id
        return DEFAULT_CATEGORY_ID

    def selected_label(self) -> str:
        """Arabic display name of the current choice."""
        for category in self._categories:
            if category.id == self.selected_category_id():
                return category_label(category)
        return self.selected_category_id()

    def set_category(self, category_id: Optional[str]) -> None:
        """Select ``category_id``; unknown/None -> default. No signals."""
        target = category_id if isinstance(category_id, str) and category_id else DEFAULT_CATEGORY_ID
        if not any(c.id == target for c in self._categories):
            target = DEFAULT_CATEGORY_ID
        self._selected_id = target
        self._name_label.setText(self.selected_label())
        self.setToolTip(self.selected_label())
        self.setAccessibleName("الفئة")

    def reset_to_default(self) -> None:
        """Return the chip to the canonical default."""
        self.set_category(DEFAULT_CATEGORY_ID)
