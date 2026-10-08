"""Phase 7A: category migration (005) and data-integrity tests.

Backend-only (stdlib + sqlite3, no Qt). Covers fresh installs and upgrades
from schema versions 1-4: every pre-existing task keeps its ids, timestamps,
priority, and rollover lineage, and lands on the default category.
"""
import sqlite3

import pytest

from app.core.models import DEFAULT_CATEGORY_ID
from app.database import migrations
from app.database.category_repository import CategoryRepository
from app.database.connection import create_connection
from app.database.migrations import apply_migrations
from app.database.task_repository import TaskRepository

REAL_DIR = migrations.MIGRATIONS_DIR

EXPECTED_SEEDS = [
    ("religion", "دين", "religion", 10),
    ("work", "عمل", "work", 20),
    ("life", "حياة", "life", 30),
    ("general", "عام", "general", 40),
]


def _use(monkeypatch, directory):
    monkeypatch.setattr(migrations, "MIGRATIONS_DIR", directory)


def _subset_dir(tmp_path, versions, name):
    directory = tmp_path / name
    directory.mkdir(exist_ok=True)
    for path in REAL_DIR.glob("*.sql"):
        if int(path.name.split("_")[0]) in versions:
            (directory / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return directory


def _build_versioned_db(tmp_path, monkeypatch, versions, name):
    """A 'production' database frozen at the given schema versions with rows."""
    db_path = tmp_path / f"{name}.db"
    _use(monkeypatch, _subset_dir(tmp_path, versions, f"mig_{name}"))
    conn = create_connection(db_path)
    apply_migrations(conn)
    conn.execute(
        "INSERT INTO days (id, date, created_at, updated_at) "
        "VALUES (1, '2026-09-20', '2026-09-20T10:00:00', '2026-09-20T10:00:00')"
    )
    has_priority = max(versions) >= 3
    if has_priority:
        conn.execute(
            "INSERT INTO tasks (id, day_id, text, is_completed, position, priority, created_at, updated_at) "
            "VALUES (1, 1, 'مهمة قديمة', 0, 0, 'HIGH', '2026-09-20T10:00:00', '2026-09-20T11:00:00')"
        )
        conn.execute(
            "INSERT INTO tasks (id, day_id, text, is_completed, position, created_at, updated_at) "
            "VALUES (2, 1, 'منجزة', 1, 1, '2026-09-20T10:05:00', '2026-09-20T11:05:00')"
        )
    else:
        conn.execute(
            "INSERT INTO tasks (id, day_id, text, is_completed, position, created_at, updated_at) "
            "VALUES (1, 1, 'مهمة قديمة', 0, 0, '2026-09-20T10:00:00', '2026-09-20T11:00:00')"
        )
        conn.execute(
            "INSERT INTO tasks (id, day_id, text, is_completed, position, created_at, updated_at) "
            "VALUES (2, 1, 'منجزة', 1, 1, '2026-09-20T10:05:00', '2026-09-20T11:05:00')"
        )
    if max(versions) >= 4:
        # A rollover copy: child of task 1 on a second day, preserving lineage.
        conn.execute(
            "INSERT INTO days (id, date, created_at, updated_at) "
            "VALUES (2, '2026-09-21', '2026-09-21T00:00:00', '2026-09-21T00:00:00')"
        )
        cols = "id, day_id, text, is_completed, position, priority, source_task_id, created_at, updated_at"
        conn.execute(
            f"INSERT INTO tasks ({cols}) "
            "VALUES (3, 2, 'مهمة قديمة', 0, 0, 'HIGH', 1, '2026-09-21T00:00:01', '2026-09-21T00:00:01')"
        )
    conn.close()
    _use(monkeypatch, REAL_DIR)
    return db_path


def _upgrade(db_path):
    conn = create_connection(db_path)
    apply_migrations(conn)
    return conn


# ------------------------------------------------------------ fresh install

def test_fresh_database_seeds_categories_deterministically(db_connection):
    repo = CategoryRepository(db_connection)
    categories = repo.list_all()
    assert [(c.id, c.name_ar, c.icon_key, c.sort_order) for c in categories] == EXPECTED_SEEDS
    assert all(c.is_active for c in categories)
    assert all(c.created_at and c.updated_at for c in categories)
    # Deterministic: identical timestamps for every seed row.
    assert len({(c.created_at, c.updated_at) for c in categories}) == 1
    versions = sorted(row[0] for row in db_connection.execute("SELECT version FROM schema_migrations"))
    assert versions == [1, 2, 3, 4, 5]


def test_fresh_database_tasks_table_has_category_index(db_connection):
    index = db_connection.execute(
        "SELECT 1 FROM sqlite_master WHERE name = 'idx_tasks_category'"
    ).fetchone()
    assert index is not None
    fk = [dict(row) for row in db_connection.execute("PRAGMA foreign_key_list(tasks)")]
    category_refs = [entry for entry in fk if entry["from"] == "category_id"]
    assert len(category_refs) == 1
    assert category_refs[0]["table"] == "categories"
    assert db_connection.execute("PRAGMA foreign_key_check").fetchall() == []


# ------------------------------------------------------------ upgrades v1-v4

@pytest.mark.parametrize("versions", [{1}, {1, 2}, {1, 2, 3}, {1, 2, 3, 4}])
def test_upgrade_from_each_version_assigns_default_category(tmp_path, monkeypatch, versions):
    name = "v" + "".join(str(v) for v in sorted(versions))
    db_path = _build_versioned_db(tmp_path, monkeypatch, versions, name)
    conn = _upgrade(db_path)

    versions_after = sorted(row[0] for row in conn.execute("SELECT version FROM schema_migrations"))
    assert versions_after == [1, 2, 3, 4, 5]

    rows = conn.execute("SELECT id, text, is_completed, position, category_id FROM tasks ORDER BY id").fetchall()
    by_id = {r[0]: (r[1], r[2], r[3], r[4]) for r in rows}
    assert by_id[1] == ("مهمة قديمة", 0, 0, DEFAULT_CATEGORY_ID)
    assert by_id[2] == ("منجزة", 1, 1, DEFAULT_CATEGORY_ID)
    # Every row, including any rollover lineage child (v4), gets the default.
    assert {r[4] for r in rows} == {DEFAULT_CATEGORY_ID}
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


def test_upgrade_preserves_ids_timestamps_and_priority(tmp_path, monkeypatch):
    db_path = _build_versioned_db(tmp_path, monkeypatch, {1, 2, 3}, "v123ts")
    conn = _upgrade(db_path)

    rows = conn.execute(
        "SELECT id, day_id, text, is_completed, position, priority, created_at, updated_at, category_id "
        "FROM tasks ORDER BY id"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        (1, 1, "مهمة قديمة", 0, 0, "HIGH", "2026-09-20T10:00:00", "2026-09-20T11:00:00", "general"),
        (2, 1, "منجزة", 1, 1, "MEDIUM", "2026-09-20T10:05:00", "2026-09-20T11:05:00", "general"),
    ]
    assert conn.execute("SELECT date FROM days WHERE id = 1").fetchone()[0] == "2026-09-20"
    conn.close()


def test_upgrade_preserves_rollover_lineage(tmp_path, monkeypatch):
    db_path = _build_versioned_db(tmp_path, monkeypatch, {1, 2, 3, 4}, "v1234lin")
    conn = _upgrade(db_path)

    child = conn.execute("SELECT id, day_id, source_task_id, category_id FROM tasks WHERE id = 3").fetchone()
    assert tuple(child) == (3, 2, 1, "general")
    parent = conn.execute("SELECT id, category_id FROM tasks WHERE id = 1").fetchone()
    assert tuple(parent) == (1, "general")
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


def test_upgrade_is_idempotent_and_seeds_stay_at_four_rows(tmp_path, monkeypatch):
    db_path = _build_versioned_db(tmp_path, monkeypatch, {1, 2}, "v12idem")
    conn = _upgrade(db_path)
    apply_migrations(conn)
    apply_migrations(conn)
    count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    assert count == 4
    assert sorted(row[0] for row in conn.execute("SELECT version FROM schema_migrations")) == [1, 2, 3, 4, 5]
    conn.close()


# ------------------------------------------------------------ integrity rules

def test_unknown_category_is_rejected_by_foreign_key(db_connection):
    day_id = db_connection.execute(
        "INSERT INTO days (date, created_at, updated_at) VALUES ('2026-09-20', 't', 't')"
    ).lastrowid
    with pytest.raises(sqlite3.IntegrityError):
        db_connection.execute(
            "INSERT INTO tasks (day_id, text, position, category_id, created_at, updated_at) "
            "VALUES (?, 'x', 0, 'no-such-category', 't', 't')",
            (day_id,),
        )
    task_id = db_connection.execute(
        "INSERT INTO tasks (day_id, text, position, category_id, created_at, updated_at) "
        "VALUES (?, 'ok', 0, 'general', 't', 't')",
        (day_id,),
    ).lastrowid
    with pytest.raises(sqlite3.IntegrityError):
        db_connection.execute("UPDATE tasks SET category_id = 'no-such-category' WHERE id = ?", (task_id,))


def test_referenced_category_cannot_be_deleted(db_connection):
    day_id = db_connection.execute(
        "INSERT INTO days (date, created_at, updated_at) VALUES ('2026-09-20', 't', 't')"
    ).lastrowid
    db_connection.execute(
        "INSERT INTO tasks (day_id, text, position, category_id, created_at, updated_at) "
        "VALUES (?, 'مهمة عامة', 0, 'general', 't', 't')",
        (day_id,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        db_connection.execute("DELETE FROM categories WHERE id = 'general'")
    # Unreferenced categories remain deletable (no historical data at risk).
    db_connection.execute(
        "INSERT INTO categories (id, name_ar, icon_key, sort_order, is_active, created_at, updated_at) "
        "VALUES ('tmp', 'مؤقت', 'tmp', 99, 1, 't', 't')"
    )
    db_connection.execute("DELETE FROM categories WHERE id = 'tmp'")
    assert CategoryRepository(db_connection).get_by_id("tmp") is None


def test_deactivating_category_keeps_tasks_valid(db_connection):
    repo = CategoryRepository(db_connection)
    repo.set_active("general", False)
    assert [c.id for c in repo.list_active()] == ["religion", "work", "life"]
    assert [c.id for c in repo.list_all()] == ["religion", "work", "life", "general"]

    task_repo = TaskRepository(db_connection)
    day_id = db_connection.execute(
        "INSERT INTO days (date, created_at, updated_at) VALUES ('2026-09-20', 't', 't')"
    ).lastrowid
    task = task_repo.create(day_id, "مهمة على فئة معطلة", category_id="general")
    assert task.category_id == "general"
    assert db_connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_renaming_category_preserves_task_identity(db_connection):
    db_connection.execute("UPDATE categories SET name_ar = 'دين محدث' WHERE id = 'religion'")
    task_repo = TaskRepository(db_connection)
    day_id = db_connection.execute(
        "INSERT INTO days (date, created_at, updated_at) VALUES ('2026-09-20', 't', 't')"
    ).lastrowid
    task = task_repo.create(day_id, "مهمة دينية", category_id="religion")
    assert task_repo.get_by_id(task.id).category_id == "religion"
    assert CategoryRepository(db_connection).get_by_id("religion").name_ar == "دين محدث"


def test_repository_hydrates_pre_005_rows_as_default(tmp_path, monkeypatch):
    """Rows read from a v4 database (no category column) surface as default."""
    db_path = _build_versioned_db(tmp_path, monkeypatch, {1, 2, 3, 4}, "v1234hyd")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        repo = TaskRepository(conn)
        tasks = repo.list_for_day(1)
        assert {t.category_id for t in tasks} == {"general"}
    finally:
        conn.close()
