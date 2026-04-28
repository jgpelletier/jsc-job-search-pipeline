"""
Job Search Pipeline — Database operations
The agent runs these functions via Python to read/write pipeline.db
"""

import sqlite3
import json
import os
import re
import shutil
import glob
from datetime import datetime, date

DB_PATH = "pipeline.db"
MIGRATIONS_DIR = "migrations"
BACKUP_DIR = "backups"
BACKUP_RETAIN = 7  # days


# ── SCHEMA MIGRATIONS ──────────────────────────────────────────────────────
# pipeline.db is versioned via migrations/NNN-name.sql files. The first call
# to con() in a process applies any pending migrations. See migrations/README.md.

_schema_ensured = False
_MIGRATION_FILENAME_RE = re.compile(r"^(\d{3})-[\w\-]+\.sql$")


def _list_migrations(migrations_dir):
    """Return [(version_int, path)] sorted by version, for files matching NNN-name.sql."""
    if not os.path.isdir(migrations_dir):
        return []
    out = []
    for fname in sorted(os.listdir(migrations_dir)):
        m = _MIGRATION_FILENAME_RE.match(fname)
        if m:
            out.append((int(m.group(1)), os.path.join(migrations_dir, fname)))
    return out


def _current_schema_version(conn):
    """Return the highest applied version, or 0 if schema_version doesn't exist."""
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return (row[0] or 0) if row else 0
    except sqlite3.OperationalError:
        return 0


def _apply_one(conn, version, path, verbose=True):
    """Apply a single migration file and record it in schema_version.

    Tolerates 'duplicate column name' errors: a council member who
    hand-patched their v0.1.0 DB before migrations existed may already have
    columns that an ALTER TABLE would otherwise fail to add. We log it and
    record the version so the migration is not retried next run.
    """
    name = os.path.basename(path)
    with open(path) as f:
        sql = f.read()
    try:
        conn.executescript(sql)
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        if "duplicate column name" in msg:
            if verbose:
                print(f"  (migration {name}: column already exists — treating as applied)")
        else:
            raise
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (version, migration_name) VALUES (?, ?)",
        (version, name)
    )
    conn.commit()
    if verbose:
        print(f"✓ Applied migration {version}: {name}")


def _apply_migrations(db_path=None, migrations_dir=None, verbose=True):
    """Apply any migrations whose version is greater than the current schema version.

    Safe to call repeatedly; pending migrations are determined by reading
    schema_version from the target DB.
    """
    db_path = db_path or DB_PATH
    migrations_dir = migrations_dir or MIGRATIONS_DIR
    migrations = _list_migrations(migrations_dir)
    if not migrations:
        return
    conn = sqlite3.connect(db_path)
    try:
        current = _current_schema_version(conn)
        pending = [(v, p) for v, p in migrations if v > current]
        for version, path in pending:
            _apply_one(conn, version, path, verbose=verbose)
    finally:
        conn.close()


def _ensure_schema():
    """Apply pending migrations once per process. Called by con()."""
    global _schema_ensured
    if _schema_ensured:
        return
    _apply_migrations(verbose=False)
    _schema_ensured = True


def backup():
    """Create a timestamped backup of pipeline.db. One per day, keeps last 7."""
    if not os.path.exists(DB_PATH):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    today = date.today().isoformat()
    dest = os.path.join(BACKUP_DIR, f"pipeline-{today}.db")
    if not os.path.exists(dest):
        shutil.copy2(DB_PATH, dest)
        print(f"✓ Backup created: {dest}")
    # Prune backups older than BACKUP_RETAIN days
    all_backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "pipeline-*.db")))
    for old in all_backups[:-BACKUP_RETAIN]:
        os.remove(old)
        print(f"  Pruned old backup: {old}")

def con():
    _ensure_schema()
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


# ── READ OPERATIONS ────────────────────────────────────────────────────────

