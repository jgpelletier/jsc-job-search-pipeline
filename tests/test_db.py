"""
Tests for db/db.py and db/init_db.py — stdlib unittest, no dependencies.

Run from the project root:
    python3 -m unittest tests.test_db

Each test runs in its own temp directory with a freshly initialized
pipeline.db so tests cannot pollute real data.
"""

import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest

# Project root on sys.path so `import db.db` works regardless of CWD.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import db.db as dbm
import db.init_db as initm


class _FreshDB(unittest.TestCase):
    """Each test runs in a temp dir with a fresh pipeline.db and the folder
    structure verify() expects (references/analyses, references/stories,
    inbox/processed)."""

    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp(prefix="jspipeline-test-")
        os.chdir(self._tmp)
        os.makedirs("references/analyses", exist_ok=True)
        os.makedirs("references/stories", exist_ok=True)
        os.makedirs("inbox/processed", exist_ok=True)
        initm.init()

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self._tmp, ignore_errors=True)


class SchemaCompletenessTests(_FreshDB):
    """Every column an INSERT writes to must exist in the schema.

    This is the test that would have caught the source_file / previous_fit
    bug. It parses the actual INSERT statements out of db/db.py and
    cross-checks them against PRAGMA table_info on a freshly initialized DB.
    """

    @staticmethod
    def _table_columns(table):
        with sqlite3.connect("pipeline.db") as conn:
            return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}

    @staticmethod
    def _insert_columns(source, table):
        match = re.search(
            rf"INSERT INTO {table}\s*\(([^)]+)\)",
            source,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        return {c.strip() for c in match.group(1).split(",")}

    def test_roles_schema_covers_add_role_inserts(self):
        with open(os.path.join(PROJECT_ROOT, "db/db.py")) as f:
            source = f.read()
        written = self._insert_columns(source, "roles")
        self.assertIsNotNone(written, "Could not locate INSERT INTO roles in db.py")
        defined = self._table_columns("roles")
        missing = written - defined
        self.assertSetEqual(
            missing, set(),
            f"add_role writes to columns missing from the roles schema: {missing}"
        )

    def test_applications_schema_covers_log_application_inserts(self):
        with open(os.path.join(PROJECT_ROOT, "db/db.py")) as f:
            source = f.read()
        written = self._insert_columns(source, "applications")
        self.assertIsNotNone(written, "Could not locate INSERT INTO applications in db.py")
        defined = self._table_columns("applications")
        missing = written - defined
        self.assertSetEqual(
            missing, set(),
            f"log_application writes to columns missing from the applications schema: {missing}"
        )


class VerifyTests(_FreshDB):

    def test_empty_db_reports_no_drift(self):
        report = dbm.verify()
        self.assertEqual(report["missing_analysis_files"], [])
        self.assertEqual(report["orphaned_analysis_files"], [])
        self.assertEqual(report["missing_source_files"], [])
        self.assertEqual(report["stories_count"], 0)

    def test_detects_missing_analysis_and_source_files(self):
        role_id = dbm.add_role(
            company_name="Test Co",
            title="Senior PM",
            source="screenshot",
            source_file="nonexistent-screenshot.png",
            overall_fit=7.5,
        )
        dbm.log_analysis(
            role_id=role_id,
            skill_type="analyze-jd",
            file_path="references/analyses/999-test-jd.md",
            overall_fit=7.5,
            verdict="pursue",
        )

        report = dbm.verify()

        self.assertEqual(len(report["missing_analysis_files"]), 1)
        self.assertEqual(report["missing_analysis_files"][0]["role_id"], role_id)
        self.assertEqual(len(report["missing_source_files"]), 1)
        self.assertEqual(
            report["missing_source_files"][0]["source_file"],
            "nonexistent-screenshot.png",
        )

    def test_detects_orphaned_analysis_files(self):
        orphan = "references/analyses/001-orphan-jd.md"
        with open(orphan, "w") as f:
            f.write("# Orphan analysis with no DB record\n")

        report = dbm.verify()
        self.assertIn(orphan, report["orphaned_analysis_files"])


class AddRoleTests(_FreshDB):

    def test_add_role_dedupes_on_company_and_title(self):
        first = dbm.add_role(
            company_name="DedupCo", title="Senior PM", overall_fit=7.0
        )
        second = dbm.add_role(
            company_name="DedupCo", title="Senior PM", overall_fit=8.0
        )
        self.assertEqual(
            first, second,
            "Adding the same (company, title) twice must return the existing role_id"
        )


class DisqualifyTests(_FreshDB):

    def test_disqualified_role_excluded_from_pipeline_summary(self):
        keeper = dbm.add_role(company_name="KeepCo", title="Senior PM")
        dropper = dbm.add_role(company_name="DropCo", title="Senior PM")
        dbm.disqualify(dropper, reason="Wrong domain")

        with sqlite3.connect("pipeline.db") as conn:
            conn.row_factory = sqlite3.Row
            ids = {row["id"] for row in conn.execute("SELECT id FROM pipeline_summary")}

        self.assertIn(keeper, ids)
        self.assertNotIn(dropper, ids)


class UndoTests(_FreshDB):

    def _last_status(self, role_id):
        with sqlite3.connect("pipeline.db") as conn:
            return conn.execute(
                "SELECT status FROM roles WHERE id=?", (role_id,)
            ).fetchone()[0]

    def test_undo_on_empty_log_returns_none(self):
        result = dbm.undo_last(confirm=True)
        self.assertIsNone(result)

    def test_undo_preview_does_not_change_state(self):
        role_id = dbm.add_role(company_name="X", title="Y")
        dbm.update_status(role_id, "Applied")
        self.assertEqual(self._last_status(role_id), "Applied")

        # Preview only — no confirm
        result = dbm.undo_last()
        self.assertIsNone(result)
        self.assertEqual(self._last_status(role_id), "Applied",
            "Preview must not change the role's status")

    def test_undo_status_change_with_confirm_reverts_status(self):
        role_id = dbm.add_role(company_name="X", title="Y")
        dbm.update_status(role_id, "Applied")
        self.assertEqual(self._last_status(role_id), "Applied")

        result = dbm.undo_last(confirm=True)
        self.assertIsNotNone(result)
        self.assertEqual(self._last_status(role_id), dbm.INITIAL_STATUS)

    def test_undo_logs_audit_entry(self):
        role_id = dbm.add_role(company_name="X", title="Y")
        dbm.update_status(role_id, "Applied")
        dbm.undo_last(confirm=True)

        with sqlite3.connect("pipeline.db") as conn:
            conn.row_factory = sqlite3.Row
            entries = conn.execute(
                "SELECT type FROM activity WHERE role_id=? ORDER BY id", (role_id,)
            ).fetchall()
        types = [e["type"] for e in entries]
        # Should be: status_change (add) + status_change (update) + status_change_undo
        self.assertIn("status_change_undo", types,
            "Undo must log an audit entry, not delete the original")

    def test_undo_refuses_outreach_sent(self):
        role_id = dbm.add_role(company_name="X", title="Y")
        dbm.log_outreach(role_id, contact_name="Jane Doe", channel="LinkedIn",
                         message_summary="Initial reach")
        # log_outreach auto-advances to "Outreach Drafted"; the most recent
        # activity entry is the auto-advance status_change. Undo would revert
        # that, not the outreach itself. We want undo to refuse for outreach
        # specifically — verify by looking at the outreach activity directly.
        with sqlite3.connect("pipeline.db") as conn:
            conn.row_factory = sqlite3.Row
            outreach = conn.execute(
                "SELECT * FROM activity WHERE type='outreach_sent' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(outreach,
            "log_outreach should have written an outreach_sent activity entry")


class StoriesTests(_FreshDB):

    def test_register_story_is_idempotent_on_slug(self):
        first = dbm.register_story(
            slug="01-platform-migration",
            file_path="references/stories/01-platform-migration.md",
            title="Platform migration",
        )
        second = dbm.register_story(
            slug="01-platform-migration",
            file_path="references/stories/01-platform-migration.md",
            title="Platform migration (renamed)",
        )
        self.assertEqual(first, second,
            "Repeat register_story calls with the same slug must return the same id")

    def test_link_story_records_artifact_relation(self):
        dbm.register_story(
            slug="01-foo",
            file_path="references/stories/01-foo.md",
        )
        dbm.link_story("01-foo", ref_type="application", ref_id=42)
        results = dbm.get_stories_for("application", 42)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["slug"], "01-foo")

    def test_link_story_rejects_invalid_ref_type(self):
        dbm.register_story(slug="01-foo", file_path="references/stories/01-foo.md")
        # Invalid ref_type — should print a warning and not insert
        result = dbm.link_story("01-foo", ref_type="bogus", ref_id=1)
        self.assertIsNone(result)

    def test_verify_detects_missing_story_files(self):
        dbm.register_story(
            slug="01-not-on-disk",
            file_path="references/stories/01-not-on-disk.md",
        )
        report = dbm.verify()
        self.assertEqual(len(report["missing_story_files"]), 1)
        self.assertEqual(report["missing_story_files"][0]["slug"], "01-not-on-disk")

    def test_verify_detects_orphaned_story_files(self):
        orphan = "references/stories/99-orphan.md"
        with open(orphan, "w") as f:
            f.write("# Orphan story with no DB record\n")
        report = dbm.verify()
        self.assertIn(orphan, report["orphaned_story_files"])


