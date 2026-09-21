"""Daily quote selection and assignment.

SELECTION POLICY (exact rule, see Phase 3 spec):
  - A Day gets exactly one quote, assigned once. Once
    Day.quote_text is set, it is returned unchanged forever —
    this method never re-rolls an existing assignment.
  - Each assignment first rolls a weighted coin
    (favorite_selection_probability) to decide whether to draw
    from the favorites pool or the normal rotation pool.
  - Normal quotes rotate through cycles: a normal quote cannot be
    selected twice within the same cycle. When the normal pool is
    exhausted, the next assignment starts a fresh cycle.
  - Favorite quotes are exempt from cycle tracking entirely: they
    may repeat on any day, and selecting one never marks any
    normal quote as consumed.
  - If there are no normal quotes at all, favorites are used
    unconditionally as a fallback (and vice versa is not needed,
    since normal quotes never run out permanently — they cycle).
  - If there are no quotes of either kind, NoAvailableQuotesError
    is raised — this is a controlled, explicit failure, not a
    silent no-op.

Randomness is injected via `random_source` (anything with .random()
and .choice(), e.g. a random.Random instance) so tests can be fully
deterministic without changing production behavior.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from app.core.models import Day, Quote
from app.database.day_repository import DayRepository
from app.database.quote_repository import QuoteRepository
from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
from app.database.quote_usage_repository import QuoteUsageRepository

DEFAULT_FAVORITE_SELECTION_PROBABILITY = 0.15


class NoAvailableQuotesError(RuntimeError):
    """Raised when there are no quotes (normal or favorite) to assign."""


@dataclass(frozen=True)
class DailyQuoteAssignment:
    day: Day
    quote: Optional[Quote]  # None only when an already-assigned day was returned as-is
    was_newly_assigned: bool


class QuoteService:
    def __init__(
        self,
        quote_repo: QuoteRepository,
        day_repo: DayRepository,
        quote_usage_repo: QuoteUsageRepository,
        rotation_state_repo: QuoteRotationStateRepository,
        favorite_selection_probability: float = DEFAULT_FAVORITE_SELECTION_PROBABILITY,
        random_source: Optional[random.Random] = None,
    ) -> None:
        self._quote_repo = quote_repo
        self._day_repo = day_repo
        self._quote_usage_repo = quote_usage_repo
        self._rotation_state_repo = rotation_state_repo
        self._favorite_probability = favorite_selection_probability
        self._random = random_source if random_source is not None else random.Random()

    def get_or_assign_daily_quote(self, date: str) -> DailyQuoteAssignment:
        day = self._day_repo.get_or_create(date)
        if day.quote_text is not None:
            return DailyQuoteAssignment(day=day, quote=None, was_newly_assigned=False)

        quote, cycle_number, is_favorite_selection = self._select_quote()
        self._quote_usage_repo.record_usage(day.id, quote.id, cycle_number, is_favorite_selection)
        updated_day = self._day_repo.set_quote_text(day.id, quote.text)
        return DailyQuoteAssignment(day=updated_day, quote=quote, was_newly_assigned=True)

    def _select_quote(self):
        normal_quotes = self._quote_repo.list_normal()
        favorite_quotes = self._quote_repo.list_favorites()

        if not normal_quotes and not favorite_quotes:
            raise NoAvailableQuotesError("No quotes available to assign.")

        cycle_number = self._rotation_state_repo.get_current_cycle()
        consumed_ids = self._quote_usage_repo.get_consumed_normal_ids(cycle_number)
        available_normal = [q for q in normal_quotes if q.id not in consumed_ids]

        if not available_normal and normal_quotes:
            # The normal pool is exhausted for this cycle — start a new one.
            cycle_number = self._rotation_state_repo.advance_cycle()
            available_normal = list(normal_quotes)

        if favorite_quotes and self._random.random() < self._favorite_probability:
            return self._random.choice(favorite_quotes), cycle_number, True

        if available_normal:
            return self._random.choice(available_normal), cycle_number, False

        # No normal quotes exist at all — favorites are the only option.
        return self._random.choice(favorite_quotes), cycle_number, True