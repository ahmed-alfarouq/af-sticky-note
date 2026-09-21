"""Explicit unit-of-work transaction boundary.

Repositories issue plain conn.execute() calls and never commit or
roll back on their own. Grouping several repository calls into one
atomic operation is done by wrapping them in this context manager.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run the wrapped block as a single atomic transaction.

    Uses BEGIN IMMEDIATE to acquire SQLite's write lock upfront, so a
    second concurrent transaction() call on the same database file
    blocks until this one commits or rolls back, rather than
    interleaving writes.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()