"""SQLite connection factory. Single place that knows connection settings."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union


def create_connection(db_path: Union[str, Path]) -> sqlite3.Connection:
    """Open a SQLite connection configured for this application.

    Foreign-key enforcement is off by default in SQLite and must be
    enabled explicitly on every connection — it is not a database-wide
    setting. Caller owns the connection and must close it.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn