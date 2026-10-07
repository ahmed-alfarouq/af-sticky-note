"""Ordered, file-based SQLite migrations.

Migration files live in app/database/migrations/ as NNN_description.sql
and are applied at most once, tracked in schema_migrations, in order.
A failing migration must not leave a partially-applied schema and must
never silently drop existing data.

Transaction model (Phase 7A)
----------------------------
Each migration runs as ONE explicit transaction owned by this module:

    BEGIN IMMEDIATE
        <every statement of the migration file, executed one by one>
        INSERT INTO schema_migrations (version, applied_at) ...
    COMMIT

so "schema changed" and "version recorded" become durable together or not at
all. SQLite DDL (CREATE/ALTER/DROP/INDEX) is transactional, and the
connection is in native autocommit mode (isolation_level=None, see
connection.py), so these explicit statements are the only transaction
boundary. ``executescript()`` is deliberately NOT used: it commits any open
transaction first and a script containing its own COMMIT commits on its own,
which would make the version row a separate, later write.

Legacy files wrap their body in ``BEGIN TRANSACTION; ... COMMIT;``. Only that
outer wrapper is stripped (the runner supplies the transaction); any other
transaction-control statement inside a migration is rejected before anything
runs.

Pre-migration backup
--------------------
When at least one migration is pending AND the database already holds user
tables, a consistent copy is taken with SQLite's online backup API before any
change. No pending migration -> no backup. Fresh/empty and in-memory
databases have nothing to protect and are not backed up.
"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import List, Optional, Set, Tuple

from app.infrastructure.clock import utc_now_iso

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
BACKUP_DIR_NAME = "backups"
_FILENAME_PATTERN = re.compile(r"^(\d+)_.*\.sql$")

_BEGIN_RE = re.compile(
    r"^BEGIN(\s+(DEFERRED|IMMEDIATE|EXCLUSIVE))?(\s+TRANSACTION)?\s*;?$", re.IGNORECASE
)
_COMMIT_RE = re.compile(r"^(COMMIT|END)(\s+TRANSACTION)?\s*;?$", re.IGNORECASE)
_TXN_CONTROL_RE = re.compile(r"^(BEGIN|COMMIT|END|ROLLBACK|SAVEPOINT|RELEASE)\b", re.IGNORECASE)


class MigrationError(RuntimeError):
    """Raised when a migration (or the backup that guards it) fails."""


def _discover_migrations() -> List[Tuple[int, Path]]:
    found = []
    for path in MIGRATIONS_DIR.glob("*.sql"):
        match = _FILENAME_PATTERN.match(path.name)
        if not match:
            continue
        found.append((int(match.group(1)), path))
    return sorted(found, key=lambda item: item[0])


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _strip_leading_comments(statement: str) -> str:
    text = statement.lstrip()
    while True:
        if text.startswith("--"):
            newline = text.find("\n")
            text = "" if newline == -1 else text[newline + 1:].lstrip()
        elif text.startswith("/*"):
            end = text.find("*/")
            text = "" if end == -1 else text[end + 2:].lstrip()
        else:
            return text


def _split_statements(sql: str) -> List[str]:
    """Split a script into complete statements (trigger bodies stay whole)."""
    statements: List[str] = []
    buffer = ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            if _strip_leading_comments(buffer):
                statements.append(buffer.strip())
            buffer = ""
    if _strip_leading_comments(buffer):
        raise MigrationError("migration ends with an incomplete SQL statement")
    return statements


def _executable_statements(sql: str) -> List[str]:
    """Statements to run inside the runner's transaction.

    Strips a single outer BEGIN ... COMMIT wrapper; rejects any other
    transaction control.
    """
    statements = _split_statements(sql)
    if statements and _BEGIN_RE.match(_strip_leading_comments(statements[0])):
        if len(statements) < 2 or not _COMMIT_RE.match(_strip_leading_comments(statements[-1])):
            raise MigrationError("migration opens a transaction but does not end with COMMIT")
        statements = statements[1:-1]
    for statement in statements:
        if _TXN_CONTROL_RE.match(_strip_leading_comments(statement)):
            raise MigrationError(
                "migration contains transaction control; the runner owns the "
                f"transaction: {statement.splitlines()[0][:60]!r}"
            )
    return statements


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def _main_db_file(conn: sqlite3.Connection) -> Optional[Path]:
    for row in conn.execute("PRAGMA database_list"):
        if row[1] == "main":
            return Path(row[2]) if row[2] else None
    return None


def _has_user_tables(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' AND name != 'schema_migrations' LIMIT 1"
    ).fetchone()
    return row is not None


def _unique_path(path: Path) -> Path:
    """Never overwrite an existing backup: add -2, -3, ... instead."""
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _create_backup(
    conn: sqlite3.Connection,
    db_file: Path,
    backup_dir: Optional[Path],
    from_version: int,
    to_version: int,
) -> Path:
    """Copy the live database with SQLite's online backup API.

    Written to a temporary name, integrity-checked, then renamed, so a
    half-written file can never be mistaken for a valid backup.
    """
    target_dir = backup_dir if backup_dir is not None else db_file.parent / BACKUP_DIR_NAME
    final = _unique_path(
        target_dir
        / f"{db_file.stem}.pre-migration-v{from_version:03d}-to-v{to_version:03d}.bak"
    )
    temp = final.with_name(final.name + ".tmp")
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        dest = sqlite3.connect(str(temp))
        try:
            conn.backup(dest)
            check = dest.execute("PRAGMA quick_check").fetchone()
            if not check or check[0] != "ok":
                raise sqlite3.DatabaseError(f"backup integrity check failed: {check}")
        finally:
            dest.close()
        os.replace(temp, final)
    except Exception as exc:
        try:
            temp.unlink()
        except OSError:
            pass
        raise MigrationError(
            f"Pre-migration backup failed ({exc}); the database was not modified."
        ) from exc
    return final


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _read_applied(conn: sqlite3.Connection) -> Set[int]:
    table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
    ).fetchone()
    if table is None:
        return set()
    return {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}


def _apply_one(
    conn: sqlite3.Connection,
    version: int,
    path: Path,
    statements: List[str],
    backup_path: Optional[Path],
) -> None:
    try:
        conn.execute("BEGIN IMMEDIATE")
        for statement in statements:
            conn.execute(statement)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, utc_now_iso()),
        )
        conn.execute("COMMIT")
    except BaseException as exc:
        if conn.in_transaction:
            conn.rollback()
        if not isinstance(exc, Exception):
            raise  # KeyboardInterrupt / SystemExit: roll back, then propagate unchanged
        note = (
            f" The migration was rolled back; a pre-migration backup is at {backup_path}."
            if backup_path is not None
            else " The migration was rolled back."
        )
        raise MigrationError(f"Migration {version} ({path.name}) failed: {exc}.{note}") from exc


def apply_migrations(
    conn: sqlite3.Connection,
    backup_dir: Optional[Path] = None,
) -> None:
    """Apply every pending migration, each atomically with its version row.

    ``backup_dir`` defaults to ``<database directory>/backups``.
    """
    applied = _read_applied(conn)
    pending = [(v, p) for v, p in _discover_migrations() if v not in applied]
    if not pending:
        return

    # Parse everything first: a malformed file must fail before any backup/change.
    prepared = []
    for version, path in pending:
        try:
            prepared.append((version, path, _executable_statements(path.read_text(encoding="utf-8"))))
        except (MigrationError, OSError, UnicodeDecodeError) as exc:
            raise MigrationError(f"Migration {version} ({path.name}) is invalid: {exc}") from exc

    backup_path: Optional[Path] = None
    db_file = _main_db_file(conn)
    if db_file is not None and _has_user_tables(conn):
        backup_path = _create_backup(
            conn, db_file, backup_dir, max(applied) if applied else 0, pending[-1][0]
        )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        """
    )
    for version, path, statements in prepared:
        _apply_one(conn, version, path, statements, backup_path)