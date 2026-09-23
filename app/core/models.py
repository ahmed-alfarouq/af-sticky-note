"""Domain models: plain data, no Qt, no SQL, no repositories."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


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