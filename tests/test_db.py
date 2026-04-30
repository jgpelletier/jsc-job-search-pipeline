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


if __name__ == "__main__":
    unittest.main()
