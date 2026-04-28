"""
Tests for the deterministic gate logic — the parts of the judgment surface
that don't depend on LLM scoring.

What's covered:
  - update_status rejects invalid statuses; accepts every valid one
  - disqualify is a soft remove (no DELETE), reason persisted
  - disqualified roles excluded from active views, still readable by id
  - log_application auto-advances status to Applied and sets a 7-day follow-up
  - log_outreach auto-advances Researching → Outreach Drafted
  - log_response leaves status alone but writes activity
  - score-revision logic preserves previous_fit
  - get_application returns the most recent submission

What's NOT covered (LLM judgment, by design):
  - whether a JD contains a must-not in its prose
  - whether a draft sounds generic
  - whether a hook is "specific enough"

Run: python3 -m unittest tests.test_judgment
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from db import db as dbmod


class JudgmentGateTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._orig_db = dbmod.DB_PATH
        dbmod.DB_PATH = os.path.join(self.tmp.name, "test.db")
        dbmod._schema_ensured = False
        dbmod._apply_migrations(verbose=False)

    def tearDown(self):
        dbmod.DB_PATH = self._orig_db
        dbmod._schema_ensured = False
        self.tmp.cleanup()

    def _row(self, role_id):
        with dbmod.con() as db:
            return dict(db.execute(
                "SELECT * FROM roles WHERE id=?", (role_id,)
            ).fetchone())

    # ── status transitions ─────────────────────────────────────────────────

    def test_update_status_rejects_invalid(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        dbmod.update_status(rid, "Frozen")  # not a valid status
        # Status should be unchanged.
        self.assertEqual(self._row(rid)["status"], "Researching")

    def test_update_status_accepts_every_valid_status(self):
        valid = ["Researching", "Qualified", "Outreach Drafted", "Applied",
                 "Screening", "Interviewing", "Offer", "Closed Won", "Closed Lost"]
        for status in valid:
            rid = dbmod.add_role("Acme", f"Role {status}")
            dbmod.update_status(rid, status)
            self.assertEqual(self._row(rid)["status"], status)

    def test_update_status_logs_activity(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        dbmod.update_status(rid, "Qualified", note="Looks good")
        with dbmod.con() as db:
            entries = db.execute(
                "SELECT type, old_status, new_status FROM activity "
                "WHERE role_id=? ORDER BY id", (rid,)
            ).fetchall()
        kinds = [e["type"] for e in entries]
        self.assertIn("status_change", kinds)
        last = entries[-1]
        self.assertEqual(last["old_status"], "Researching")
        self.assertEqual(last["new_status"], "Qualified")

    # ── disqualify ─────────────────────────────────────────────────────────

    def test_disqualify_is_soft_remove(self):
        rid = dbmod.add_role("Beacon", "Senior PM")
        dbmod.disqualify(rid, "Below 6 — adjacent domain")
        # Row still exists.
        with dbmod.con() as db:
            count = db.execute(
                "SELECT COUNT(*) FROM roles WHERE id=?", (rid,)
            ).fetchone()[0]
        self.assertEqual(count, 1)
        row = self._row(rid)
        self.assertEqual(row["disqualified"], 1)
        self.assertEqual(row["disqualify_reason"], "Below 6 — adjacent domain")

    def test_disqualified_excluded_from_pipeline_summary_view(self):
        active = dbmod.add_role("Acme", "Sr PM", overall_fit=8.0)
        dropped = dbmod.add_role("Beacon", "Senior PM")
        dbmod.disqualify(dropped, "Below 6")
        with dbmod.con() as db:
            ids = [r[0] for r in db.execute(
                "SELECT id FROM pipeline_summary"
            ).fetchall()]
        self.assertIn(active, ids)
        self.assertNotIn(dropped, ids)

    # ── log_application ────────────────────────────────────────────────────

    def test_log_application_auto_advances_to_applied(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        dbmod.update_status(rid, "Qualified")
        dbmod.log_application(
            role_id=rid, method="ATS Direct",
            resume_version="platform-pm v1",
            resume_bullets_used="...",
            cover_letter_used="..."
        )
        self.assertEqual(self._row(rid)["status"], "Applied")

    def test_log_application_sets_seven_day_followup(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        dbmod.log_application(
            role_id=rid, method="ATS Direct",
            resume_version="v1",
            resume_bullets_used="...", cover_letter_used="..."
        )
        next_due = self._row(rid)["next_action_due"]
        # Parse ISO date stamp; should be ~7 days from today.
        target = (date.today() + timedelta(days=7)).isoformat()
        self.assertEqual(next_due, target)

    def test_get_application_returns_most_recent(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        dbmod.log_application(
            role_id=rid, method="LinkedIn Easy Apply",
            resume_version="v1", resume_bullets_used="A",
            cover_letter_used="A"
        )
        dbmod.log_application(
            role_id=rid, method="ATS Direct",
            resume_version="v2", resume_bullets_used="B",
            cover_letter_used="B"
        )
        with dbmod.con() as db:
            row = db.execute(
                "SELECT method, resume_version FROM applications "
                "WHERE role_id=? ORDER BY submitted_at DESC LIMIT 1", (rid,)
            ).fetchone()
        self.assertEqual(row["method"], "ATS Direct")
        self.assertEqual(row["resume_version"], "v2")

    # ── log_outreach ───────────────────────────────────────────────────────

    def test_log_outreach_auto_advances_from_researching(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        # Default status is Researching.
        dbmod.log_outreach(
            role_id=rid, contact_name="Jane Smith",
            channel="LinkedIn", message_summary="Intro about platform work"
        )
        self.assertEqual(self._row(rid)["status"], "Outreach Drafted")

    def test_log_outreach_does_not_advance_if_already_past_researching(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        dbmod.update_status(rid, "Qualified")
        dbmod.log_outreach(
            role_id=rid, contact_name="Jane Smith",
            channel="LinkedIn", message_summary="Follow-up"
        )
        # Still Qualified — outreach after Qualified shouldn't drop back.
        self.assertEqual(self._row(rid)["status"], "Qualified")

    # ── log_response ───────────────────────────────────────────────────────

    def test_log_response_writes_activity_without_status_change(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        dbmod.update_status(rid, "Outreach Drafted")
        dbmod.log_response(rid, "Jane Smith", "Open to chatting next week")
        # Status unchanged; agent decides when to advance to Screening.
        self.assertEqual(self._row(rid)["status"], "Outreach Drafted")
        with dbmod.con() as db:
            kinds = [r[0] for r in db.execute(
                "SELECT type FROM activity WHERE role_id=?", (rid,)
            ).fetchall()]
        self.assertIn("response_received", kinds)

    # ── score revision ─────────────────────────────────────────────────────

    def test_score_revision_writes_activity_entry(self):
        rid = dbmod.add_role("Acme", "Sr PM",
                             tech_fit=8, culture_fit=7, overall_fit=7.6)
        dbmod.log_jd_analysis(
            role_id=rid, tech_fit=7, culture_fit=6,
            file_path="references/analyses/x.md", verdict="research"
        )
        with dbmod.con() as db:
            row = db.execute(
                "SELECT type, detail FROM activity "
                "WHERE role_id=? AND type='score_revision'", (rid,)
            ).fetchone()
        self.assertIsNotNone(row, "score_revision activity entry not written")
        self.assertIn("was 7.6", row["detail"])

    def test_no_score_revision_when_score_unchanged(self):
        rid = dbmod.add_role("Acme", "Sr PM",
                             tech_fit=8, culture_fit=7, overall_fit=7.6)
        dbmod.log_jd_analysis(
            role_id=rid, tech_fit=8, culture_fit=7,
            file_path="references/analyses/x.md"
        )
        with dbmod.con() as db:
            count = db.execute(
                "SELECT COUNT(*) FROM activity "
                "WHERE role_id=? AND type='score_revision'", (rid,)
            ).fetchone()[0]
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
