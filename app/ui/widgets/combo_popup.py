"""Popup sizing for the compact task selectors (Phase 7H).

The closed selectors stay compact (``Maximum`` + ``AdjustToContents``),
but the popup view must fit the widest item -- icon, full label, delegate
padding -- instead of clipping to the closed width. Qt sizes the popup
from the combo, so callers widen the *view* in an overridden
``showPopup()`` (a documented virtual: QComboBox.showPopup). Width is
bounded by the available screen geometry; nothing here changes stored
data, labels, or the closed control.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox


def popup_content_width(combo: QComboBox) -> int:
    """Width in pixels needed to show the widest popup item fully."""
    view = combo.view()
    metrics = view.fontMetrics()
    icon_width = combo.iconSize().width()
    widest = 0
    for index in range(combo.count()):
        text_width = metrics.horizontalAdvance(combo.itemText(index))
        widest = max(widest, text_width)
    # Icon + gap, item padding, view frame and a small breathing margin.
    return widest + (icon_width + 8 if icon_width > 0 else 0) + 28


def fit_popup_to_contents(combo: QComboBox) -> int:
    """Size the popup view to the content width; return the width used.

    Never shrinks below the closed combo width and never exceeds the
    available screen width. Also disables delegate elision so labels can
    never be replaced by "...".
    """
    view = combo.view()
    view.setTextElideMode(Qt.TextElideMode.ElideNone)
    needed = max(popup_content_width(combo), combo.width())
    screen = combo.screen()
    if screen is not None:
        available = screen.availableGeometry().width()
        if available > 0:
            needed = min(needed, available)
    view.setMinimumWidth(needed)
    return needed