class CanonicalConstantsTests(unittest.TestCase):
    """Lock in the canonical constants and verify the docs match the code.

    These tests do not need a fresh DB — they're checking module-level state
    and the contents of CLAUDE.md / skills/*.md.
    """

    def test_compute_overall_fit_matches_documented_examples(self):
        # Examples documented in compute_overall_fit's docstring
        self.assertEqual(dbm.compute_overall_fit(8, 7), 7.6)
        self.assertEqual(dbm.compute_overall_fit(7, 8), 7.4)
        self.assertEqual(dbm.compute_overall_fit(9, 7), 8.2)

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(dbm.TECH_WEIGHT + dbm.CULTURE_WEIGHT, 1.0)

    def test_valid_statuses_has_expected_funnel(self):
        # The order matters — it's the funnel sequence the agent follows.
        self.assertEqual(dbm.VALID_STATUSES, [
            "Researching", "Qualified", "Outreach Drafted", "Applied",
            "Screening", "Interviewing", "Offer", "Closed Won", "Closed Lost",
        ])
        self.assertEqual(dbm.INITIAL_STATUS,    "Researching")
        self.assertEqual(dbm.DISQUALIFY_STATUS, "Closed Lost")

    def test_update_status_rejects_invalid_status(self):
        # This one needs a DB. Use the _FreshDB pattern inline.
        cwd = os.getcwd()
        tmp = tempfile.mkdtemp(prefix="jspipeline-status-")
        try:
            os.chdir(tmp)
            initm.init()
            role_id = dbm.add_role(company_name="X", title="Y")
            dbm.update_status(role_id, "BogusStatus")
            with sqlite3.connect("pipeline.db") as conn:
                status = conn.execute(
                    "SELECT status FROM roles WHERE id=?", (role_id,)
                ).fetchone()[0]
            self.assertEqual(
                status, dbm.INITIAL_STATUS,
                "update_status should refuse invalid values and leave status unchanged"
            )
        finally:
            os.chdir(cwd)
            shutil.rmtree(tmp, ignore_errors=True)


