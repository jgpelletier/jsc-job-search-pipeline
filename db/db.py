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
    auto_advance = False
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
        auto_advance = (r["status"] == "Researching")

    # update_status opens its own connection, so must run after the block above commits.
    if auto_advance:
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


# ── SESSION NOTES ──────────────────────────────────────────────────────────
# session_notes hold per-session state that isn't naturally derivable from
# other tables: open decisions waiting on the candidate, end-of-session
# completion summaries, free-form notes. The render functions read these
# when generating HANDOFF.md.

_SESSION_NOTE_KINDS = {"decision", "completion", "note"}


def add_session_note(kind, body, role_id=None):
    """Append a session note. kind ∈ {'decision', 'completion', 'note'}.

    Use 'decision' for items that need the candidate's input (resolve later
    with resolve_session_note). Use 'completion' for end-of-session summaries.
    Use 'note' for everything else.
    """
    if kind not in _SESSION_NOTE_KINDS:
        print(f"⚠ Invalid note kind {kind!r}. Choose from: {sorted(_SESSION_NOTE_KINDS)}")
        return
    with con() as db:
        cur = db.execute(
            "INSERT INTO session_notes (kind, role_id, body) VALUES (?,?,?)",
            (kind, role_id, body)
        )
        note_id = cur.lastrowid
    print(f"✓ Session note added: [{kind}] id={note_id}")
    return note_id


def resolve_session_note(note_id, resolution=None):
    """Mark a decision-kind note as resolved with an optional short note."""
    with con() as db:
        existing = db.execute(
            "SELECT kind, resolved_at FROM session_notes WHERE id=?", (note_id,)
        ).fetchone()
        if not existing:
            print(f"Session note {note_id} not found.")
            return
        if existing["resolved_at"]:
            print(f"Session note {note_id} already resolved at {existing['resolved_at']}.")
            return
        db.execute(
            "UPDATE session_notes SET resolved_at=datetime('now'), resolution=? WHERE id=?",
            (resolution, note_id)
        )
    print(f"✓ Session note {note_id} resolved.")


