"""Phase 7A: migration atomicity and pre-migration backup.

Backend-only (stdlib + sqlite3, no Qt, no Windows). Every test performs real
assertions against real SQLite files in a temporary directory; nothing here
depends on PySide6 being installed, so none of it can silently no-op.

Failure boundaries covered
--------------------------
* SQL error mid-migration                -> rolled back, version not recorded
* failure at the version-row write       -> the exact gap the old runner had
* real process death (os._exit) inside the migration transaction
* backup cannot be written               -> migration never starts

NOT covered (cannot be simulated portably): power loss / OS crash during the
final COMMIT fsync. That relies on SQLite's own journal guarantees, which the
os._exit test exercises only up to process-kill level.
"""
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from app.database import migrations
from app.database.connection import create_connection
from app.database.migrations import MigrationError, apply_migrations

REAL_DIR = migrations.MIGRATIONS_DIR
_REAL_CLOCK = migrations.utc_now_iso
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- helpers

def _migrations_subset(tmp_path: Path, versions, extra=None, name="mig") -> Path:
    """A migrations dir holding only the given REAL files (+ synthetic extras)."""
    directory = tmp_path / name
    directory.mkdir(exist_ok=True)
    for path in REAL_DIR.glob("*.sql"):
        if int(path.name.split("_")[0]) in versions:
            (directory / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    for filename, sql in (extra or {}).items():
        (directory / filename).write_text(sql, encoding="utf-8")
    return directory


def _use(monkeypatch, directory: Path) -> None:
    monkeypatch.setattr(migrations, "MIGRATIONS_DIR", directory)


def _build_v3_database(tmp_path: Path, monkeypatch) -> Path:
    """An existing 'production' database at schema v3 with real rows."""
    db_path = tmp_path / "daily_sticky.db"
    _use(monkeypatch, _migrations_subset(tmp_path, {1, 2, 3}, name="mig_v3"))
    conn = create_connection(db_path)
    apply_migrations(conn)
    conn.execute("INSERT INTO days (date, created_at, updated_at) VALUES ('2026-09-20','t','t')")
    conn.execute(
        "INSERT INTO tasks (day_id, text, position, priority, created_at, updated_at) "
        "VALUES (1, 'مهمة قديمة', 0, 'HIGH', 't', 't')"
    )
    conn.execute(
        "INSERT INTO tasks (day_id, text, position, is_completed, created_at, updated_at) "
        "VALUES (1, 'منجزة', 1, 1, 't', 't')"
    )
    conn.execute("INSERT INTO quotes (text, created_at, updated_at) VALUES ('q','t','t')")
    conn.close()
    _use(monkeypatch, REAL_DIR)
    return db_path


def _columns(conn, table="tasks"):
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def _versions(conn):
    return sorted(row[0] for row in conn.execute("SELECT version FROM schema_migrations"))


def _backups(db_path: Path):
    directory = db_path.parent / "backups"
    return sorted(directory.glob("*.bak")) if directory.exists() else []


def _snapshot(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    try:
        return (
            conn.execute("SELECT id, day_id, text, is_completed, position, priority FROM tasks ORDER BY id").fetchall(),
            sorted(r[0] for r in conn.execute("SELECT version FROM schema_migrations")),
            [r[1] for r in conn.execute("PRAGMA table_info(tasks)")],
        )
    finally:
        conn.close()


# ------------------------------------------------------------ backup rules

def test_fresh_database_gets_no_backup(tmp_path):
    db_path = tmp_path / "fresh.db"
    conn = create_connection(db_path)
    apply_migrations(conn)
    assert _versions(conn) == [1, 2, 3, 4]
    conn.close()
    assert _backups(db_path) == []


def test_no_pending_migration_creates_no_backup(tmp_path):
    db_path = tmp_path / "current.db"
    conn = create_connection(db_path)
    apply_migrations(conn)
    apply_migrations(conn)
    apply_migrations(conn)
    conn.close()
    assert _backups(db_path) == []
    assert not (tmp_path / "backups").exists()


def test_pending_migration_creates_backup_with_predictable_name(tmp_path, monkeypatch):
    db_path = _build_v3_database(tmp_path, monkeypatch)
    conn = create_connection(db_path)
    apply_migrations(conn)
    conn.close()
    backups = _backups(db_path)
    assert [b.name for b in backups] == ["daily_sticky.pre-migration-v003-to-v004.bak"]
    assert not list((tmp_path / "backups").glob("*.tmp"))


def test_backup_contains_pre_migration_state(tmp_path, monkeypatch):
    db_path = _build_v3_database(tmp_path, monkeypatch)
    before = _snapshot(db_path)
    conn = create_connection(db_path)
    apply_migrations(conn)
    conn.close()

    backup = _backups(db_path)[0]
    assert _snapshot(backup) == before
    assert "source_task_id" not in _snapshot(backup)[2]
    assert _snapshot(backup)[1] == [1, 2, 3]
    # ...while the live database really moved forward.
    live_rows, live_versions, live_cols = _snapshot(db_path)
    assert live_versions == [1, 2, 3, 4]
    assert "source_task_id" in live_cols
    assert live_rows == before[0]


def test_custom_backup_dir_is_used(tmp_path, monkeypatch):
    db_path = _build_v3_database(tmp_path, monkeypatch)
    target = tmp_path / "elsewhere"
    conn = create_connection(db_path)
    apply_migrations(conn, backup_dir=target)
    conn.close()
    assert len(list(target.glob("*.bak"))) == 1
    assert _backups(db_path) == []


def test_unwritable_backup_aborts_before_any_change(tmp_path, monkeypatch):
    db_path = _build_v3_database(tmp_path, monkeypatch)
    before = _snapshot(db_path)
    blocker = tmp_path / "not_a_directory"
    blocker.write_text("i am a file", encoding="utf-8")

    conn = create_connection(db_path)
    with pytest.raises(MigrationError):
        apply_migrations(conn, backup_dir=blocker / "sub")
    conn.close()
    assert _snapshot(db_path) == before


# ------------------------------------------------------ success / upgrade

def test_successful_migration_records_schema_and_version(tmp_path, monkeypatch):
    db_path = _build_v3_database(tmp_path, monkeypatch)
    conn = create_connection(db_path)
    apply_migrations(conn)
    assert "source_task_id" in _columns(conn)
    assert _versions(conn) == [1, 2, 3, 4]
    index = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name = 'idx_tasks_day_source'"
    ).fetchone()
    assert index is not None
    assert conn.in_transaction is False
    conn.close()


def test_upgrade_preserves_ids_priorities_and_history(tmp_path, monkeypatch):
    db_path = _build_v3_database(tmp_path, monkeypatch)
    conn = create_connection(db_path)
    apply_migrations(conn)
    rows = conn.execute(
        "SELECT id, day_id, text, is_completed, position, priority, source_task_id "
        "FROM tasks ORDER BY id"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        (1, 1, "مهمة قديمة", 0, 0, "HIGH", None),
        (2, 1, "منجزة", 1, 1, "MEDIUM", None),
    ]
    assert conn.execute("SELECT date FROM days WHERE id = 1").fetchone()[0] == "2026-09-20"
    assert conn.execute("SELECT text FROM quotes").fetchone()[0] == "q"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


def test_rerun_after_success_is_idempotent_and_makes_no_new_backup(tmp_path, monkeypatch):
    db_path = _build_v3_database(tmp_path, monkeypatch)
    conn = create_connection(db_path)
    apply_migrations(conn)
    apply_migrations(conn)
    assert _versions(conn) == [1, 2, 3, 4]
    conn.close()
    assert len(_backups(db_path)) == 1


def test_all_real_migrations_have_a_single_version_row_each(tmp_path):
    conn = create_connection(tmp_path / "x.db")
    apply_migrations(conn)
    rows = conn.execute("SELECT version, COUNT(*) AS c FROM schema_migrations GROUP BY version").fetchall()
    assert [(r["version"], r["c"]) for r in rows] == [(1, 1), (2, 1), (3, 1), (4, 1)]
    assert conn.execute("SELECT current_cycle FROM quote_rotation_state WHERE id = 1").fetchone()[0] == 1
    conn.close()


# --------------------------------------------------------------- failures

BAD_005 = {
    "005_synthetic_failing.sql": (
        "BEGIN TRANSACTION;\n"
        "CREATE TABLE half_done (id INTEGER);\n"
        "ALTER TABLE tasks ADD COLUMN extra_col TEXT;\n"
        "INSERT INTO table_that_does_not_exist VALUES (1);\n"
        "COMMIT;\n"
    )
}


def test_failed_migration_is_rolled_back_and_not_recorded(tmp_path, monkeypatch):
    db_path = _build_v3_database(tmp_path, monkeypatch)
    _use(monkeypatch, _migrations_subset(tmp_path, {1, 2, 3, 4}, BAD_005, name="mig_bad"))
    conn = create_connection(db_path)
    with pytest.raises(MigrationError):
        apply_migrations(conn)

    # 004 (good) committed on its own; 005 left no trace at all.
    assert _versions(conn) == [1, 2, 3, 4]
    assert "extra_col" not in _columns(conn)
    assert conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'half_done'").fetchone() is None
    assert conn.in_transaction is False
    conn.close()


def test_failed_migration_keeps_user_data_and_a_backup_exists(tmp_path, monkeypatch):
    db_path = _build_v3_database(tmp_path, monkeypatch)
    before_rows = _snapshot(db_path)[0]
    _use(monkeypatch, _migrations_subset(tmp_path, {1, 2, 3, 4}, BAD_005, name="mig_bad"))
    conn = create_connection(db_path)
    message = ""
    try:
        apply_migrations(conn)
    except MigrationError as exc:
        message = str(exc)
    conn.close()

    assert "005_synthetic_failing.sql" in message
    assert "backup" in message
    assert _snapshot(db_path)[0] == before_rows
    backups = _backups(db_path)
    assert len(backups) == 1 and str(backups[0]) in message
    assert _snapshot(backups[0])[1] == [1, 2, 3]


def test_restart_after_failed_migration_retries_cleanly_and_keeps_old_backup(tmp_path, monkeypatch):
    db_path = _build_v3_database(tmp_path, monkeypatch)
    _use(monkeypatch, _migrations_subset(tmp_path, {1, 2, 3, 4}, BAD_005, name="mig_bad"))
    for _ in range(2):
        conn = create_connection(db_path)
        with pytest.raises(MigrationError):
            apply_migrations(conn)
        conn.close()
    # second attempt backs up the (4-versions-now) DB under a NEW name; nothing overwritten
    names = [b.name for b in _backups(db_path)]
    assert names == [
        "daily_sticky.pre-migration-v003-to-v005.bak",
        "daily_sticky.pre-migration-v004-to-v005.bak",
    ]

    # Ship a fixed 005 -> the same database upgrades without manual repair.
    fixed = {"005_synthetic_failing.sql": "ALTER TABLE tasks ADD COLUMN extra_col TEXT;\n"}
    _use(monkeypatch, _migrations_subset(tmp_path, {1, 2, 3, 4}, fixed, name="mig_fixed"))
    conn = create_connection(db_path)
    apply_migrations(conn)
    assert _versions(conn) == [1, 2, 3, 4, 5]
    assert "extra_col" in _columns(conn)
    conn.close()


def test_failure_at_version_row_write_leaves_no_false_state(tmp_path, monkeypatch):
    """The exact gap of the old runner: schema statements done, version row fails."""
    db_path = _build_v3_database(tmp_path, monkeypatch)
    before = _snapshot(db_path)

    def exploding_clock():
        raise RuntimeError("simulated failure while writing the version row")

    monkeypatch.setattr(migrations, "utc_now_iso", exploding_clock)
    conn = create_connection(db_path)
    with pytest.raises(MigrationError):
        apply_migrations(conn)
    conn.close()

    assert _snapshot(db_path) == before
    # Next launch (real clock) succeeds; before the fix this raised
    # "duplicate column name: source_task_id" and locked the user out.
    monkeypatch.setattr(migrations, "utc_now_iso", _REAL_CLOCK)
    conn = create_connection(db_path)
    apply_migrations(conn)
    assert _versions(conn) == [1, 2, 3, 4]
    conn.close()


def test_process_death_inside_migration_transaction_leaves_old_state(tmp_path, monkeypatch):
    """Real process kill (os._exit) after the schema statements, before COMMIT."""
    db_path = _build_v3_database(tmp_path, monkeypatch)
    before = _snapshot(db_path)

    child = textwrap.dedent(
        f"""
        import os, sys
        sys.path.insert(0, r"{PROJECT_ROOT}")
        from app.database import migrations
        from app.database.connection import create_connection
        migrations.utc_now_iso = lambda: os._exit(9)   # dies mid-transaction
        conn = create_connection(r"{db_path}")
        migrations.apply_migrations(conn)
        """
    )
    result = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True)
    assert result.returncode == 9, result.stderr

    assert _snapshot(db_path) == before   # schema AND version rolled back together
    conn = create_connection(db_path)
    apply_migrations(conn)                # restart recovers normally
    assert _versions(conn) == [1, 2, 3, 4]
    assert "source_task_id" in _columns(conn)
    conn.close()