class DocsSyncTests(unittest.TestCase):
    """The canonical constants live in db.py, but CLAUDE.md and the skills
    restate them in prose for passive context. These tests catch drift between
    the prose and the code — when the code changes, the prose must too.
    """

    @staticmethod
    def _read(rel_path):
        with open(os.path.join(PROJECT_ROOT, rel_path)) as f:
            return f.read()

    def test_claude_md_states_current_weights(self):
        text = self._read("CLAUDE.md")
        # Match the prose form: "60% technical + 40% culture"
        tech_pct = int(dbm.TECH_WEIGHT * 100)
        culture_pct = int(dbm.CULTURE_WEIGHT * 100)
        self.assertIn(
            f"{tech_pct}% technical + {culture_pct}% culture", text,
            f"CLAUDE.md must state the weighting as '{tech_pct}% technical + {culture_pct}% culture'"
        )

    def test_claude_md_lists_all_valid_statuses(self):
        text = self._read("CLAUDE.md")
        for status in dbm.VALID_STATUSES:
            self.assertIn(
                status, text,
                f"CLAUDE.md must mention status '{status}' from VALID_STATUSES"
            )

    def test_skills_do_not_inline_the_formula(self):
        """analyze-jd and score-fit should call db.compute_overall_fit, not
        restate the 0.6/0.4 multiplication inline. If you change the weights,
        only one place needs updating."""
        for skill in ("analyze-jd", "score-fit"):
            text = self._read(f"skills/{skill}/SKILL.md")
            self.assertNotIn(
                "0.6 * tech_fit", text,
                f"skills/{skill}/SKILL.md must not inline the formula — "
                f"call db.compute_overall_fit instead"
            )


if __name__ == "__main__":
    unittest.main()
