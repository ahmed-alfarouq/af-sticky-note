"""Daily quote selection and assignment.

SELECTION POLICY:
  - A Day gets exactly one quote, assigned once. Once
    Day.quote_text is set, it is returned unchanged forever.
  - Each assignment rolls a weighted coin (favorite_selection_probability)
    to decide whether to draw from the favorite pool or the normal
    rotation pool.
  - Pool membership (normal vs favorite) is evaluated from each
    quote's CURRENT is_favorite value at selection time -- not from
    any value recorded in a past quote_usage row. If a quote's
    favorite status changes later, its pool membership changes
    immediately; historical quote_usage rows (which record which
    branch a past selection actually took) are never rewritten.
  - Normal quotes rotate through cycles: a normal quote cannot be
    selected twice within the same cycle. When the normal pool is
    exhausted, the next assignment starts a fresh cycle.
  - Favorite quotes are exempt from cycle tracking: they may repeat
    on any day, and selecting one never marks any normal quote as
    consumed and never advances/resets the normal cycle.
  - If there are no normal quotes at all, favorites are used
    unconditionally as a fallback.
  - If there are no quotes of either kind, NoAvailableQuotesError
    is raised.

ATOMICITY (see app/database/unit_of_work.py for the transaction
boundary itself):
  get_or_assign_daily_quote() uses a double-checked pattern:

    1. A cheap pre-check, outside any explicit transaction:
       get_or_create(date) -- this may create the Day row (its own,
       separate, immediately-committed statement; a Day existing
       with quote_text=NULL never counts as an assignment) and
       returns early if that Day already has a quote.
    2. If not already assigned, the authoritative attempt opens a
       UnitOfWork (BEGIN IMMEDIATE -- acquires SQLite's write lock
       up front) and re-reads the Day by id inside that lock. If a
       concurrent writer committed a full assignment in the gap
       between step 1 and this point, this re-read sees it and
       returns it -- no second selection, no second INSERT.
    3. Only if still unassigned does it select a quote, insert the
       quote_usage row, and stamp Day.quote_text -- all inside the
       same UnitOfWork, so a failure at any point rolls back the
       whole attempt (no partial Day, no orphan quote_usage row, no
       incorrectly advanced cycle).

  Two SQLite UNIQUE constraints back this up as defense-in-depth for
  races BEGIN IMMEDIATE's locking should already prevent in practice:
  days.date (two callers racing to create the same brand-new Day)
  and quote_usage.day_id (two callers racing to insert a second
  usage row for an already-assigned Day). If either ever fires,
  get_or_assign_daily_quote() does not crash: it retries the whole
  attempt, whose own pre-check will then see the now-committed
  winner and return it. A narrow, bounded retry count guards against
  retrying forever if something is genuinely wrong; any IntegrityError
  that isn't recognizable as one of these two specific races still
  propagates unchanged.

Randomness is injected via `random_source` so tests can be fully
deterministic without changing production behavior.
"""
from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass
from typing import Optional

from app.core.models import Day, Quote
from app.database.day_repository import DayRepository
from app.database.quote_repository import QuoteRepository
from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
from app.database.quote_usage_repository import QuoteUsageRepository
from app.database.unit_of_work import UnitOfWork

DEFAULT_FAVORITE_SELECTION_PROBABILITY = 0.15
MAX_ASSIGNMENT_RACE_RETRIES = 5

# Substrings of the sqlite3 IntegrityError message that identify it as
# one of the two expected same-day assignment races, not some other,
# unrelated constraint violation.
_EXPECTED_RACE_CONSTRAINT_MARKERS = ("days.date", "quote_usage.day_id")


class NoAvailableQuotesError(RuntimeError):
    """Raised when there are no quotes (normal or favorite) to assign."""


def _is_expected_assignment_race(exc: sqlite3.IntegrityError) -> bool:
    message = str(exc)
    return any(marker in message for marker in _EXPECTED_RACE_CONSTRAINT_MARKERS)


@dataclass(frozen=True)
class DailyQuoteAssignment:
    day: Day
    quote: Optional[Quote]  # None only when an already-assigned day was returned as-is
    was_newly_assigned: bool


class QuoteService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        quote_repo: QuoteRepository,
        day_repo: DayRepository,
        quote_usage_repo: QuoteUsageRepository,
        rotation_state_repo: QuoteRotationStateRepository,
        favorite_selection_probability: float = DEFAULT_FAVORITE_SELECTION_PROBABILITY,
        random_source: Optional[random.Random] = None,
    ) -> None:
        self._conn = conn
        self._quote_repo = quote_repo
        self._day_repo = day_repo
        self._quote_usage_repo = quote_usage_repo
        self._rotation_state_repo = rotation_state_repo
        self._favorite_probability = favorite_selection_probability
        self._random = random_source if random_source is not None else random.Random()

    def get_or_assign_daily_quote(self, date: str) -> DailyQuoteAssignment:
        last_error: Optional[sqlite3.IntegrityError] = None
        for _ in range(MAX_ASSIGNMENT_RACE_RETRIES):
            try:
                return self._attempt_assignment(date)
            except sqlite3.IntegrityError as exc:
                if not _is_expected_assignment_race(exc):
                    raise
                last_error = exc
                # Another connection won a narrow race (Day creation or
                # quote assignment) between our pre-check and our
                # write. Retrying re-runs the pre-check, which will now
                # see the winner's committed state and either
                # short-circuit immediately or proceed correctly.
                continue
        assert last_error is not None
        raise last_error

    def _attempt_assignment(self, date: str) -> DailyQuoteAssignment:
        # Cheap pre-check, outside any explicit transaction. May itself
        # create the Day row (its own, separate, immediately-committed
        # statement) if this is the first call for `date` -- a Day
        # existing with quote_text=NULL never counts as an assignment.
        day = self._day_repo.get_or_create(date)
        if day.quote_text is not None:
            return DailyQuoteAssignment(day=day, quote=None, was_newly_assigned=False)

        with UnitOfWork(self._conn):
            # Authoritative re-check, now holding the write lock: a
            # concurrent winner may have committed a full assignment in
            # the gap between the pre-check above and BEGIN IMMEDIATE.
            current_day = self._day_repo.get_by_id(day.id)
            assert current_day is not None, "Day cannot vanish between its own creation and this read"
            if current_day.quote_text is not None:
                return DailyQuoteAssignment(day=current_day, quote=None, was_newly_assigned=False)

            quote, cycle_number, is_favorite_selection = self._select_quote()
            assert current_day.id is not None, "Day.id is always set once persisted"
            assert quote.id is not None, "Quote.id is always set once persisted"
            self._quote_usage_repo.record_usage(
                current_day.id, quote.id, cycle_number, is_favorite_selection
            )
            updated_day = self._day_repo.set_quote_text(current_day.id, quote.text)
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
            cycle_number = self._rotation_state_repo.advance_cycle()
            available_normal = list(normal_quotes)

        if favorite_quotes and self._random.random() < self._favorite_probability:
            return self._random.choice(favorite_quotes), cycle_number, True

        if available_normal:
            return self._random.choice(available_normal), cycle_number, False

        return self._random.choice(favorite_quotes), cycle_number, True
