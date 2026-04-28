"""
Drift guard: SKILL.md files must not embed raw SQL or sqlite3 connections.
All schema-touching code goes through db/db.py named functions.

Run: python3 -m unittest tests.test_skills_no_raw_sql
"""

import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")

# Patterns that indicate skill files are reaching past db.py and into the
# DB or schema directly. Each pattern is matched case-insensitively against
# the full file contents (including code fences).
FORBIDDEN = [
    (r"\bsqlite3\.connect\b",                  "raw sqlite3.connect"),
    (r"\bimport\s+sqlite3\b",                  "import sqlite3"),
    (r"\bconn\.execute\b",                     "conn.execute"),
    (r"\bUPDATE\s+roles\b",                    "UPDATE roles statement"),
    (r"\bINSERT\s+INTO\s+\w+",                 "INSERT INTO statement"),
    (r"\bSELECT\s+\w+.*?\bFROM\s+roles\b",     "SELECT FROM roles"),
    (r"\bSELECT\s+\*\s+FROM\b",                "SELECT * FROM"),
    (r"\bDELETE\s+FROM\b",                     "DELETE FROM"),
]


class NoRawSqlInSkillsTests(unittest.TestCase):

    def test_no_skill_file_uses_raw_sql(self):
        violations = []
        for skill in sorted(os.listdir(SKILLS_DIR)):
            path = os.path.join(SKILLS_DIR, skill, "SKILL.md")
            if not os.path.isfile(path):
                continue
            with open(path) as f:
                text = f.read()
            for pattern, label in FORBIDDEN:
                for m in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                    line = text[:m.start()].count("\n") + 1
                    violations.append(f"  {skill}/SKILL.md:{line}  matched {label}: {m.group(0)[:60]!r}")
        self.assertFalse(
            violations,
            "Skills must call db.* functions instead of embedding SQL.\n" +
            "\n".join(violations)
        )


if __name__ == "__main__":
    unittest.main()
