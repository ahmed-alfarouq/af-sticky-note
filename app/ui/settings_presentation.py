"""What the settings pickers offer -- with no Qt dependency at all."""
from __future__ import annotations

from typing import List

from app.infrastructure.clock import ARABIC_WEEKDAYS
from app.ui.sheet_presentation import SheetOption

__all__ = ["WEEKDAY_CHOICES", "weekday_sheet_options"]

#: Weekdays in the order the picker lists them, as Python weekdays
#: (Monday = 0 ... Sunday = 6): Saturday first.
WEEKDAY_CHOICES = (5, 6, 0, 1, 2, 3, 4)


def weekday_sheet_options() -> List[SheetOption]:
    """One plain row per weekday; the key is the weekday number."""
    return [SheetOption(key=str(weekday), label=ARABIC_WEEKDAYS[weekday]) for weekday in WEEKDAY_CHOICES]