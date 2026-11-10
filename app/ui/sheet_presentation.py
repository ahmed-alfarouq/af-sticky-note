"""What the bottom option sheet shows for categories and priorities.

Qt-free: turns domain objects into :class:`SheetOption` rows (key, label,
marker, optional hint). The sheet widget only renders rows; it never knows
about categories or priorities.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Sequence

from app.core.models import Category
from app.ui.category_presentation import category_icon_key, category_label, sort_categories
from app.ui.priority_presentation import (
    PRIORITY_COLORS,
    PRIORITY_HINTS,
    PRIORITY_LABELS,
    PRIORITY_ORDER,
)

__all__ = [
    "CATEGORY_SHEET_TITLE",
    "PRIORITY_SHEET_TITLE",
    "MarkerShape",
    "SheetOption",
    "category_sheet_options",
    "priority_sheet_options",
]

CATEGORY_SHEET_TITLE = "اختر التصنيف"
PRIORITY_SHEET_TITLE = "اختر الأولوية"


class MarkerShape(str, Enum):
    SQUARE = "square"
    CIRCLE = "circle"


@dataclass(frozen=True)
class SheetOption:
    """One selectable row: stable ``key``, label, marker, optional hint.

    The marker is the icon named by ``icon_key`` when given; otherwise a
    shape filled with ``marker_color``.
    """

    key: str
    label: str
    hint: str = ""
    marker_color: str = ""
    marker_shape: MarkerShape = MarkerShape.CIRCLE
    icon_key: str = ""


def category_sheet_options(categories: Sequence[Category]) -> List[SheetOption]:
    """Active categories in display order; the key is the stable id."""
    return [
        SheetOption(
            key=category.id,
            label=category_label(category),
            icon_key=category_icon_key(category),
        )
        for category in sort_categories(categories)
        if category.is_active
    ]


def priority_sheet_options() -> List[SheetOption]:
    """All priorities, most urgent first; the key is the enum value."""
    return [
        SheetOption(
            key=priority.value,
            label=PRIORITY_LABELS[priority],
            marker_color=PRIORITY_COLORS[priority],
            marker_shape=MarkerShape.CIRCLE,
            hint=PRIORITY_HINTS[priority],
        )
        for priority in PRIORITY_ORDER
    ]