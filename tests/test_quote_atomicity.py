import random
import sqlite3
import threading

import pytest

from app.core.services.quote_service import QuoteService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.quote_repository import QuoteRepository
from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
from app.database.quote_usage_repository import QuoteUsageRepository


def test_failure_mid_assignment_leaves_no_partial_state(db_connection, quote_repo, make_quote_service):
    quote_repo.create("ابدأ بما تستطيع.")
    service = make_quote_service()

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    service._quote_usage_repo.record_usage = _boom  # inject failure mid-transaction

    with pytest.raises(RuntimeError):
        service.get_or_assign_daily_quote("2026-09-21")

    # The whole transaction must have rolled back: no Day row left with a
    # quote assigned (or no Day row at all — either way, no partial state).
    day = DayRepository(db_connection).get_by_date("2026-09-21")
    assert day is None or day.quote_text is None

    usage_count = db_connection.execute("SELECT COUNT(*) AS c FROM quote_usage").fetchone()["c"]
    assert usage_count == 0


def test_rollback_does_not_advance_rotation_state(db_connection, quote_repo, rotation_state_repo, make_quote_service):
    # Exhaust the single normal quote's cycle first, so the next call
    # would need to advance the cycle — then make that call fail.
    quote_repo.create("الوحيدة")
    service = make_quote_service()
    service.get_or_assign_daily_quote("2026-09-01")
    cycle_before = rotation_state_repo.get_current_cycle()

    failing_service = make_quote_service()
    failing_service._quote_usage_repo.record_usage = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))

    with pytest.raises(RuntimeError):
        failing_service.get_or_assign_daily_quote("2026-09-02")

    assert rotation_state_repo.get_current_cycle() == cycle_before


def test_pool_membership_uses_current_status_history_unchanged(db_connection, quote_repo, make_quote_service):
    quote_a = quote_repo.create("A")
    quote_repo.create("B")

    service = make_quote_service(random_source=random.Random(2))
    first = service.get_or_assign_daily_quote("2026-09-01")
    second = service.get_or_assign_daily_quote("2026-09-02")
    assert {first.day.quote_text, second.day.quote_text} == {"A", "B"}

    # Mark A as favorite now.
    quote_repo.set_favorite(quote_a.id, True)

    fav_service = make_quote_service(favorite_selection_probability=1.0, random_source=random.Random(9))
    third = fav_service.get_or_assign_daily_quote("2026-09-03")
    fourth = fav_service.get_or_assign_daily_quote("2026-09-04")
    # A is now favorite-pool and can repeat.
    assert third.day.quote_text == "A"
    assert fourth.day.quote_text == "A"

    # The original selection of A (back when it was normal) is unchanged
    # in history: recorded as a normal (non-favorite) selection.
    row = db_connection.execute(
        "SELECT is_favorite_selection FROM quote_usage WHERE quote_id = ? ORDER BY id ASC LIMIT 1",
        (quote_a.id,),
    ).fetchone()
    assert row["is_favorite_selection"] == 0


def test_selecting_favorite_never_advances_or_resets_normal_cycle(
    db_connection, quote_repo, rotation_state_repo, make_quote_service
):
    quote_repo.create("عادية 1")
    quote_repo.create("عادية 2")
    quote_repo.create("مفضلة", is_favorite=True)

    fav_service = make_quote_service(favorite_selection_probability=1.0, random_source=random.Random(1))
    fav_service.get_or_assign_daily_quote("2026-09-01")
    cycle_after_favorite = rotation_state_repo.get_current_cycle()
    assert cycle_after_favorite == 1  # unchanged by a favorite-only selection

    normal_service = make_quote_service(favorite_selection_probability=0.0, random_source=random.Random(4))
    texts = [
        normal_service.get_or_assign_daily_quote(d).day.quote_text
        for d in ["2026-09-02", "2026-09-03"]
    ]
    assert set(texts) == {"عادية 1", "عادية 2"}  # neither consumed by the favorite pick


def _build_service(conn):
    return QuoteService(
        conn,
        QuoteRepository(conn),
        DayRepository(conn),
        QuoteUsageRepository(conn),
        QuoteRotationStateRepository(conn),
        favorite_selection_probability=0.0,
        random_source=random.Random(),
    )


def test_concurrent_calls_assign_exactly_one_quote(db_path):
    seed_conn = create_connection(db_path)
    apply_migrations(seed_conn)
    QuoteRepository(seed_conn).create("ابدأ بما تستطيع.")
    QuoteRepository(seed_conn).create("خطوة صغيرة كل يوم.")
    seed_conn.close()

    results = []
    errors = []

    def _worker():
        conn = create_connection(db_path)
        try:
            assignment = _build_service(conn).get_or_assign_daily_quote("2026-09-21")
            results.append(assignment.day.quote_text)
        except Exception as exc:  # surfaced via errors, not swallowed
            errors.append(exc)
        finally:
            conn.close()

    threads = [threading.Thread(target=_worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(set(results)) == 1  # every caller ended up seeing the same assigned quote

    check_conn = create_connection(db_path)
    usage_count = check_conn.execute("SELECT COUNT(*) AS c FROM quote_usage").fetchone()["c"]
    check_conn.close()
    assert usage_count == 1  # exactly one assignment was ever persisted