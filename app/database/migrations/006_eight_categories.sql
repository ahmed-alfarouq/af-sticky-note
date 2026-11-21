BEGIN TRANSACTION;

-- Phase 0G: eight active categories (approved amendment 01,
-- docs/specs/amendment-01-eight-categories.md).
--
-- Additive only: the four original categories keep their stable ids, Arabic
-- names, active flags, tasks, and history. Nothing here renames, deletes,
-- deactivates, or remaps anything.
--
-- Two operations, both deterministic and re-runnable:
--   1. INSERT OR IGNORE the four new categories (personal, study, health,
--      home) with icon keys following the existing id-as-key convention.
--      Missing PNG assets resolve through the existing provider fallback;
--      icon files are deliberately out of scope for this migration.
--   2. Re-sort to the approved order by absolute sort_order assignment.
--      Only sort_order (and its updated_at stamp) changes on existing rows;
--      identity, names, active flags, and task references are untouched.
--      Approved order: general (10), work (20), personal (30), study (40),
--      health (50), home (60), religion (70), life (80). Gaps preserved for
--      future inserts, matching the 005 convention.
-- Seed timestamps reuse one fixed constant so application is fully
-- deterministic (same convention as 005_task_categories.sql).

INSERT OR IGNORE INTO categories (id, name_ar, icon_key, sort_order, is_active, created_at, updated_at) VALUES
    ('personal', 'شخصي', 'personal', 30, 1, '2026-10-14T00:00:00+00:00', '2026-10-14T00:00:00+00:00'),
    ('study', 'دراسة', 'study', 40, 1, '2026-10-14T00:00:00+00:00', '2026-10-14T00:00:00+00:00'),
    ('health', 'صحة', 'health', 50, 1, '2026-10-14T00:00:00+00:00', '2026-10-14T00:00:00+00:00'),
    ('home', 'المنزل', 'home', 60, 1, '2026-10-14T00:00:00+00:00', '2026-10-14T00:00:00+00:00');

UPDATE categories SET sort_order = 10, updated_at = '2026-10-14T00:00:00+00:00' WHERE id = 'general';
UPDATE categories SET sort_order = 70, updated_at = '2026-10-14T00:00:00+00:00' WHERE id = 'religion';
UPDATE categories SET sort_order = 80, updated_at = '2026-10-14T00:00:00+00:00' WHERE id = 'life';

COMMIT;