def show_pipeline(status=None):
    """Full pipeline summary, optionally filtered by status."""
    with con() as db:
        if status:
            rows = db.execute(
                "SELECT * FROM pipeline_summary WHERE status = ?", (status,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM pipeline_summary").fetchall()
    _print_table(rows)


def needs_action():
    """Roles that need attention — overdue or stale for 5+ days."""
    with con() as db:
        rows = db.execute("SELECT * FROM needs_action").fetchall()
    if not rows:
        print("✓ Nothing urgent right now.")
        return
    print(f"\n⚡ {len(rows)} role(s) need attention:\n")
    _print_table(rows)


def stats():
    """Pipeline health stats — funnel counts and velocity."""
    with con() as db:
        total = db.execute(
            "SELECT COUNT(*) FROM roles WHERE disqualified=0"
        ).fetchone()[0]
        by_status = db.execute("""
            SELECT status, COUNT(*) as n
            FROM roles WHERE disqualified=0
            GROUP BY status ORDER BY n DESC
        """).fetchall()
        avg_fit = db.execute(
            "SELECT AVG(overall_fit) FROM roles WHERE overall_fit IS NOT NULL AND disqualified=0"
        ).fetchone()[0]
        stale = db.execute(
            "SELECT COUNT(*) FROM needs_action"
        ).fetchone()[0]
        sourced_7d = db.execute("""
            SELECT COUNT(*) FROM roles
            WHERE created_at >= date('now', '-7 days') AND disqualified=0
        """).fetchone()[0]

    print(f"\n📊 Pipeline Stats")
    print(f"   Total active roles:  {total}")
    print(f"   Added last 7 days:   {sourced_7d}")
    print(f"   Avg fit score:       {avg_fit:.1f}/10" if avg_fit else "   Avg fit score:  —")
    print(f"   Needing action:      {stale}")
    print(f"\n   Funnel:")
    for row in by_status:
        print(f"   {row['status']:<22} {row['n']}")


def get_role(role_id):
    """Full detail on one role."""
    with con() as db:
        r = db.execute(
            "SELECT r.*, c.name as company FROM roles r JOIN companies c ON c.id=r.company_id WHERE r.id=?",
            (role_id,)
        ).fetchone()
        if not r:
            print(f"Role {role_id} not found.")
            return
        log = db.execute(
            "SELECT * FROM activity WHERE role_id=? ORDER BY logged_at DESC", (role_id,)
        ).fetchall()
    print(f"\n{'─'*60}")
    print(f"  {r['title']} at {r['company']}")
    print(f"  Status:     {r['status']}")
    print(f"  Fit:        {r['overall_fit']}/10  (tech {r['tech_fit']}, culture {r['culture_fit']})")
    print(f"  Remote:     {r['remote']}")
    print(f"  Comp:       {r['comp_min']}–{r['comp_max']}k" if r['comp_min'] else "  Comp:   not listed")
    print(f"  Next:       {r['next_action']} by {r['next_action_due']}")
    print(f"  URL:        {r['url']}")
    print(f"\n  Fit notes:\n  {r['fit_notes']}")
    if log:
        print(f"\n  Activity log:")
        for entry in log:
            print(f"  {entry['logged_at'][:10]}  [{entry['type']}]  {entry['detail']}")
    print(f"{'─'*60}")


def search_roles(query):
    """Full-text search across company name, role title, and notes."""
    with con() as db:
        rows = db.execute("""
            SELECT r.id, c.name as company, r.title, r.status, r.overall_fit, r.next_action
            FROM roles r JOIN companies c ON c.id=r.company_id
            WHERE r.disqualified=0
              AND (c.name LIKE ? OR r.title LIKE ? OR r.fit_notes LIKE ? OR r.jd_text LIKE ?)
        """, (f"%{query}%",)*4).fetchall()
    _print_table(rows)


# ── WRITE OPERATIONS ───────────────────────────────────────────────────────

# Schema note: fit is stored as overall_fit (not fit_score). Components: tech_fit, culture_fit.
# Formula: overall_fit = 0.6 * tech_fit + 0.4 * culture_fit
# previous_fit stores the prior score when a revision is made — never overwrite without saving it first.
def add_role(company_name, title, url=None, source="manual", source_file=None,
             tech_fit=None, culture_fit=None, overall_fit=None, remote=None,
             location=None, jd_text=None, fit_notes=None, next_action=None,
             next_action_due=None, comp_min=None, comp_max=None,
             company_domain=None, company_size=None, company_stage=None,
             company_remote=None):
    """Add a new role, creating the company if it doesn't exist."""
    with con() as db:
        # Upsert company
        existing = db.execute(
            "SELECT id FROM companies WHERE name=?", (company_name,)
        ).fetchone()
        if existing:
            company_id = existing["id"]
        else:
            cur = db.execute(
                "INSERT INTO companies (name, domain, size, stage, remote_friendly) VALUES (?,?,?,?,?)",
                (company_name, company_domain, company_size, company_stage, company_remote)
            )
            company_id = cur.lastrowid

        # Check for duplicate role at same company
        dupe = db.execute(
            "SELECT id FROM roles WHERE company_id=? AND title=? AND disqualified=0",
            (company_id, title)
        ).fetchone()
        if dupe:
            print(f"⚠ Already tracking '{title}' at {company_name} (id={dupe['id']})")
            return dupe["id"]

        cur = db.execute("""
            INSERT INTO roles
              (company_id, title, url, source, source_file, tech_fit, culture_fit,
               overall_fit, previous_fit, remote, location, jd_text, fit_notes,
               next_action, next_action_due, comp_min, comp_max)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (company_id, title, url, source, source_file, tech_fit, culture_fit,
              overall_fit, None, remote, location, jd_text, fit_notes, next_action,
              next_action_due, comp_min, comp_max))
        role_id = cur.lastrowid

        _log(db, company_id=company_id, role_id=role_id,
             type="status_change", new_status="Researching",
             detail=f"Role added via {source}")

    print(f"✓ Added: {title} at {company_name} (id={role_id})")
    return role_id


def update_status(role_id, new_status, note=None, next_action=None, next_action_due=None):
    """Move a role to a new status and log it."""
    valid = ["Researching","Qualified","Outreach Drafted","Applied",
             "Screening","Interviewing","Offer","Closed Won","Closed Lost"]
    if new_status not in valid:
        print(f"⚠ Invalid status. Choose from: {valid}")
        return
    with con() as db:
        r = db.execute("SELECT status, company_id FROM roles WHERE id=?", (role_id,)).fetchone()
        if not r:
            print(f"Role {role_id} not found.")
            return
        old_status = r["status"]
        db.execute("""
            UPDATE roles SET status=?, next_action=?, next_action_due=?
            WHERE id=?
        """, (new_status, next_action, next_action_due, role_id))
        _log(db, company_id=r["company_id"], role_id=role_id,
             type="status_change", old_status=old_status, new_status=new_status,
             detail=note or f"Status → {new_status}")
    print(f"✓ Role {role_id}: {old_status} → {new_status}")


def log_outreach(role_id, contact_name, contact_title=None, channel="LinkedIn",
                 message_summary=None):
    """Record that outreach was sent."""
    with con() as db:
        r = db.execute("SELECT company_id, status FROM roles WHERE id=?", (role_id,)).fetchone()
        if not r:
            print(f"Role {role_id} not found.")
            return
        contact_id = None
        if contact_name:
            existing = db.execute(
                "SELECT id FROM contacts WHERE company_id=? AND name=?",
                (r["company_id"], contact_name)
            ).fetchone()
            if existing:
                contact_id = existing["id"]
            else:
                cur = db.execute(
                    "INSERT INTO contacts (company_id, name, title) VALUES (?,?,?)",
                    (r["company_id"], contact_name, contact_title)
                )
                contact_id = cur.lastrowid

        _log(db, company_id=r["company_id"], role_id=role_id, contact_id=contact_id,
             type="outreach_sent",
             detail=f"{channel} → {contact_name}: {message_summary or '(no summary)'}")

        if r["status"] == "Researching":
            update_status(role_id, "Outreach Drafted",
                          note="Auto-advanced after outreach logged")
    print(f"✓ Outreach logged: {contact_name} via {channel}")


def log_response(role_id, contact_name, summary):
    """Record an inbound response from a contact."""
    with con() as db:
        r = db.execute("SELECT company_id FROM roles WHERE id=?", (role_id,)).fetchone()
        if not r:
            print(f"Role {role_id} not found.")
            return
        _log(db, company_id=r["company_id"], role_id=role_id,
             type="response_received", detail=f"{contact_name}: {summary}")
    print(f"✓ Response logged for role {role_id}")


def disqualify(role_id, reason):
    """Remove a role from active pipeline."""
    with con() as db:
        r = db.execute("SELECT company_id, status FROM roles WHERE id=?", (role_id,)).fetchone()
        if not r:
            print(f"Role {role_id} not found.")
            return
        db.execute(
            "UPDATE roles SET disqualified=1, disqualify_reason=? WHERE id=?",
            (reason, role_id)
        )
        _log(db, company_id=r["company_id"], role_id=role_id,
             type="status_change", old_status=r["status"], new_status="Closed Lost",
             detail=f"Disqualified: {reason}")
    print(f"✓ Role {role_id} disqualified: {reason}")


def log_search_run(queries_run, roles_found, roles_added, roles_duped, roles_screened, notes=None):
    """Record a job-search run for tracking search velocity."""
    with con() as db:
        db.execute("""
            INSERT INTO search_runs
              (queries_run, roles_found, roles_added, roles_duped, roles_screened, notes)
            VALUES (?,?,?,?,?,?)
        """, (queries_run, roles_found, roles_added, roles_duped, roles_screened, notes))
    print(f"✓ Search run logged: {roles_added} new roles added")


# ── HELPERS ────────────────────────────────────────────────────────────────

def _log(db, company_id, type, role_id=None, contact_id=None,
         old_status=None, new_status=None, detail=None):
    db.execute("""
        INSERT INTO activity (role_id, company_id, contact_id, type, old_status, new_status, detail)
        VALUES (?,?,?,?,?,?,?)
    """, (role_id, company_id, contact_id, type, old_status, new_status, detail))


def _print_table(rows):
    if not rows:
        print("  (no results)")
        return
    rows = [dict(r) for r in rows]
    keys = list(rows[0].keys())
    widths = {k: max(len(k), max(len(str(r.get(k) or "")) for r in rows)) for k in keys}
    widths = {k: min(v, 30) for k, v in widths.items()}  # cap at 30
    header = "  " + "  ".join(k.upper().ljust(widths[k]) for k in keys)
    print(f"\n{header}")
    print("  " + "  ".join("─" * widths[k] for k in keys))
    for r in rows:
        row = "  " + "  ".join(str(r.get(k) or "").ljust(widths[k])[:widths[k]] for k in keys)
        print(row)
    print(f"\n  {len(rows)} row(s)\n")


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pipeline"
    if cmd == "pipeline":   backup(); show_pipeline()
    elif cmd == "action":   needs_action()
    elif cmd == "stats":    stats()
    elif cmd == "search":   search_roles(sys.argv[2] if len(sys.argv)>2 else "")
    elif cmd == "backup":   backup()
    else: print(f"Unknown command: {cmd}")


# ── APPLICATION OPERATIONS ─────────────────────────────────────────────────

def log_application(role_id, method, resume_version, resume_bullets_used,
                    cover_letter_used, ats_url=None, ats_name=None,
                    confirmation_code=None, screening_questions=None, notes=None):
    """Record a submitted application with full snapshot of what was sent."""
    from datetime import datetime
    submitted_at = datetime.now().isoformat()
    with con() as db:
        r = db.execute(
            "SELECT company_id, status FROM roles WHERE id=?", (role_id,)
        ).fetchone()
        if not r:
            print(f"Role {role_id} not found.")
            return
        db.execute("""
            INSERT INTO applications
              (role_id, company_id, submitted_at, method, ats_url, ats_name,
               confirmation_code, resume_version, resume_bullets_used,
               cover_letter_used, screening_questions, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (role_id, r["company_id"], submitted_at, method, ats_url, ats_name,
              confirmation_code, resume_version, resume_bullets_used,
              cover_letter_used, screening_questions, notes))
        _log(db, company_id=r["company_id"], role_id=role_id,
             type="application_submitted",
             detail=f"Applied via {method} | Resume: {resume_version} | ATS: {ats_name or 'n/a'}")
    # Auto-advance status to Applied
    update_status(role_id, "Applied",
                  note=f"Application submitted via {method}",
                  next_action="Follow up if no response in 7 days",
                  next_action_due=str((datetime.now().date().__class__.fromordinal(
                      datetime.now().date().toordinal() + 7))))
    print(f"✓ Application logged for role {role_id} — {method}")


def show_applications():
    """Show all submitted applications."""
    with con() as db:
        rows = db.execute("SELECT * FROM application_log").fetchall()
    _print_table(rows)


def get_application(role_id):
    """Retrieve what was submitted for a specific role — for interview prep."""
    with con() as db:
        a = db.execute(
            "SELECT a.*, c.name as company, r.title FROM applications a "
            "JOIN roles r ON r.id=a.role_id JOIN companies c ON c.id=a.company_id "
            "WHERE a.role_id=? ORDER BY a.submitted_at DESC LIMIT 1",
            (role_id,)
        ).fetchone()
    if not a:
        print(f"No application found for role {role_id}.")
        return
    print(f"\n{'─'*60}")
    print(f"  Application: {a['title']} at {a['company']}")
    print(f"  Submitted:   {a['submitted_at'][:10]}")
    print(f"  Method:      {a['method']}")
    print(f"  ATS:         {a['ats_name'] or 'n/a'} — {a['ats_url'] or 'n/a'}")
    print(f"  Resume:      {a['resume_version']}")
    print(f"\n  Resume bullets submitted:\n{a['resume_bullets_used']}")
    print(f"\n  Cover letter submitted:\n{a['cover_letter_used']}")
    if a['screening_questions']:
        print(f"\n  Screening Q&A:\n{a['screening_questions']}")
    print(f"{'─'*60}")


# ── CONTACT SEARCH OPERATIONS ──────────────────────────────────────────────

def add_contact(company_id, name, title=None, relationship=None,
                linkedin_search_query=None, notes=None):
    """Add a contact record with LinkedIn search query for manual lookup."""
    with con() as db:
        existing = db.execute(
            "SELECT id FROM contacts WHERE company_id=? AND name=?",
            (company_id, name)
        ).fetchone()
        if existing:
            print(f"⚠ Contact '{name}' already exists for this company (id={existing['id']})")
            return existing["id"]
        cur = db.execute("""
            INSERT INTO contacts
              (company_id, name, title, relationship, linkedin_search_query, notes)
            VALUES (?,?,?,?,?,?)
        """, (company_id, name, title, relationship, linkedin_search_query, notes))
        contact_id = cur.lastrowid
    print(f"✓ Contact added: {name} at company {company_id} (id={contact_id})")
    return contact_id


def get_contacts(company_id):
    """List all contacts for a company with their LinkedIn search queries."""
    with con() as db:
        company = db.execute(
            "SELECT name FROM companies WHERE id=?", (company_id,)
        ).fetchone()
        rows = db.execute(
            "SELECT * FROM contacts WHERE company_id=? ORDER BY relationship",
            (company_id,)
        ).fetchall()
    if not rows:
        print(f"No contacts found for company {company_id}.")
        return
    print(f"\n  Contacts — {company['name'] if company else company_id}:")
    for r in rows:
        print(f"\n  [{r['relationship'] or 'contact'}] {r['name']} — {r['title'] or 'title unknown'}")
        if r['linkedin_search_query']:
            print(f"  LinkedIn search: {r['linkedin_search_query']}")
        if r['linkedin_url']:
            print(f"  LinkedIn URL:    {r['linkedin_url']}")
        if r['notes']:
            print(f"  Notes:           {r['notes']}")


def update_contact_linkedin(contact_id, linkedin_url):
    """Save LinkedIn URL after manual lookup."""
    with con() as db:
        db.execute(
            "UPDATE contacts SET linkedin_url=? WHERE id=?",
            (linkedin_url, contact_id)
        )
    print(f"✓ LinkedIn URL saved for contact {contact_id}")


# ── ANALYSIS PERSISTENCE OPERATIONS ──────────────────────────────────────────

def log_analysis(role_id, skill_type, file_path, overall_fit=None, verdict=None,
                 tool='claude-code', regenerated_from=None):
    """Log that an analysis file was generated for a role.

    Args:
        role_id: The role ID this analysis is for
        skill_type: 'company-research' | 'analyze-jd' | 'score-fit' | 'find-contacts'
        file_path: Relative path to the saved markdown file (e.g., 'references/analyses/001-acme-fit-2026-01-15.md')
        overall_fit: Optional fit score (1-10) for quick lookup
        verdict: Optional 'pursue' | 'pass' | 'research'
        tool: Which tool generated the analysis ('claude-code' or other agent identifier)
        regenerated_from: If this replaces an earlier analysis, link to that snapshot id
    """
    with con() as db:
        cur = db.execute("""
            INSERT INTO analysis_snapshots
              (role_id, tool, skill_type, file_path, overall_fit, verdict, regenerated_from)
            VALUES (?,?,?,?,?,?,?)
        """, (role_id, tool, skill_type, file_path, overall_fit, verdict, regenerated_from))
        snapshot_id = cur.lastrowid
    print(f"✓ Analysis logged: {skill_type} for role {role_id} → {file_path}")
    return snapshot_id


def get_analyses(role_id, skill_type=None):
    """Get all analyses for a role, optionally filtered by skill type.
    
    Returns list of analysis records with metadata.
    """
    with con() as db:
        if skill_type:
            rows = db.execute("""
                SELECT * FROM analysis_snapshots 
                WHERE role_id=? AND skill_type=?
                ORDER BY generated_at DESC
            """, (role_id, skill_type)).fetchall()
        else:
            rows = db.execute("""
                SELECT * FROM analysis_snapshots 
                WHERE role_id=?
                ORDER BY generated_at DESC
            """, (role_id,)).fetchall()
    
    if not rows:
        print(f"No analyses found for role {role_id}" + (f" of type '{skill_type}'" if skill_type else ""))
        return []
    
    print(f"\n  Analyses for role {role_id}:" + (f" (type: {skill_type})" if skill_type else ""))
    for r in rows:
        fit_str = f"fit={r['overall_fit']:.1f}" if r['overall_fit'] else "no fit score"
        verdict_str = f", verdict={r['verdict']}" if r['verdict'] else ""
        print(f"  [{r['generated_at'][:10]}] {r['skill_type']:<20} {fit_str}{verdict_str}")
        print(f"              → {r['file_path']}")
    return [dict(r) for r in rows]


def get_latest_analysis(role_id, skill_type):
    """Get the most recent analysis of a specific type for a role.
    
    Returns the file path and metadata, or None if not found.
    """
    with con() as db:
        row = db.execute("""
            SELECT * FROM analysis_snapshots 
            WHERE role_id=? AND skill_type=?
            ORDER BY generated_at DESC LIMIT 1
        """, (role_id, skill_type)).fetchone()
    
    if not row:
        return None
    return dict(row)


def update_contact_discovered(contact_id, linkedin_url, is_target=False):
    """Mark contact as discovered with timestamp and optional priority flag.
    
    Args:
        contact_id: The contact to update
        linkedin_url: The discovered LinkedIn URL
        is_target: Whether this is a priority outreach target (default False)
    """
    discovered_at = datetime.now().isoformat()
    with con() as db:
        db.execute("""
            UPDATE contacts 
            SET linkedin_url=?, discovered_at=?, is_target=?
            WHERE id=?
        """, (linkedin_url, discovered_at, 1 if is_target else 0, contact_id))
    print(f"✓ Contact {contact_id} updated: LinkedIn discovered, target={is_target}")


def update_contact_outreach(contact_id, sent_at=None, response_received=False):
    """Track outreach status for a contact.
    
    Args:
        contact_id: The contact to update
        sent_at: When outreach was sent (default: now)
        response_received: Whether a response was received
    """
    if sent_at is None:
        sent_at = datetime.now().isoformat()
    with con() as db:
        db.execute("""
            UPDATE contacts 
            SET outreach_sent_at=?, response_received=?
            WHERE id=?
        """, (sent_at, 1 if response_received else 0, contact_id))
    status = "response received" if response_received else "outreach sent"
    print(f"✓ Contact {contact_id} updated: {status}")


def get_target_contacts(company_id=None):
    """Get all priority target contacts, optionally filtered by company.
    
    Returns contacts marked as is_target=1 with their current status.
    """
    with con() as db:
        if company_id:
            rows = db.execute("""
                SELECT c.*, co.name as company_name
                FROM contacts c
                JOIN companies co ON co.id=c.company_id
                WHERE c.company_id=? AND c.is_target=1
                ORDER BY c.discovered_at DESC
            """, (company_id,)).fetchall()
        else:
            rows = db.execute("""
                SELECT c.*, co.name as company_name
                FROM contacts c
                JOIN companies co ON co.id=c.company_id
                WHERE c.is_target=1
                ORDER BY c.discovered_at DESC
            """).fetchall()
    
    if not rows:
        print("No target contacts found" + (f" for company {company_id}" if company_id else ""))
        return []
    
    print(f"\n  Target contacts:" + (f" (company {company_id})" if company_id else ""))
    for r in rows:
        status = []
        if r['outreach_sent_at']:
            status.append("sent" + ("+response" if r['response_received'] else ""))
        else:
            status.append("pending")
        if r['discovered_at']:
            status.append(f"found {r['discovered_at'][:10]}")
        
        print(f"  [{r['company_name']}] {r['name']} — {r['title'] or 'unknown title'}")
        print(f"              Status: {', '.join(status)}")
        if r['linkedin_url']:
            print(f"              LinkedIn: {r['linkedin_url']}")
    return [dict(r) for r in rows]
