"""Domain models: plain data, no Qt, no SQL, no repositories."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# Canonical default category: every task created through the supported
# application path carries a valid category_id, and pre-category rows are
# backfilled to this id by migration 005. Never use a display label as identity.
DEFAULT_CATEGORY_ID = "general"


@dataclass(frozen=True)
class Category:
    """First-class task category (Phase 7A).

    Identity is the stable string ``id`` (e.g. "religion", "work", "life",
    "general") and never the Arabic display name, so renames never corrupt
    historical tasks or future reports. ``icon_key`` is a relative asset key
    resolved by the future UI as ``assets/icons/<icon_key>.svg`` (fallback
    icon when missing); absolute paths are never stored. ``is_active=False``
    hides a category from future selectors without invalidating tasks that
    already reference it (tasks FK is RESTRICT, never CASCADE).

    Initial seeds (migration 005_task_categories.sql, sort_order in
    parentheses): religion/"دين" (10), work/"عمل" (20), life/"حياة" (30),
    general/"عام" (40, the default). Gaps leave room for future inserts.
    """

    id: str
    name_ar: str
    icon_key: str
    sort_order: int
    is_active: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Task:
    id: Optional[int]
    day_id: int
    text: str
    is_completed: bool
    position: int
    created_at: str
    updated_at: str
    priority: TaskPriority = TaskPriority.MEDIUM
    source_task_id: Optional[int] = None
    category_id: str = DEFAULT_CATEGORY_ID


@dataclass(frozen=True)
class Day:
    id: Optional[int]
    date: str  # local calendar date, YYYY-MM-DD — never derived from UTC
    quote_text: Optional[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Quote:
    id: Optional[int]
    text: str
    is_favorite: bool
    is_user_created: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class QuoteUsage:
    """Historical record of which quote was assigned to which day,
    and whether it was drawn from the favorite pool or the normal
    rotation."""
    id: Optional[int]
    day_id: int
    quote_id: int
    cycle_number: int
    is_favorite_selection: bool
    selected_at: str