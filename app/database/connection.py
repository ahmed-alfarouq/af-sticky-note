"""SQLite connection factory. Single place that knows connection settings."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union


def create_connection(db_path: Union[str, Path]) -> sqlite3.Connection:
    """Open a SQLite connection configured for this application.

    isolation_level=None puts the connection in SQLite's native
    autocommit mode: a statement run outside an explicit transaction
    commits itself immediately (preserving the old single-call
    behavior every repository relies on), while a statement run
    inside an explicit BEGIN...COMMIT block (see transaction.py)
    participates in that block instead of committing on its own.
    Repositories therefore never call commit()/rollback() themselves.

    Foreign-key enforcement is off by default in SQLite and must be
    enabled explicitly on every connection.
    """
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn