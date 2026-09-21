"""Explicit transaction boundary for multi-step database operations.

SQLite's Python driver has no real notion of nested transactions: if
two repository methods each manage their own commit (as most of this
codebase's simple, single-statement repo methods correctly do), then
composing them into one logical operation does NOT make that
operation atomic — whichever inner `with connection:` block finishes
first commits everything so far, not just its own step. A crash
between the two leaves the first half permanently persisted.

UnitOfWork exists for the small number of operations that must
succeed or fail as a single unit (e.g. QuoteService's daily
assignment: select a quote, record its usage, stamp the Day, maybe
advance the rotation cycle). Repository methods that are meant to be
called *inside* a UnitOfWork block must not commit or roll back
themselves — see the docstrings on DayRepository.set_quote_text,
QuoteUsageRepository.record_usage, and
QuoteRotationStateRepository.get_current_cycle/advance_cycle.

Uses BEGIN IMMEDIATE rather than the driver's default deferred BEGIN,
so the write lock is acquired the moment the block starts rather than
lazily on the first write statement. That is what protects against
two callers both deciding "no quote assigned yet" and racing to
assign one: the second caller blocks at BEGIN IMMEDIATE (and, if the
first is still holding the lock past the connection's busy timeout,
raises sqlite3.OperationalError) instead of interleaving writes with
the first.
"""
from __future__ import annotations

import sqlite3


class UnitOfWork:
    """Reusable transaction context manager for one sqlite3 connection.

    A single instance can be entered multiple times (once per logical
    operation) — it holds no per-transaction state beyond the
    connection itself.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def __enter__(self) -> "UnitOfWork":
        self._conn.execute("BEGIN IMMEDIATE")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        return False  # never swallow the exception ourselves
