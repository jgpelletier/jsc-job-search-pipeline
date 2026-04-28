"""
Tests for the migration runner in db/db.py.

Run from the repo root:  python3 -m unittest tests.test_migrations
Or:                       python3 -m unittest discover tests

Uses stdlib unittest only — no pytest required so council members can run
tests on a clean checkout without installing anything.
"""

import os
import sqlite3
import sys
import tempfile
import textwrap
import unittest

# Put repo root on sys.path so `import db.db` resolves correctly even when
# tests/ is run as a script directory.
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from db import db as dbmod


# Faithful reproduction of v0.1.0 init_db.py output (the buggy schema —
# missing roles.source_file and roles.previous_fit). Used to simulate a
# council member upgrading from v0.1.0.
V010_SCHEMA = """
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    website TEXT, size TEXT, stage TEXT, domain TEXT, hq TEXT,
    remote_friendly INTEGER, notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    title TEXT NOT NULL, url TEXT, source TEXT,
    status TEXT DEFAULT 'Researching',
    tech_fit REAL, culture_fit REAL, overall_fit REAL,
    comp_min INTEGER, comp_max INTEGER,
    remote TEXT, location TEXT, jd_text TEXT, fit_notes TEXT,
    next_action TEXT, next_action_due TEXT,
    disqualified INTEGER DEFAULT 0, disqualify_reason TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
"""


class MigrationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "test.db")
        # Default to the real migrations/ dir — individual tests can override.
        self.migrations_dir = os.path.join(REPO_ROOT, "migrations")

    def tearDown(self):
        self.tmp.cleanup()

    # ── helpers ────────────────────────────────────────────────────────────

    def _columns(self, conn, table):
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}

    def _versions(self, conn):
        return [r[0] for r in conn.execute(
            "SELECT version FROM schema_version ORDER BY version"
        ).fetchall()]

    # ── tests ──────────────────────────────────────────────────────────────

    def test_fresh_db_applies_all_migrations(self):
        dbmod._apply_migrations(self.db_path, self.migrations_dir, verbose=False)
        conn = sqlite3.connect(self.db_path)
        try:
            versions = self._versions(conn)
            self.assertGreaterEqual(len(versions), 2)
            self.assertEqual(versions[0], 1)
            cols = self._columns(conn, "roles")
            self.assertIn("source_file", cols)
            self.assertIn("previous_fit", cols)
        finally:
            conn.close()

    def test_idempotent_rerun(self):
        dbmod._apply_migrations(self.db_path, self.migrations_dir, verbose=False)
        first = sqlite3.connect(self.db_path)
        try:
            v1 = self._versions(first)
        finally:
            first.close()
        # Second run should be a no-op.
        dbmod._apply_migrations(self.db_path, self.migrations_dir, verbose=False)
        second = sqlite3.connect(self.db_path)
        try:
            v2 = self._versions(second)
        finally:
            second.close()
        self.assertEqual(v1, v2)

    def test_v010_db_upgrades_in_place(self):
        # Build a DB that looks like v0.1.0 init_db.py left it (no
        # schema_version table, no source_file/previous_fit columns).
        legacy = sqlite3.connect(self.db_path)
        try:
            legacy.executescript(V010_SCHEMA)
            legacy.execute(
                "INSERT INTO companies (name) VALUES (?)", ("LegacyCo",)
            )
            legacy.commit()
        finally:
            legacy.close()

        # Apply migrations.
        dbmod._apply_migrations(self.db_path, self.migrations_dir, verbose=False)

        # Existing data should survive.
        conn = sqlite3.connect(self.db_path)
        try:
            self.assertEqual(
                conn.execute("SELECT name FROM companies").fetchone()[0],
                "LegacyCo",
            )
            cols = self._columns(conn, "roles")
            self.assertIn("source_file", cols)
            self.assertIn("previous_fit", cols)
            self.assertGreaterEqual(self._versions(conn)[-1], 2)
        finally:
            conn.close()

    def test_pre_patched_v010_tolerates_duplicate_column(self):
        # A council member who hand-patched their v0.1.0 DB may already have
        # source_file / previous_fit. Migration 002 should not fail them.
        legacy = sqlite3.connect(self.db_path)
        try:
            legacy.executescript(V010_SCHEMA)
            legacy.execute("ALTER TABLE roles ADD COLUMN source_file TEXT")
            legacy.execute("ALTER TABLE roles ADD COLUMN previous_fit REAL")
            legacy.commit()
        finally:
            legacy.close()

        # Should not raise.
        dbmod._apply_migrations(self.db_path, self.migrations_dir, verbose=False)

        conn = sqlite3.connect(self.db_path)
        try:
            self.assertGreaterEqual(self._versions(conn)[-1], 2)
        finally:
            conn.close()

    def test_new_migration_picked_up(self):
        # Stage the real migrations into a temp dir, add a fake 999, and
        # verify the runner applies it on top of an already-migrated DB.
        custom_dir = os.path.join(self.tmp.name, "migrations")
        os.makedirs(custom_dir)
        for fname in os.listdir(self.migrations_dir):
            if fname.endswith(".sql"):
                src = os.path.join(self.migrations_dir, fname)
                dst = os.path.join(custom_dir, fname)
                with open(src) as f, open(dst, "w") as g:
                    g.write(f.read())

        dbmod._apply_migrations(self.db_path, custom_dir, verbose=False)

        with open(os.path.join(custom_dir, "999-test-marker.sql"), "w") as f:
            f.write(textwrap.dedent("""
                CREATE TABLE test_marker (id INTEGER PRIMARY KEY);
                INSERT INTO test_marker (id) VALUES (42);
            """))

        dbmod._apply_migrations(self.db_path, custom_dir, verbose=False)

        conn = sqlite3.connect(self.db_path)
        try:
            self.assertEqual(
                conn.execute("SELECT id FROM test_marker").fetchone()[0], 42
            )
            self.assertIn(999, self._versions(conn))
        finally:
            conn.close()

    def test_filename_must_match_pattern(self):
        custom_dir = os.path.join(self.tmp.name, "migrations")
        os.makedirs(custom_dir)
        # Wrong filename pattern — no leading version number.
        with open(os.path.join(custom_dir, "missing-version.sql"), "w") as f:
            f.write("CREATE TABLE should_not_exist (id INTEGER);")

        dbmod._apply_migrations(self.db_path, custom_dir, verbose=False)

        # No file matched, so nothing was created and no schema_version table
        # exists either.
        conn = sqlite3.connect(self.db_path)
        try:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            self.assertNotIn("should_not_exist", tables)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
