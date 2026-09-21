"""Clarification 2: get_or_assign_daily_quote is atomic.

If any step of "select a quote, record its usage, stamp the Day,
maybe advance the cycle" fails, the whole assignment must roll back:
no partially-assigned Day, no orphan quote_usage row, no incorrectly
advanced rotation cycle.
"""
import random

import pytest


def test_failure_during_assignment_leaves_no_partial_state(
    db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo, monkeypatch
):
    from app.core.services.quote_service import QuoteService

    quote_repo.create("A")
    quote_repo.create("B")

    service = QuoteService(
        db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo,
        favorite_selection_probability=0.0, random_source=random.Random(0),
    )

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure after quote selection")

    # Fail after the quote has been picked but before the Day is stamped.
    monkeypatch.setattr(quote_usage_repo, "record_usage", _boom)

    with pytest.raises(RuntimeError):
        service.get_or_assign_daily_quote("2026-09-01")

    # The Day was created (that step is intentionally its own, separate
    # commit) but must NOT have been stamped with a quote.
    day = day_repo.get_by_date("2026-09-01")
    assert day is not None
    assert day.quote_text is None

    # No orphan quote_usage row for this day.
    assert quote_usage_repo.get_for_day(day.id) is None

    # The rotation cycle must be exactly where it started.
    assert rotation_state_repo.get_current_cycle() == 1


def test_failure_during_cycle_advance_leaves_no_partial_state(
    db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo, monkeypatch
):
    """Exhaust the normal pool, then force a failure exactly on the
    assignment that would advance the cycle — the cycle counter must
    not move, and no usage/Day state for that attempt should exist."""
    from app.core.services.quote_service import QuoteService

    quote_repo.create("A")
    quote_repo.create("B")

    service = QuoteService(
        db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo,
        favorite_selection_probability=0.0, random_source=random.Random(0),
    )

    # Use up the whole cycle (A and B).
    service.get_or_assign_daily_quote("2026-09-01")
    service.get_or_assign_daily_quote("2026-09-02")
    assert rotation_state_repo.get_current_cycle() == 1

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure during cycle rollover")

    monkeypatch.setattr(day_repo, "set_quote_text", _boom)

    with pytest.raises(RuntimeError):
        service.get_or_assign_daily_quote("2026-09-03")

    day = day_repo.get_by_date("2026-09-03")
    assert day.quote_text is None
    assert quote_usage_repo.get_for_day(day.id) is None
    # The failed attempt must not have left the cycle counter advanced.
    assert rotation_state_repo.get_current_cycle() == 1


def test_commit_between_the_two_checks_is_caught_by_the_in_transaction_check(
    db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo, db_path, monkeypatch
):
    """Realistic race: another connection completes and commits a full
    assignment for this exact day in the gap between our pre-transaction
    check and our BEGIN IMMEDIATE. Our in-transaction re-read must see
    that committed result and return it — never attempting a second
    INSERT and never producing a second quote for the same day."""
    from app.database.connection import create_connection
    from app.core.services.quote_service import QuoteService

    quote_a = quote_repo.create("A")

    service = QuoteService(
        db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo,
        favorite_selection_probability=0.0, random_source=random.Random(0),
    )

    real_get_or_create = day_repo.get_or_create

    def _get_or_create_then_simulate_a_concurrent_winner(date):
        day = real_get_or_create(date)  # quote_text is still None here
        other_conn = create_connection(db_path)
        other_conn.execute(
            "UPDATE days SET quote_text = ?, updated_at = 'now' WHERE id = ?",
            (quote_a.text, day.id),
        )
        other_conn.execute(
            "INSERT INTO quote_usage "
            "(day_id, quote_id, cycle_number, is_favorite_selection, selected_at) "
            "VALUES (?, ?, 1, 0, 'now')",
            (day.id, quote_a.id),
        )
        other_conn.commit()
        other_conn.close()
        return day  # snapshot from before the other connection's commit

    monkeypatch.setattr(day_repo, "get_or_create", _get_or_create_then_simulate_a_concurrent_winner)

    result = service.get_or_assign_daily_quote("2026-09-01")

    assert result.was_newly_assigned is False
    assert result.day.quote_text == "A"

    day = day_repo.get_by_date("2026-09-01")
    row = db_connection.execute(
        "SELECT COUNT(*) AS c FROM quote_usage WHERE day_id = ?", (day.id,)
    ).fetchone()
    assert row["c"] == 1  # no duplicate usage row was inserted


def test_integrity_error_fallback_returns_existing_assignment_without_crashing(
    db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo, monkeypatch
):
    """Directly exercises the except-branch's recovery logic: if the
    INSERT into quote_usage ever raises sqlite3.IntegrityError (its
    UNIQUE day_id constraint firing), the service must recover by
    returning the already-committed assignment rather than propagating
    the error. The double-checked read above is what normally prevents
    this from being reached at all under the app's own BEGIN IMMEDIATE
    locking (see the concurrency test above) — this test isolates the
    except-branch itself so its recovery behavior is verified directly."""
    import sqlite3

    from app.core.services.quote_service import QuoteService

    quote_a = quote_repo.create("A")

    # A day that is already fully, validly assigned — standing in for
    # "whatever committed state the constraint violation would have
    # been protecting."
    day = day_repo.get_or_create("2026-09-01")
    quote_usage_repo.record_usage(day.id, quote_a.id, cycle_number=1, is_favorite_selection=False)
    day_repo.set_quote_text(day.id, quote_a.text)
    db_connection.commit()

    def _raise_integrity_error(*args, **kwargs):
        raise sqlite3.IntegrityError("UNIQUE constraint failed: quote_usage.day_id")

    monkeypatch.setattr(quote_usage_repo, "record_usage", _raise_integrity_error)

    # Force past the early "already assigned" short-circuit by pointing
    # the service at a stale in-memory Day snapshot with quote_text=None,
    # exactly as if our pre-transaction read had happened before the
    # commit above. This puts the call on the same path a genuine race
    # would take, landing on the manually-forced IntegrityError.
    from app.core.models import Day

    stale_day = Day(
        id=day.id, date=day.date, quote_text=None,
        created_at=day.created_at, updated_at=day.updated_at,
    )
    monkeypatch.setattr(day_repo, "get_or_create", lambda date: stale_day)

    service = QuoteService(
        db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo,
        favorite_selection_probability=0.0, random_source=random.Random(0),
    )

    result = service.get_or_assign_daily_quote("2026-09-01")

    assert result.was_newly_assigned is False
    assert result.day.quote_text == "A"
