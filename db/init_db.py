"""
Job Search Pipeline — Database initialization
Run once to create pipeline.db
"""

import sqlite3

DB_PATH = "pipeline.db"

def init():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # ── Companies ──────────────────────────────────────────────────────────
    cur.execute("""
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
    )""")

    # ── Roles ──────────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id      INTEGER NOT NULL REFERENCES companies(id),
        title           TEXT NOT NULL,
        url             TEXT,
        source          TEXT,
        source_file     TEXT,                       -- original screenshot filename or other source identifier
        status          TEXT DEFAULT 'Researching',
        tech_fit        REAL,
        culture_fit     REAL,
        overall_fit     REAL,
        previous_fit    REAL,                       -- prior overall_fit, set on score revision (audit trail)
        comp_min        INTEGER,
        comp_max        INTEGER,
        remote          TEXT,
        location        TEXT,
        jd_text         TEXT,
        fit_notes       TEXT,
        next_action     TEXT,
        next_action_due TEXT,
        disqualified    INTEGER DEFAULT 0,
        disqualify_reason TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )""")

    # ── Contacts ───────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id      INTEGER NOT NULL REFERENCES companies(id),
        name            TEXT NOT NULL,
        title           TEXT,
        linkedin_url    TEXT,
        email           TEXT,
        relationship    TEXT,
        linkedin_search_query TEXT,
        notes           TEXT,
        discovered_at   TEXT,           -- when LinkedIn URL was found
        is_target       INTEGER DEFAULT 0,  -- priority outreach flag (0/1)
        outreach_sent_at TEXT,          -- when message was sent
        response_received INTEGER DEFAULT 0,  -- 0/1
        created_at      TEXT DEFAULT (datetime('now'))
    )""")

    # ── Applications ───────────────────────────────────────────────────────
    cur.execute("""
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
    )""")

    # ── Activity log ───────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS activity (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        role_id         INTEGER REFERENCES roles(id),
        company_id      INTEGER NOT NULL REFERENCES companies(id),
        contact_id      INTEGER REFERENCES contacts(id),
        type            TEXT NOT NULL,
        detail          TEXT,
        old_status      TEXT,
        new_status      TEXT,
        logged_at       TEXT DEFAULT (datetime('now'))
    )""")

    # ── Search runs ────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS search_runs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        run_at          TEXT DEFAULT (datetime('now')),
        queries_run     INTEGER,
        roles_found     INTEGER,
        roles_added     INTEGER,
        roles_duped     INTEGER,
        roles_screened  INTEGER,
        notes           TEXT
    )""")

    # ── Analysis Snapshots ─────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS analysis_snapshots (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        role_id         INTEGER NOT NULL REFERENCES roles(id),
        generated_at    TEXT DEFAULT (datetime('now')),
        tool            TEXT,                       -- 'claude-code' or other agent identifier
        skill_type      TEXT NOT NULL,              -- 'company-research' | 'analyze-jd' | 'score-fit' | 'find-contacts'
        file_path       TEXT NOT NULL,              -- relative path: references/analyses/...
        overall_fit     REAL,                       -- quick lookup: 1-10 score
        verdict         TEXT,                       -- 'pursue' | 'pass' | 'research'
        regenerated_from INTEGER,                   -- links to earlier version
        created_at      TEXT DEFAULT (datetime('now'))
    )""")

    # Indexes for analysis_snapshots
    cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_role ON analysis_snapshots(role_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_skill ON analysis_snapshots(skill_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_generated ON analysis_snapshots(generated_at)")

    # ── Stories ───────────────────────────────────────────────────────────
    # Verified work-story files in references/stories/ as first-class records.
    # The slug (filename without .md) is the canonical identity used by skills
    # to reference a story when drafting bullets, cover letters, or outreach.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stories (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        slug            TEXT NOT NULL UNIQUE,       -- e.g. "01-platform-migration"
        file_path       TEXT NOT NULL,              -- relative path: references/stories/01-platform-migration.md
        title           TEXT,                       -- optional human-readable title
        created_at      TEXT DEFAULT (datetime('now'))
    )""")

    # Join table: which stories backed which artifact (application, analysis, outreach).
    # Records "this draft used these stories" so interview prep can answer
    # "what did I tell them this story was?" weeks later.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS story_refs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        story_id        INTEGER NOT NULL REFERENCES stories(id),
        ref_type        TEXT NOT NULL,              -- 'application' | 'analysis' | 'outreach'
        ref_id          INTEGER NOT NULL,           -- foreign id for the ref_type
        created_at      TEXT DEFAULT (datetime('now'))
    )""")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_story_refs_story ON story_refs(story_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_story_refs_target ON story_refs(ref_type, ref_id)")

    # ── Triggers ───────────────────────────────────────────────────────────
    for table in ("companies", "roles"):
        cur.execute(f"""
        CREATE TRIGGER IF NOT EXISTS {table}_updated
        AFTER UPDATE ON {table}
        BEGIN
            UPDATE {table} SET updated_at = datetime('now') WHERE id = NEW.id;
        END""")

    # ── Views ──────────────────────────────────────────────────────────────
    cur.execute("DROP VIEW IF EXISTS pipeline_summary")
    cur.execute("""
    CREATE VIEW pipeline_summary AS
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
    ORDER BY r.overall_fit DESC, r.updated_at DESC
    """)

    cur.execute("DROP VIEW IF EXISTS needs_action")
    cur.execute("""
    CREATE VIEW needs_action AS
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
    ORDER BY r.next_action_due ASC, days_stale DESC
    """)

    cur.execute("DROP VIEW IF EXISTS application_log")
    cur.execute("""
    CREATE VIEW application_log AS
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
    ORDER BY a.submitted_at DESC
    """)

    con.commit()
    con.close()
    print(f"✓ Database initialized: {DB_PATH}")
    print("  Tables: companies, roles, contacts, applications, activity, search_runs, analysis_snapshots, stories, story_refs")
    print("  Views:  pipeline_summary, needs_action, application_log")

if __name__ == "__main__":
    init()
