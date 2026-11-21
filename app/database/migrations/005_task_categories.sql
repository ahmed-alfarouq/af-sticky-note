BEGIN TRANSACTION;

-- Phase 7A: first-class task categories.
--
-- Migration strategy (chosen over ALTER TABLE ... NOT NULL DEFAULT ... REFERENCES):
-- SQLite rejects adding a REFERENCES column with a non-NULL default while
-- foreign-key enforcement is on ("Cannot add a REFERENCES column with
-- non-NULL default value", verified on this repo's SQLite 3.50.4). A full
-- table rebuild would give a DB-level NOT NULL but risks task IDs, the
-- self-referencing source_task_id lineage, and existing indexes. Instead:
--   1. create + deterministically seed categories,
--   2. add a NULLABLE FK column (allowed),
--   3. backfill every existing row to the default category in the same txn,
--   4. enforce non-NULL assignment in TaskService/TaskRepository from here on.
-- NULL is therefore unreachable through the supported application path; only
-- out-of-band raw SQL could produce it, and TaskRepository hydrates such rows
-- (or pre-005 readers) as the default category defensively.
-- Category deletion is RESTRICT (never CASCADE) so history can never be wiped
-- by removing a category; deactivation is via is_active.
-- Seed timestamps are a fixed constant so seeding is fully deterministic.

CREATE TABLE categories (
    id TEXT PRIMARY KEY,
    name_ar TEXT NOT NULL CHECK (length(trim(name_ar)) > 0),
    icon_key TEXT NOT NULL CHECK (length(trim(icon_key)) > 0),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

INSERT OR IGNORE INTO categories (id, name_ar, icon_key, sort_order, is_active, created_at, updated_at) VALUES
    ('religion', 'دين', 'religion', 10, 1, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'),
    ('work', 'عمل', 'work', 20, 1, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'),
    ('life', 'حياة', 'life', 30, 1, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'),
    ('general', 'عام', 'general', 40, 1, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00');

ALTER TABLE tasks ADD COLUMN category_id TEXT REFERENCES categories(id) ON DELETE RESTRICT;

UPDATE tasks SET category_id = 'general' WHERE category_id IS NULL;

CREATE INDEX idx_tasks_category ON tasks(category_id);

COMMIT;
