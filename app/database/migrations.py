"""Ordered, file-based SQLite migrations.

Migration files live in app/database/migrations/ as NNN_description.sql
and are applied at most once, tracked in schema_migrations, in order.
A failing migration must not leave a partially-applied schema and must
never silently drop existing data.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import List, Tuple

from app.infrastructure.clock import utc_now_iso

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_FILENAME_PATTERN = re.compile(r"^(\d+)_.*\.sql$")


class MigrationError(RuntimeError):
    """Raised when a migration fails to apply."""


def _discover_migrations() -> List[Tuple[int, Path]]:
    found = []
    for path in MIGRATIONS_DIR.glob("*.sql"):
        match = _FILENAME_PATTERN.match(path.name)
        if not match:
            continue
        found.append((int(match.group(1)), path))
    return sorted(found, key=lambda item: item[0])


def apply_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        """
    )
    conn.commit()

    applied = {
        row["version"]
        for row in conn.execute("SELECT version FROM schema_migrations")
    }

    for version, path in _discover_migrations():
        if version in applied:
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            # The migration file wraps its own BEGIN/COMMIT, so this is
            # the schema change committing atomically as written.
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, utc_now_iso()),
            )
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise MigrationError(
                f"Migration {version} ({path.name}) failed: {exc}"
            ) from exc