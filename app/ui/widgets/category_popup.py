"""Custom category dropdown popup (v3 §9).

A frameless ``Qt.Popup`` panel listing the active categories from the
database-backed source of truth: label at the start (right), check mark at
the end (left, visible only on the selected item). No ``QComboBox`` or
``QMenu`` is involved. Category choice is identified by stable id, never by
display label. Per-category artwork is intentionally absent here (the spec
defines no per-category glyphs); rows/menus/history keep their existing
category icons, untouched by this module.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.models import Category
from app.ui.category_presentation import category_label, sort_categories
from app.ui.icons import icon as vector_icon

#: Panel metrics (v3 §9), extended from six to eight rows by the approved
#: amendment: same 40 px rows, same padding -- only the count changes.
PANEL_WIDTH = 176
PANEL_PADDING = 4
ITEM_HEIGHT = 40
SHADOW_MARGIN = 32

__all__ = [
    "CategoryPopup",
    "ITEM_HEIGHT",
    "PANEL_PADDING",
    "PANEL_WIDTH",
    "SHADOW_MARGIN",
    "place_popup",
]


def place_popup(
    trigger: QRect,
    popup_size: QSize,
    window: QRect,
    prefer_above: bool,
) -> QRect:
    """Position a popup rect for a trigger rect inside a window rect.

    Pure geometry (unit-testable, no widgets): the popup's right edge aligns
    to the trigger's right edge with a 6 px gap, opening above by default
    and flipping below when it does not fit (8 px window margins); when
    neither side fits, or horizontally, the rect is clamped inside the
    window. All coordinates are inclusive Qt rects.
    """
    gap = 6
    margin = 8
    width, height = popup_size.width(), popup_size.height()
    x = trigger.right() - width + 1
    x = max(window.left() + margin, min(x, window.right() - margin - width + 1))

    above_y = trigger.top() - gap - height + 1
    below_y = trigger.bottom() + gap
    if prefer_above and above_y >= window.top() + margin:
        y = above_y
    elif not prefer_above and below_y + height - 1 <= window.bottom() - margin:
        y = below_y
    elif above_y >= window.top() + margin:
        y = above_y
    elif below_y + height - 1 <= window.bottom() - margin:
        y = below_y
    else:
        y = max(window.top() + margin, min(above_y, window.bottom() - margin - height + 1))
    return QRect(x, y, width, height)


class _PopupList(QListWidget):
    """Keyboard map for the popup (v3 §9): wrapping arrows, Home/End,
    Enter/Space to choose, Escape/Tab to dismiss."""

    choose_requested = Signal()
    escape_pressed = Signal()
    tab_pressed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("categoryPopupList")
        self.setAccessibleName("اختيار الفئة")
        # Check mark at the end (left): with a left-to-right view the icon
        # stays left while item text is explicitly right-aligned.
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setUniformItemSizes(True)
        self.setSpacing(0)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        key = event.key()
        count = self.count()
        if count == 0:
            super().keyPressEvent(event)
            return
        current = self.currentRow()
        if key == Qt.Key.Key_Up:
            self.setCurrentRow((current - 1) % count)
            self.scrollToItem(self.currentItem())
            event.accept()
            return
        if key == Qt.Key.Key_Down:
            self.setCurrentRow((current + 1) % count)
            self.scrollToItem(self.currentItem())
            event.accept()
            return
        if key == Qt.Key.Key_Home:
            self.setCurrentRow(0)
            self.scrollToItem(self.currentItem())
            event.accept()
            return
        if key == Qt.Key.Key_End:
            self.setCurrentRow(count - 1)
            self.scrollToItem(self.currentItem())
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.choose_requested.emit()
            event.accept()
            return
        if key == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            event.accept()
            return
        if key == Qt.Key.Key_Tab:
            self.tab_pressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class CategoryPopup(QWidget):
    """Frameless category dropdown showing the supplied active categories."""

    category_chosen = Signal(str)  # stable category id
    popup_closed = Signal()  # dismissed without choosing

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
        )
        self.setObjectName("categoryPopup")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._categories: List[Category] = []
        self._trigger: Optional[QWidget] = None
        self._panel_height = PANEL_PADDING * 2 + 2

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SHADOW_MARGIN, SHADOW_MARGIN, SHADOW_MARGIN, SHADOW_MARGIN)
        outer.setSpacing(0)

        self._panel = QFrame(self)
        self._panel.setObjectName("categoryPopupPanel")
        self._panel.setFixedWidth(PANEL_WIDTH)
        outer.addWidget(self._panel)

        panel_layout = QVBoxLayout(self._panel)
        panel_layout.setContentsMargins(PANEL_PADDING, PANEL_PADDING, PANEL_PADDING, PANEL_PADDING)
        panel_layout.setSpacing(0)

        self._list = _PopupList(self._panel)
        panel_layout.addWidget(self._list)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.choose_requested.connect(self._choose_current)
        self._list.escape_pressed.connect(lambda: self._dismiss(restore_focus=True))
        self._list.tab_pressed.connect(lambda: self._dismiss(restore_focus=False))

        shadow = QGraphicsDropShadowEffect(self._panel)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 128))
        self._panel.setGraphicsEffect(shadow)

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------
    def set_categories(self, categories: Sequence[Category]) -> None:
        """Offer these categories (active, stable-id valued). Rebuilds the
        item list only when the offered ids actually change."""
        ordered = [c for c in sort_categories(categories) if c.is_active]
        if [c.id for c in ordered] == [c.id for c in self._categories]:
            return
        self._categories = ordered
        self._list.clear()
        for category in ordered:
            item = QListWidgetItem(category_label(category), self._list)
            item.setData(Qt.ItemDataRole.UserRole, category.id)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setSizeHint(QSize(0, ITEM_HEIGHT))
        self._panel.setFixedHeight(PANEL_PADDING * 2 + 2 + len(ordered) * ITEM_HEIGHT)
        self._panel_height = self._panel.height()
        total = QSize(
            PANEL_WIDTH + SHADOW_MARGIN * 2, self._panel_height + SHADOW_MARGIN * 2
        )
        self.setFixedSize(total)
        self._refresh_checks(None)

    def _refresh_checks(self, selected_id: Optional[str]) -> None:
        """Check mark on the selected item only (space kept reserved)."""
        check = vector_icon("check", "#8FB8D8").pixmap(16, 16)
        blank = QPixmap(16, 16)
        blank.fill(Qt.GlobalColor.transparent)
        for index in range(self._list.count()):
            item = self._list.item(index)
            is_current = item.data(Qt.ItemDataRole.UserRole) == selected_id
            item.setIcon(check if is_current else QIcon(blank))

    # ------------------------------------------------------------------
    # Open / choose / dismiss
    # ------------------------------------------------------------------
    def open_for(
        self,
        categories: Sequence[Category],
        current_id: str,
        trigger: QWidget,
        prefer_above: bool = True,
    ) -> bool:
        """Show the popup for ``trigger``; False when there is nothing to show."""
        self.set_categories(categories)
        if not self._categories:
            return False
        self._trigger = trigger
        ids = [c.id for c in self._categories]
        self._list.setCurrentRow(ids.index(current_id) if current_id in ids else 0)
        self._refresh_checks(self._categories[self._list.currentRow()].id)
        trigger_rect = QRect(trigger.mapToGlobal(QPoint(0, 0)), trigger.size())
        window_rect = QRect(
            trigger.window().mapToGlobal(QPoint(0, 0)), trigger.window().size()
        )
        self.setGeometry(
            place_popup(trigger_rect, self.size(), window_rect, prefer_above)
        )
        self.show()
        self._list.setFocus()
        return True

    def _chosen_id(self) -> Optional[str]:
        item = self._list.currentItem()
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return data if isinstance(data, str) and data else None

    def _on_item_clicked(self) -> None:
        self._choose_current()

    def _choose_current(self) -> None:
        chosen = self._chosen_id()
        trigger, self._trigger = self._trigger, None
        self.hide()
        if chosen is not None:
            self.category_chosen.emit(chosen)
        if trigger is not None:
            try:
                trigger.setFocus()
            except RuntimeError:
                pass  # trigger went away with its window; nothing to focus

    def _dismiss(self, restore_focus: bool = True) -> None:
        trigger, self._trigger = self._trigger, None
        self.hide()
        if restore_focus and trigger is not None:
            try:
                trigger.setFocus()
            except RuntimeError:
                pass

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt naming
        # Outside-click dismissal (native Qt.Popup behavior) lands here with
        # no choice made; choosing already emitted before hiding.
        self._trigger = None
        super().hideEvent(event)
        self.popup_closed.emit()

    def category_ids(self) -> List[str]:
        """Offered stable ids in display order (tests / diagnostics)."""
        return [c.id for c in self._categories]