# ------------------------------------------------- migration file handling

def test_legacy_wrapper_and_unwrapped_files_both_work(tmp_path, monkeypatch):
    extra = {"001_a.sql": "BEGIN TRANSACTION;\nCREATE TABLE a (i INTEGER);\nCOMMIT;\n",
             "002_b.sql": "-- no wrapper, with a comment\nCREATE TABLE b (i INTEGER);\n"
                          "CREATE TRIGGER tb AFTER INSERT ON b BEGIN INSERT INTO a VALUES (1); END;\n"}
    _use(monkeypatch, _migrations_subset(tmp_path, set(), extra, name="mig_forms"))
    conn = create_connection(tmp_path / "forms.db")
    apply_migrations(conn)
    conn.execute("INSERT INTO b VALUES (7)")
    assert conn.execute("SELECT COUNT(*) FROM a").fetchone()[0] == 1   # trigger body stayed whole
    assert _versions(conn) == [1, 2]
    conn.close()


def test_inner_transaction_control_is_rejected_before_anything_runs(tmp_path, monkeypatch):
    db_path = _build_v3_database(tmp_path, monkeypatch)
    before = _snapshot(db_path)
    bad = {"005_sneaky.sql": "CREATE TABLE s1 (i);\nCOMMIT;\nCREATE TABLE s2 (i);\n"}
    _use(monkeypatch, _migrations_subset(tmp_path, {1, 2, 3}, bad, name="mig_sneaky"))
    conn = create_connection(db_path)
    with pytest.raises(MigrationError):
        apply_migrations(conn)
    conn.close()
    assert _snapshot(db_path) == before
    conn = sqlite3.connect(str(db_path))
    leaked = conn.execute("SELECT name FROM sqlite_master WHERE name IN ('s1', 's2')").fetchall()
    conn.close()
    assert leaked == []                     # not even the statement BEFORE the COMMIT ran
    assert _backups(db_path) == []          # rejected at parse time: no backup, no change


def test_in_memory_database_still_migrates_without_backup():
    conn = create_connection(":memory:")
    apply_migrations(conn)
    assert _versions(conn) == [1, 2, 3, 4]
    conn.close()