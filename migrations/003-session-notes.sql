-- 003-session-notes.sql
-- Stores session-level state that HANDOFF.md needs to render but that has
-- no natural home in the existing tables: open decisions waiting on the
-- candidate, end-of-session completion summaries, free-form notes.

CREATE TABLE IF NOT EXISTS session_notes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind         TEXT NOT NULL,          -- 'decision' | 'completion' | 'note'
    role_id      INTEGER REFERENCES roles(id),
    body         TEXT NOT NULL,
    resolved_at  TEXT,                   -- only used for kind='decision'
    resolution   TEXT,                   -- short note on how the decision was resolved
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_session_notes_kind     ON session_notes(kind);
CREATE INDEX IF NOT EXISTS idx_session_notes_resolved ON session_notes(resolved_at);
CREATE INDEX IF NOT EXISTS idx_session_notes_role     ON session_notes(role_id);
