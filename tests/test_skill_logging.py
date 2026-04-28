"""
Tests for the skill-helper functions in db/db.py:
  - get_role_state_for_skill
  - log_jd_analysis
  - log_culture_revision
  - log_company_research
  - log_find_contacts_run

Run: python3 -m unittest tests.test_skill_logging
"""

import os
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from db import db as dbmod


class SkillLoggingTests(unittest.TestCase):

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

    # ── get_role_state_for_skill ───────────────────────────────────────────

    def test_role_state_returns_none_for_missing(self):
        self.assertIsNone(dbmod.get_role_state_for_skill(999))

    def test_role_state_unflagged_role(self):
        rid = dbmod.add_role("Acme", "Sr PM", overall_fit=7.6,
                             next_action="Run company-research")
        s = dbmod.get_role_state_for_skill(rid)
        self.assertEqual(s["company"], "Acme")
        self.assertEqual(s["overall_fit"], 7.6)
        self.assertFalse(s["flagged"])
        self.assertFalse(s["disqualified"])
        self.assertEqual(s["open_decisions"], [])

    def test_role_state_flagged_when_next_action_says_recommend_close(self):
        rid = dbmod.add_role("Beacon", "Senior PM",
                             next_action="Recommend close — domain mismatch")
        s = dbmod.get_role_state_for_skill(rid)
        self.assertTrue(s["flagged"])

    def test_role_state_includes_open_decisions(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        dbmod.add_session_note("decision", "Comp not confirmed", role_id=rid)
        s = dbmod.get_role_state_for_skill(rid)
        self.assertEqual(len(s["open_decisions"]), 1)
        self.assertIn("Comp not confirmed", s["open_decisions"][0]["body"])

    # ── log_jd_analysis ────────────────────────────────────────────────────

    def test_jd_analysis_writes_components_and_overall(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        old, new, snap = dbmod.log_jd_analysis(
            role_id=rid, tech_fit=8, culture_fit=7,
            file_path="references/analyses/x.md", verdict="pursue",
            fit_notes="Strong infra fit"
        )
        self.assertIsNone(old)
        self.assertAlmostEqual(new, round(0.6 * 8 + 0.4 * 7, 1))
        row = self._row(rid)
        self.assertEqual(row["tech_fit"], 8)
        self.assertEqual(row["culture_fit"], 7)
        self.assertEqual(row["overall_fit"], 7.6)
        self.assertEqual(row["fit_notes"], "Strong infra fit")

    def test_jd_analysis_saves_previous_fit_on_revision(self):
        rid = dbmod.add_role("Acme", "Sr PM",
                             tech_fit=8, culture_fit=7, overall_fit=7.6)
        dbmod.log_jd_analysis(
            role_id=rid, tech_fit=7, culture_fit=6,
            file_path="references/analyses/x.md", verdict="research"
        )
        row = self._row(rid)
        self.assertEqual(row["previous_fit"], 7.6)
        self.assertEqual(row["overall_fit"], round(0.6 * 7 + 0.4 * 6, 1))

    def test_jd_analysis_no_previous_when_score_unchanged(self):
        rid = dbmod.add_role("Acme", "Sr PM",
                             tech_fit=8, culture_fit=7, overall_fit=7.6)
        dbmod.log_jd_analysis(
            role_id=rid, tech_fit=8, culture_fit=7,
            file_path="references/analyses/x.md"
        )
        row = self._row(rid)
        # previous_fit unchanged from initial (None)
        self.assertIsNone(row["previous_fit"])

    def test_jd_analysis_logs_snapshot(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        _, _, snap = dbmod.log_jd_analysis(
            role_id=rid, tech_fit=8, culture_fit=7,
            file_path="references/analyses/x.md", verdict="pursue"
        )
        with dbmod.con() as db:
            row = db.execute(
                "SELECT skill_type, file_path, verdict FROM analysis_snapshots "
                "WHERE id=?", (snap,)
            ).fetchone()
        self.assertEqual(row["skill_type"], "analyze-jd")
        self.assertEqual(row["verdict"], "pursue")

    # ── log_culture_revision ───────────────────────────────────────────────

    def test_culture_revision_recomputes_using_existing_tech(self):
        rid = dbmod.add_role("Acme", "Sr PM",
                             tech_fit=8, culture_fit=7, overall_fit=7.6)
        old, new, _ = dbmod.log_culture_revision(
            role_id=rid, culture_fit=9,
            file_path="references/analyses/x.md", verdict="pursue"
        )
        self.assertEqual(old, 7.6)
        self.assertEqual(new, round(0.6 * 8 + 0.4 * 9, 1))
        row = self._row(rid)
        self.assertEqual(row["tech_fit"], 8)  # untouched
        self.assertEqual(row["culture_fit"], 9)
        self.assertEqual(row["previous_fit"], 7.6)

    def test_culture_revision_records_snapshot_with_correct_skill_type(self):
        rid = dbmod.add_role("Acme", "Sr PM", tech_fit=8, culture_fit=7)
        _, _, snap = dbmod.log_culture_revision(
            role_id=rid, culture_fit=8,
            file_path="references/analyses/x.md"
        )
        with dbmod.con() as db:
            stype = db.execute(
                "SELECT skill_type FROM analysis_snapshots WHERE id=?", (snap,)
            ).fetchone()[0]
        self.assertEqual(stype, "score-fit")

    # ── thin wrappers ──────────────────────────────────────────────────────

    def test_log_company_research(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        snap = dbmod.log_company_research(
            role_id=rid, file_path="references/analyses/x.md", verdict="pursue"
        )
        with dbmod.con() as db:
            row = db.execute(
                "SELECT skill_type, verdict FROM analysis_snapshots WHERE id=?",
                (snap,)
            ).fetchone()
        self.assertEqual(row["skill_type"], "company-research")
        self.assertEqual(row["verdict"], "pursue")

    def test_log_find_contacts_run(self):
        rid = dbmod.add_role("Acme", "Sr PM")
        snap = dbmod.log_find_contacts_run(
            role_id=rid, file_path="references/analyses/x.md"
        )
        with dbmod.con() as db:
            stype = db.execute(
                "SELECT skill_type FROM analysis_snapshots WHERE id=?", (snap,)
            ).fetchone()[0]
        self.assertEqual(stype, "find-contacts")

    # ── formula correctness ────────────────────────────────────────────────

    def test_formula_is_60_40_split(self):
        # Spot-check: 0.6 * tech + 0.4 * culture, rounded to 1 decimal.
        cases = [
            (10, 10, 10.0),
            (8, 6, round(0.6 * 8 + 0.4 * 6, 1)),
            (5, 9, round(0.6 * 5 + 0.4 * 9, 1)),
        ]
        for tech, culture, expected in cases:
            self.assertEqual(
                dbmod._compute_overall_fit(tech, culture), expected,
                f"({tech}, {culture})"
            )
        self.assertIsNone(dbmod._compute_overall_fit(None, 7))
        self.assertIsNone(dbmod._compute_overall_fit(7, None))


if __name__ == "__main__":
    unittest.main()
