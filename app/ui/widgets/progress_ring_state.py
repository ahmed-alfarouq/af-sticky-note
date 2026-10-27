"""State and caption helpers for the daily progress ring."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "ProgressState",
    "ProgressSnapshot",
    "create_progress_snapshot",
    "progress_caption",
]


class ProgressState(str, Enum):
    """Visual states supported by the daily progress ring."""

    EMPTY = "empty"
    NOT_STARTED = "not_started"
    PARTIAL = "partial"
    COMPLETE = "complete"
    PAST_DAY = "past_day"


@dataclass(frozen=True, slots=True)
class ProgressSnapshot:
    """Immutable, normalized progress information supplied by the caller."""

    completed: int
    total: int
    state: ProgressState

    @property
    def fraction(self) -> float:
        """Completed fraction, between zero and one."""
        return self.completed / self.total if self.total else 0.0

    @property
    def remaining(self) -> int:
        return self.total - self.completed

    @property
    def is_empty(self) -> bool:
        """True when there are no tasks, regardless of past-day mode."""
        return self.total == 0

    @property
    def is_complete(self) -> bool:
        return self.state == ProgressState.COMPLETE

    @property
    def is_past_day(self) -> bool:
        return self.state == ProgressState.PAST_DAY


def create_progress_snapshot(
    completed: int,
    total: int,
    past_day: bool = False,
) -> ProgressSnapshot:
    """Normalize task counts and determine the appropriate visual state."""
    total = max(0, int(total))
    completed = min(max(0, int(completed)), total)

    if past_day:
        state = ProgressState.PAST_DAY
    elif total == 0:
        state = ProgressState.EMPTY
    elif completed == 0:
        state = ProgressState.NOT_STARTED
    elif completed == total:
        state = ProgressState.COMPLETE
    else:
        state = ProgressState.PARTIAL

    return ProgressSnapshot(completed=completed, total=total, state=state)


def progress_caption(snapshot: ProgressSnapshot) -> str:
    """Return the Arabic caption appropriate for a progress state."""
    if snapshot.is_past_day:
        return "عرض فقط"

    match snapshot.state:
        case ProgressState.EMPTY:
            return "لا مهام"
        case ProgressState.NOT_STARTED:
            return "لم تبدأ بعد"
        case ProgressState.COMPLETE:
            return "أنجزت كل المهام"

    remaining = snapshot.remaining
    if remaining == 1:
        return "مهمة واحدة وتنتهي"
    if remaining == 2:
        return "بقيت مهمتان"
    return f"بقيت {remaining} مهام"