BEGIN TRANSACTION;

CREATE TABLE quote_rotation_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_cycle INTEGER NOT NULL DEFAULT 1
);

INSERT INTO quote_rotation_state (id, current_cycle) VALUES (1, 1);

CREATE TABLE quote_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_id INTEGER NOT NULL UNIQUE REFERENCES days(id) ON DELETE CASCADE,
    quote_id INTEGER NOT NULL REFERENCES quotes(id),
    cycle_number INTEGER NOT NULL,
    is_favorite_selection INTEGER NOT NULL CHECK (is_favorite_selection IN (0, 1)),
    selected_at TEXT NOT NULL
);

CREATE INDEX idx_quote_usage_cycle ON quote_usage(cycle_number, is_favorite_selection);

COMMIT;