-- 001-initial.sql
-- Captures the v0.1.0 schema verbatim. Idempotent: safe to run on a fresh
-- DB or on an existing v0.1.0 DB that pre-dates the migrations system.
--
-- NOTE: This faithfully reproduces v0.1.0 init_db.py, which is missing two
-- columns that db.py writes to (roles.source_file, roles.previous_fit).
-- Migration 002 repairs that. They are deliberately split so existing
-- v0.1.0 DBs upgrade cleanly to schema_version 1, then 2.

CREATE TABLE IF NOT EXISTS schema_version (
    version         INTEGER PRIMARY KEY,
    migration_name  TEXT,
    applied_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS companies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    website         TEXT,
    size            TEXT,
    stage           TEXT,
    domain          TEXT,
    hq              TEXT,
    remote_friendly INTEGER,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS roles (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id        INTEGER NOT NULL REFERENCES companies(id),
    title             TEXT NOT NULL,
    url               TEXT,
    source            TEXT,
    status            TEXT DEFAULT 'Researching',
    tech_fit          REAL,
    culture_fit       REAL,
    overall_fit       REAL,
    comp_min          INTEGER,
    comp_max          INTEGER,
    remote            TEXT,
    location          TEXT,
    jd_text           TEXT,
    fit_notes         TEXT,
    next_action       TEXT,
    next_action_due   TEXT,
    disqualified      INTEGER DEFAULT 0,
    disqualify_reason TEXT,
    created_at        TEXT DEFAULT (datetime('now')),
    updated_at        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contacts (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id            INTEGER NOT NULL REFERENCES companies(id),
    name                  TEXT NOT NULL,
    title                 TEXT,
    linkedin_url          TEXT,
    email                 TEXT,
    relationship          TEXT,
    linkedin_search_query TEXT,
    notes                 TEXT,
    discovered_at         TEXT,
    is_target             INTEGER DEFAULT 0,
    outreach_sent_at      TEXT,
    response_received     INTEGER DEFAULT 0,
    created_at            TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id             INTEGER NOT NULL REFERENCES roles(id),
    company_id          INTEGER NOT NULL REFERENCES companies(id),
    submitted_at        TEXT,
    method              TEXT,
    ats_url             TEXT,
    ats_name            TEXT,
    confirmation_code   TEXT,
    resume_version      TEXT,
    resume_bullets_used TEXT,
    cover_letter_used   TEXT,
    screening_questions TEXT,
    notes               TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS activity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id     INTEGER REFERENCES roles(id),
    company_id  INTEGER NOT NULL REFERENCES companies(id),
    contact_id  INTEGER REFERENCES contacts(id),
    type        TEXT NOT NULL,
    detail      TEXT,
    old_status  TEXT,
    new_status  TEXT,
    logged_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS search_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at          TEXT DEFAULT (datetime('now')),
    queries_run     INTEGER,
    roles_found     INTEGER,
    roles_added     INTEGER,
    roles_duped     INTEGER,
    roles_screened  INTEGER,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS analysis_snapshots (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id          INTEGER NOT NULL REFERENCES roles(id),
    generated_at     TEXT DEFAULT (datetime('now')),
    tool             TEXT,
    skill_type       TEXT NOT NULL,
    file_path        TEXT NOT NULL,
    overall_fit      REAL,
    verdict          TEXT,
    regenerated_from INTEGER,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_analysis_role      ON analysis_snapshots(role_id);
CREATE INDEX IF NOT EXISTS idx_analysis_skill     ON analysis_snapshots(skill_type);
CREATE INDEX IF NOT EXISTS idx_analysis_generated ON analysis_snapshots(generated_at);

CREATE TRIGGER IF NOT EXISTS companies_updated
AFTER UPDATE ON companies
BEGIN
    UPDATE companies SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS roles_updated
AFTER UPDATE ON roles
BEGIN
    UPDATE roles SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE VIEW IF NOT EXISTS pipeline_summary AS
SELECT
    r.id,
    c.name          AS company,
    r.title,
    r.status,
    r.overall_fit,
    r.next_action,
    r.next_action_due,
    r.source,
    r.remote,
    r.comp_min,
    r.comp_max,
    r.updated_at,
    julianday('now') - julianday(r.updated_at) AS days_since_update
FROM roles r
JOIN companies c ON c.id = r.company_id
WHERE r.disqualified = 0
ORDER BY r.overall_fit DESC, r.updated_at DESC;

CREATE VIEW IF NOT EXISTS needs_action AS
SELECT
    c.name          AS company,
    r.id            AS role_id,
    r.title,
    r.status,
    r.next_action,
    r.next_action_due,
    r.overall_fit,
    julianday('now') - julianday(r.updated_at) AS days_stale
FROM roles r
JOIN companies c ON c.id = r.company_id
WHERE r.disqualified = 0
  AND r.status NOT IN ('Closed Won', 'Closed Lost')
  AND (
      r.next_action_due <= date('now', '+2 days')
      OR julianday('now') - julianday(r.updated_at) >= 5
  )
ORDER BY r.next_action_due ASC, days_stale DESC;

CREATE VIEW IF NOT EXISTS application_log AS
SELECT
    a.id,
    c.name          AS company,
    r.title,
    a.submitted_at,
    a.method,
    a.ats_name,
    a.resume_version,
    a.ats_url,
    a.confirmation_code,
    r.status
FROM applications a
JOIN roles r ON r.id = a.role_id
JOIN companies c ON c.id = a.company_id
ORDER BY a.submitted_at DESC;
