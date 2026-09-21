"""Genuine concurrency test: two real threads, two real sqlite3
connections to the same database file, both racing to assign the
same calendar day's quote at the same time.

This is the actual proof for the spec's requirement: "The system
must protect against assigning two different quotes to the same
calendar day if get_or_assign_daily_quote() is called more than once
before the first assignment completes." BEGIN IMMEDIATE serializes
the two writers at the database level, so only one can ever complete
the assignment — no Python-level lock is involved anywhere in
QuoteService.
"""
import random
import threading

from app.core.services.quote_service import QuoteService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.quote_repository import QuoteRepository
from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
from app.database.quote_usage_repository import QuoteUsageRepository


def _build_service(db_path):
    """Each thread gets its own connection — sqlite3 connections are not
    thread-safe to share, and real apps would never share one across
    threads either."""
    conn = create_connection(db_path)
    apply_migrations(conn)
    return conn, QuoteService(
        conn,
        QuoteRepository(conn),
        DayRepository(conn),
        QuoteUsageRepository(conn),
        QuoteRotationStateRepository(conn),
        favorite_selection_probability=0.0,
        random_source=random.Random(threading.get_ident()),
    )


def test_two_threads_racing_for_the_same_day_produce_exactly_one_assignment(db_path):
    setup_conn = create_connection(db_path)
    apply_migrations(setup_conn)
    QuoteRepository(setup_conn).create("A")
    QuoteRepository(setup_conn).create("B")
    setup_conn.close()

    results = [None, None]
    barrier = threading.Barrier(2)

    def _worker(index):
        conn, service = _build_service(db_path)
        try:
            barrier.wait(timeout=5)  # maximize the chance both hit BEGIN IMMEDIATE together
            results[index] = service.get_or_assign_daily_quote("2026-09-01")
        finally:
            conn.close()

    t1 = threading.Thread(target=_worker, args=(0,))
    t2 = threading.Thread(target=_worker, args=(1,))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert results[0] is not None and results[1] is not None

    # Both threads must agree on the same quote for the same day.
    assert results[0].day.quote_text == results[1].day.quote_text

    # Exactly one of them actually performed the assignment.
    newly_assigned_flags = [results[0].was_newly_assigned, results[1].was_newly_assigned]
    assert sorted(newly_assigned_flags) == [False, True]

    # The database has exactly one usage row for this day — no
    # duplicate, no corruption.
    verify_conn = create_connection(db_path)
    day = DayRepository(verify_conn).get_by_date("2026-09-01")
    row = verify_conn.execute(
        "SELECT COUNT(*) AS c FROM quote_usage WHERE day_id = ?", (day.id,)
    ).fetchone()
    assert row["c"] == 1
    verify_conn.close()