def list_open_decisions(role_id=None):
    """Return open decisions, optionally filtered by role."""
    with con() as db:
        if role_id is not None:
            rows = db.execute(
                "SELECT * FROM session_notes "
                "WHERE kind='decision' AND resolved_at IS NULL AND role_id=? "
                "ORDER BY created_at DESC",
                (role_id,)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM session_notes "
                "WHERE kind='decision' AND resolved_at IS NULL "
                "ORDER BY created_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def list_recent_completions(limit=3):
    """Return the most recent completion-kind notes, newest first."""
    with con() as db:
        rows = db.execute(
            "SELECT * FROM session_notes WHERE kind='completion' "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── RENDER OPERATIONS ──────────────────────────────────────────────────────
# pipeline.md and HANDOFF.md are render outputs of pipeline.db. They carry a
# do-not-hand-edit header. Regenerate with `python3 db/db.py render` or call
# render_all() from Python.

PIPELINE_MD_PATH = "pipeline.md"
HANDOFF_MD_PATH = "HANDOFF.md"
_AUTOGEN_NOTE = (
    "<!-- AUTOGENERATED from pipeline.db at {ts} — do not hand-edit.\n"
    "     Regenerate: python3 db/db.py render\n"
    "     Add session notes: python3 db/db.py note <decision|completion|note> <body>\n"
    "     (or db.add_session_note(kind, body, role_id=None) from Python). -->"
)


def _now_iso():
    return datetime.now().replace(microsecond=0).isoformat()


def _md_table(headers, rows, empty_text="(empty)"):
    """Render a Markdown table. rows is a list of tuples matching headers."""
    if not rows:
        return f"_{empty_text}_\n"
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        cells = []
        for cell in row:
            if cell is None:
                cells.append("")
            else:
                # Pipe characters break Markdown tables; escape them.
                cells.append(str(cell).replace("|", "\\|").replace("\n", " "))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def _strip_render_timestamps(text):
    """Return `text` with the autogen header line and 'Last rendered' line removed.

    Used to compare two renders for content equivalence — every render bakes
    a fresh ISO timestamp into both lines, but that's not a meaningful diff.
    Mirrors the strip used by tests/test_render.py.
    """
    out = []
    for line in text.splitlines():
        if "AUTOGENERATED from" in line or "Last rendered" in line:
            continue
        out.append(line)
    return "\n".join(out)


def _write_render_if_changed(path, new_text):
    """Write `new_text` to `path`, but skip the write if only timestamps differ.

    Returns True if a write happened, False if the existing file was already
    content-equivalent. Skipping the write keeps file mtime stable across
    no-op re-renders, which avoids spurious "uncommitted changes" diffs on
    every session start.
    """
    if os.path.isfile(path):
        with open(path) as f:
            existing = f.read()
        if _strip_render_timestamps(existing) == _strip_render_timestamps(new_text):
            return False
    with open(path, "w") as f:
        f.write(new_text)
    return True


def render_pipeline_md(path=None):
    """Regenerate pipeline.md from the DB."""
    path = path or PIPELINE_MD_PATH
    ts = _now_iso()
    with con() as db:
        active = db.execute("""
            SELECT r.id, c.name AS company, r.title, r.status,
                   r.overall_fit, r.next_action, r.next_action_due, r.remote
            FROM roles r JOIN companies c ON c.id=r.company_id
            WHERE r.disqualified = 0
            ORDER BY (r.overall_fit IS NULL), r.overall_fit DESC, r.updated_at DESC
        """).fetchall()
        screened = db.execute("""
            SELECT r.id, c.name AS company, r.title,
                   r.overall_fit, r.disqualify_reason, r.updated_at
            FROM roles r JOIN companies c ON c.id=r.company_id
            WHERE r.disqualified = 1
            ORDER BY r.updated_at DESC
        """).fetchall()
        searches = db.execute("""
            SELECT run_at, queries_run, roles_found, roles_added,
                   roles_duped, roles_screened
            FROM search_runs ORDER BY run_at DESC LIMIT 10
        """).fetchall()
        funnel = db.execute("""
            SELECT status, COUNT(*) AS n
            FROM roles WHERE disqualified=0
            GROUP BY status ORDER BY n DESC
        """).fetchall()
        avg_fit = db.execute(
            "SELECT AVG(overall_fit) FROM roles "
            "WHERE overall_fit IS NOT NULL AND disqualified=0"
        ).fetchone()[0]
        stale_count = db.execute("SELECT COUNT(*) FROM needs_action").fetchone()[0]

    parts = [
        _AUTOGEN_NOTE.format(ts=ts),
        "",
        "# Job Search Pipeline",
        "",
        f"_Last rendered: {ts}_",
        "",
        "## Active Pipeline",
        "",
        _md_table(
            ["ID", "Company", "Role", "Status", "Fit", "Next Action", "Due", "Remote"],
            [(r["id"], r["company"], r["title"], r["status"],
              f"{r['overall_fit']:.1f}" if r["overall_fit"] is not None else "",
              r["next_action"], r["next_action_due"], r["remote"])
             for r in active],
            empty_text="No active roles."
        ),
        "Statuses: `Researching` → `Qualified` → `Outreach Drafted` → `Applied` → `Screening` → `Interviewing` → `Offer` → `Closed Won` / `Closed Lost`",
        "",
        "## Screened / Closed",
        "",
        _md_table(
            ["ID", "Company", "Role", "Fit", "Reason", "Date"],
            [(r["id"], r["company"], r["title"],
              f"{r['overall_fit']:.1f}" if r["overall_fit"] is not None else "",
              r["disqualify_reason"], (r["updated_at"] or "")[:10])
             for r in screened],
            empty_text="No screened or closed roles."
        ),
        "",
        "## Search Log",
        "",
        _md_table(
            ["Date", "Queries", "Found", "Added", "Duped", "Screened"],
            [((r["run_at"] or "")[:10], r["queries_run"], r["roles_found"],
              r["roles_added"], r["roles_duped"], r["roles_screened"])
             for r in searches],
            empty_text="No search runs yet."
        ),
        "",
        "## Funnel",
        "",
        _md_table(
            ["Status", "Count"],
            [(r["status"], r["n"]) for r in funnel],
            empty_text="Funnel empty."
        ),
        "",
        f"- Average fit (active): {avg_fit:.1f}/10" if avg_fit else "- Average fit: —",
        f"- Roles needing action: {stale_count}",
        "",
    ]
    _write_render_if_changed(path, "\n".join(parts))
    return path


def render_handoff_md(path=None):
    """Regenerate HANDOFF.md from the DB."""
    path = path or HANDOFF_MD_PATH
    ts = _now_iso()
    with con() as db:
        roles_by_status = db.execute("""
            SELECT r.id, c.name AS company, r.title, r.status,
                   r.overall_fit, r.next_action, r.next_action_due
            FROM roles r JOIN companies c ON c.id=r.company_id
            WHERE r.disqualified = 0
            ORDER BY r.status, (r.overall_fit IS NULL), r.overall_fit DESC
        """).fetchall()
        decisions = db.execute("""
            SELECT sn.id, sn.body, sn.role_id, sn.created_at,
                   c.name AS company, r.title
            FROM session_notes sn
            LEFT JOIN roles r     ON r.id=sn.role_id
            LEFT JOIN companies c ON c.id=r.company_id
            WHERE sn.kind='decision' AND sn.resolved_at IS NULL
            ORDER BY sn.created_at DESC
        """).fetchall()
        completions = db.execute("""
            SELECT body, created_at FROM session_notes
            WHERE kind='completion'
            ORDER BY created_at DESC LIMIT 5
        """).fetchall()
        analyses = db.execute("""
            SELECT a.role_id, c.name AS company, a.skill_type,
                   a.file_path, a.overall_fit, a.verdict, a.generated_at
            FROM analysis_snapshots a
            JOIN roles r     ON r.id=a.role_id
            JOIN companies c ON c.id=r.company_id
            WHERE r.disqualified = 0
            ORDER BY a.role_id, a.generated_at DESC
        """).fetchall()

    # Group roles by status in pipeline order.
    status_order = ["Researching", "Qualified", "Outreach Drafted", "Applied",
                    "Screening", "Interviewing", "Offer", "Closed Won", "Closed Lost"]
    by_status = {s: [] for s in status_order}
    for row in roles_by_status:
        by_status.setdefault(row["status"], []).append(row)

    parts = [
        _AUTOGEN_NOTE.format(ts=ts),
        "",
        "# Session Handoff",
        "",
        f"_Last rendered: {ts}_",
        "",
        "## Pipeline by Status",
        "",
    ]
    any_active = False
    for status in status_order:
        rows = by_status.get(status) or []
        if not rows:
            continue
        any_active = True
        parts.append(f"### {status} ({len(rows)})")
        parts.append("")
        for r in rows:
            fit = f"fit {r['overall_fit']:.1f}" if r["overall_fit"] is not None else "no fit"
            due = f" by {r['next_action_due']}" if r["next_action_due"] else ""
            action = r["next_action"] or "—"
            parts.append(f"- **id={r['id']}** {r['company']} — {r['title']} ({fit}). Next: {action}{due}.")
        parts.append("")
    if not any_active:
        parts.append("_No active roles in pipeline._")
        parts.append("")

    parts.extend([
        "## Open Decisions",
        "",
    ])
    if decisions:
        for d in decisions:
            tag = f"role id={d['role_id']} ({d['company']})" if d["role_id"] else "general"
            parts.append(f"- **note id={d['id']}** [{tag}] {d['body']} _(opened {d['created_at'][:10]})_")
        parts.append("")
        parts.append("_Resolve with: `db.resolve_session_note(note_id, resolution=\"...\")`._")
    else:
        parts.append("_None._")
    parts.append("")

    parts.extend([
        "## Recent Session Summaries",
        "",
    ])
    if completions:
        for c in completions:
            parts.append(f"### {c['created_at'][:10]}")
            parts.append("")
            parts.append(c["body"])
            parts.append("")
    else:
        parts.append("_No session summaries yet. Add via `db.add_session_note(\"completion\", \"...\")`._")
        parts.append("")

    parts.extend([
        "## Analyses Index",
        "",
    ])
    if analyses:
        current_role = None
        for a in analyses:
            if a["role_id"] != current_role:
                current_role = a["role_id"]
                parts.append(f"### role id={current_role} — {a['company']}")
                parts.append("")
            verdict = f", verdict={a['verdict']}" if a["verdict"] else ""
            fit = f", fit={a['overall_fit']:.1f}" if a["overall_fit"] is not None else ""
            parts.append(
                f"- {a['generated_at'][:10]} `{a['skill_type']}` → "
                f"`{a['file_path']}`{fit}{verdict}"
            )
        parts.append("")
    else:
        parts.append("_No analyses generated yet._")
        parts.append("")

    _write_render_if_changed(path, "\n".join(parts))
    return path


def render_all():
    """Regenerate both pipeline.md and HANDOFF.md from the DB."""
    p1 = render_pipeline_md()
    p2 = render_handoff_md()
    print(f"✓ Rendered: {p1}, {p2}")


# ── SKILL HELPERS ──────────────────────────────────────────────────────────
# Skills should not embed SQL or column names. Each skill that writes to the
# DB calls one of these named functions. Schema knowledge stays in db.py.

# Canonical fit formula. Skills should not recompute it inline.
_FIT_TECH_WEIGHT = 0.6
_FIT_CULTURE_WEIGHT = 0.4


def _compute_overall_fit(tech_fit, culture_fit):
    """Return rounded overall fit. Either input may be None — returns None then."""
    if tech_fit is None or culture_fit is None:
        return None
    return round(_FIT_TECH_WEIGHT * tech_fit + _FIT_CULTURE_WEIGHT * culture_fit, 1)


def get_role_state_for_skill(role_id):
    """Return pre-flight state a skill needs to gate-check before running.

    Returns a dict with keys:
        company        — company name
        title          — role title
        status         — current pipeline status
        overall_fit    — current fit score (may be None)
        tech_fit       — current tech component
        culture_fit    — current culture component
        next_action    — current next-action text
        disqualified   — bool
        flagged        — bool: True if next_action mentions "recommend close" or "caution"
        open_decisions — list of open session_notes (kind='decision') for this role

    Returns None if the role does not exist.
    """
    with con() as db:
        r = db.execute(
            "SELECT r.id, r.title, r.status, r.overall_fit, r.tech_fit, "
            "       r.culture_fit, r.next_action, r.disqualified, c.name AS company "
            "FROM roles r JOIN companies c ON c.id=r.company_id "
            "WHERE r.id=?",
            (role_id,)
        ).fetchone()
        if not r:
            return None
        decisions = db.execute(
            "SELECT id, body, created_at FROM session_notes "
            "WHERE kind='decision' AND resolved_at IS NULL AND role_id=? "
            "ORDER BY created_at DESC",
            (role_id,)
        ).fetchall()

    next_action = (r["next_action"] or "").lower()
    flagged = ("recommend close" in next_action) or ("caution" in next_action)
    return {
        "company":        r["company"],
        "title":          r["title"],
        "status":         r["status"],
        "overall_fit":    r["overall_fit"],
        "tech_fit":       r["tech_fit"],
        "culture_fit":    r["culture_fit"],
        "next_action":    r["next_action"],
        "disqualified":   bool(r["disqualified"]),
        "flagged":        flagged,
        "open_decisions": [dict(d) for d in decisions],
    }


def log_jd_analysis(role_id, tech_fit, culture_fit, file_path,
                    verdict=None, fit_notes=None, tool="claude-code"):
    """Persist analyze-jd output: update fit components, save previous_fit, log analysis.

    Returns (old_overall, new_overall, snapshot_id). Skills should print the
    delta when old != new — never silently overwrite.

    The overall fit is computed via the canonical formula
    (0.6 * tech_fit + 0.4 * culture_fit). Callers cannot override it.
    """
    new_overall = _compute_overall_fit(tech_fit, culture_fit)
    with con() as db:
        existing = db.execute(
            "SELECT overall_fit FROM roles WHERE id=?", (role_id,)
        ).fetchone()
        if not existing:
            print(f"Role {role_id} not found.")
            return None
        old_overall = existing["overall_fit"]
        if old_overall != new_overall:
            db.execute(
                "UPDATE roles SET previous_fit=?, tech_fit=?, culture_fit=?, "
                "overall_fit=?, fit_notes=COALESCE(?, fit_notes) WHERE id=?",
                (old_overall, tech_fit, culture_fit, new_overall, fit_notes, role_id)
            )
            _log(db, company_id=db.execute(
                "SELECT company_id FROM roles WHERE id=?", (role_id,)
            ).fetchone()[0], role_id=role_id,
                type="score_revision",
                detail=f"was {old_overall}, now {new_overall} — analyze-jd")
        else:
            # Score unchanged but components or notes may have shifted.
            db.execute(
                "UPDATE roles SET tech_fit=?, culture_fit=?, "
                "fit_notes=COALESCE(?, fit_notes) WHERE id=?",
                (tech_fit, culture_fit, fit_notes, role_id)
            )

    snapshot_id = log_analysis(
        role_id=role_id, skill_type="analyze-jd", file_path=file_path,
        overall_fit=new_overall, verdict=verdict, tool=tool
    )
    return (old_overall, new_overall, snapshot_id)


def log_culture_revision(role_id, culture_fit, file_path,
                         verdict=None, fit_notes=None, tool="claude-code"):
    """Persist score-fit output: revise culture_fit, recompute overall_fit, log analysis.

    Reuses the existing tech_fit. Returns (old_overall, new_overall, snapshot_id).
    """
    with con() as db:
        existing = db.execute(
            "SELECT overall_fit, tech_fit FROM roles WHERE id=?", (role_id,)
        ).fetchone()
        if not existing:
            print(f"Role {role_id} not found.")
            return None
        old_overall = existing["overall_fit"]
        tech_fit = existing["tech_fit"]
        new_overall = _compute_overall_fit(tech_fit, culture_fit)

        if old_overall != new_overall:
            db.execute(
                "UPDATE roles SET previous_fit=?, culture_fit=?, overall_fit=?, "
                "fit_notes=COALESCE(?, fit_notes) WHERE id=?",
                (old_overall, culture_fit, new_overall, fit_notes, role_id)
            )
            _log(db, company_id=db.execute(
                "SELECT company_id FROM roles WHERE id=?", (role_id,)
            ).fetchone()[0], role_id=role_id,
                type="score_revision",
                detail=f"was {old_overall}, now {new_overall} — score-fit")
        else:
            db.execute(
                "UPDATE roles SET culture_fit=?, "
                "fit_notes=COALESCE(?, fit_notes) WHERE id=?",
                (culture_fit, fit_notes, role_id)
            )

    snapshot_id = log_analysis(
        role_id=role_id, skill_type="score-fit", file_path=file_path,
        overall_fit=new_overall, verdict=verdict, tool=tool
    )
    return (old_overall, new_overall, snapshot_id)


def log_company_research(role_id, file_path, verdict="research", tool="claude-code"):
    """Persist company-research output. Thin wrapper over log_analysis.

    Skills call this so the skill files do not name the analysis_snapshots
    table or the skill_type string directly.
    """
    return log_analysis(
        role_id=role_id, skill_type="company-research", file_path=file_path,
        overall_fit=None, verdict=verdict, tool=tool
    )


def log_find_contacts_run(role_id, file_path, tool="claude-code"):
    """Persist find-contacts output. Thin wrapper over log_analysis."""
    return log_analysis(
        role_id=role_id, skill_type="find-contacts", file_path=file_path,
        overall_fit=None, verdict=None, tool=tool
    )


# ── REFERENCES LOADING ─────────────────────────────────────────────────────
# references/*.md hold the candidate's structured facts (must-haves,
# must-nots, voice anchors). Each file MAY carry a YAML frontmatter block
# bracketed by '---' lines for programmatic access. The narrative body is
# always preserved for the LLM to read.
#
# load_references() returns a dict like:
#   {
#       "mnookin": {"frontmatter": {...}, "body": "..."},
#       "cmf":     {"frontmatter": {...}, "body": "..."},
#       "resume":  {"frontmatter": {...}, "body": "..."},
#   }
#
# We use a stdlib-only mini-parser instead of PyYAML so this template
# works on minimal Python installs.

REFERENCES_DIR = "references"
_REFERENCES_FILES = ("mnookin", "cmf", "resume")


def _strip_quotes(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def parse_frontmatter(text):
    """Parse YAML frontmatter at the top of a markdown string.

    Supports the small subset references/*.md actually use:
      - 'key: value'                    → str
      - 'key:' then indented '- item'   → list[str]
      - 'key:' then indented 'k: v'     → dict[str, str]

    Returns (frontmatter_dict, body_str). If no frontmatter is present,
    returns ({}, original_text).
    """
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return {}, text
    # Locate the closing fence.
    nl = "\r\n" if text.startswith("---\r\n") else "\n"
    fence = f"{nl}---{nl}"
    end = text.find(fence, len("---") + len(nl))
    if end == -1:
        return {}, text
    fm_text = text[len("---") + len(nl):end]
    body = text[end + len(fence):]

    data = {}
    current_key = None
    current_kind = None  # None | 'list' | 'dict'
    for raw in fm_text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[0] in (" ", "\t"):
            stripped = raw.strip()
            if current_key is None:
                continue
            if stripped.startswith("- "):
                if current_kind is None:
                    current_kind = "list"
                    data[current_key] = []
                if not isinstance(data[current_key], list):
                    continue
                data[current_key].append(_strip_quotes(stripped[2:]))
            elif ":" in stripped:
                if current_kind is None:
                    current_kind = "dict"
                    data[current_key] = {}
                if not isinstance(data[current_key], dict):
                    continue
                k, _, v = stripped.partition(":")
                data[current_key][k.strip()] = _strip_quotes(v)
        else:
            key_part, _, val_part = raw.partition(":")
            key = key_part.strip()
            val = val_part.strip()
            if val:
                data[key] = _strip_quotes(val)
                current_key = None
                current_kind = None
            else:
                current_key = key
                current_kind = None
                data[key] = []  # default to empty list; promoted to dict if needed
    return data, body


def load_references(directory=None):
    """Read references/{mnookin,cmf,resume}.md and return parsed frontmatter + body.

    Returns a dict keyed by file basename (without .md). Each value is
    `{"frontmatter": dict, "body": str, "path": str}`. Files that don't
    exist are skipped silently.
    """
    directory = directory or REFERENCES_DIR
    out = {}
    for name in _REFERENCES_FILES:
        path = os.path.join(directory, f"{name}.md")
        if not os.path.isfile(path):
            continue
        with open(path) as f:
            text = f.read()
        fm, body = parse_frontmatter(text)
        out[name] = {"frontmatter": fm, "body": body, "path": path}
    return out


def get_must_haves():
    """Return the list of must-haves from references/mnookin.md frontmatter, or []."""
    refs = load_references()
    return refs.get("mnookin", {}).get("frontmatter", {}).get("must_haves", []) or []


def get_must_nots():
    """Return the list of must-nots from references/mnookin.md frontmatter, or []."""
    refs = load_references()
    return refs.get("mnookin", {}).get("frontmatter", {}).get("must_nots", []) or []


def get_voice_anchors():
    """Return the list of voice anchors from references/cmf.md frontmatter, or []."""
    refs = load_references()
    return refs.get("cmf", {}).get("frontmatter", {}).get("voice_anchors", []) or []


# ── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pipeline"
    if cmd == "pipeline":   backup(); show_pipeline()
    elif cmd == "action":   needs_action()
    elif cmd == "stats":    stats()
    elif cmd == "search":   search_roles(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "backup":   backup()
    elif cmd == "render":   render_all()
    elif cmd == "migrate":  _apply_migrations(verbose=True)
    elif cmd == "note":
        # python3 db/db.py note <kind> <body...>
        if len(sys.argv) < 4:
            print("Usage: python3 db/db.py note <decision|completion|note> <body>")
        else:
            add_session_note(sys.argv[2], " ".join(sys.argv[3:]))
    else:
        print(f"Unknown command: {cmd}")
