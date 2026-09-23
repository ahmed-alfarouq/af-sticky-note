BEGIN TRANSACTION;

ALTER TABLE tasks ADD COLUMN source_task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL;

CREATE UNIQUE INDEX idx_tasks_day_source ON tasks(day_id, source_task_id) WHERE source_task_id IS NOT NULL;

COMMIT;
