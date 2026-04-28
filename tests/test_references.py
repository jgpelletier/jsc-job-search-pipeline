"""
Tests for references/*.md frontmatter convention and the stdlib YAML parser.

Run: python3 -m unittest tests.test_references
"""

import os
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from db import db as dbmod


class FrontmatterParserTests(unittest.TestCase):

    def test_no_frontmatter_returns_empty_dict_and_full_body(self):
        text = "# Title\n\nBody text."
        fm, body = dbmod.parse_frontmatter(text)
        self.assertEqual(fm, {})
        self.assertEqual(body, text)

    def test_simple_string_keys(self):
        text = textwrap.dedent("""\
            ---
            name: Alice
            role: PM
            ---
            # Body
            """)
        fm, body = dbmod.parse_frontmatter(text)
        self.assertEqual(fm, {"name": "Alice", "role": "PM"})
        self.assertTrue(body.startswith("# Body"))

    def test_list_under_key(self):
        text = textwrap.dedent("""\
            ---
            must_haves:
              - end-to-end ownership
              - access to operational data
              - "coaching manager"
            ---
            body
            """)
        fm, _ = dbmod.parse_frontmatter(text)
        self.assertEqual(fm["must_haves"], [
            "end-to-end ownership",
            "access to operational data",
            "coaching manager",
        ])

    def test_nested_dict_under_key(self):
        text = textwrap.dedent("""\
            ---
            hard_constraints:
              location: Remote (PST/MST/CST)
              domain: PM roles only
            ---
            body
            """)
        fm, _ = dbmod.parse_frontmatter(text)
        self.assertEqual(fm["hard_constraints"], {
            "location": "Remote (PST/MST/CST)",
            "domain": "PM roles only",
        })

    def test_empty_list_when_key_has_no_children(self):
        text = textwrap.dedent("""\
            ---
            must_haves:
            must_nots:
              - prescribed solutions
            ---
            body
            """)
        fm, _ = dbmod.parse_frontmatter(text)
        self.assertEqual(fm["must_haves"], [])
        self.assertEqual(fm["must_nots"], ["prescribed solutions"])

    def test_comments_and_blank_lines_ignored(self):
        text = textwrap.dedent("""\
            ---
            # leading comment
            must_haves:
              # nested comment
              - end-to-end ownership

              - access to operational data
            ---
            body
            """)
        fm, _ = dbmod.parse_frontmatter(text)
        self.assertEqual(fm["must_haves"], [
            "end-to-end ownership",
            "access to operational data",
        ])


class LoadReferencesTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.refs_dir = os.path.join(self.tmp.name, "references")
        os.makedirs(self.refs_dir)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, text):
        with open(os.path.join(self.refs_dir, f"{name}.md"), "w") as f:
            f.write(text)

    def test_load_references_returns_per_file_entries(self):
        self._write("mnookin", textwrap.dedent("""\
            ---
            must_haves:
              - end-to-end ownership
            must_nots:
              - prescribed solutions
            ---
            # body
            """))
        self._write("cmf", textwrap.dedent("""\
            ---
            voice_anchors:
              - "I built X"
            ---
            # body
            """))
        refs = dbmod.load_references(self.refs_dir)
        self.assertIn("mnookin", refs)
        self.assertIn("cmf", refs)
        self.assertEqual(refs["mnookin"]["frontmatter"]["must_haves"],
                         ["end-to-end ownership"])
        self.assertEqual(refs["cmf"]["frontmatter"]["voice_anchors"],
                         ["I built X"])
        # Body is preserved.
        self.assertIn("# body", refs["mnookin"]["body"])

    def test_load_references_skips_missing_files(self):
        self._write("mnookin", "no frontmatter here")
        refs = dbmod.load_references(self.refs_dir)
        self.assertIn("mnookin", refs)
        self.assertEqual(refs["mnookin"]["frontmatter"], {})
        self.assertNotIn("cmf", refs)
        self.assertNotIn("resume", refs)

    def test_get_must_haves_empty_when_unset(self):
        # No mnookin.md present at all.
        # We can't easily monkey-patch REFERENCES_DIR cleanly, so call the
        # underlying load with our temp dir and verify the path.
        self._write("mnookin", "")
        refs = dbmod.load_references(self.refs_dir)
        self.assertEqual(
            refs.get("mnookin", {}).get("frontmatter", {}).get("must_haves", []),
            []
        )


class TemplateReferencesTests(unittest.TestCase):
    """Sanity-check the references/*.md files shipped with the template."""

    def test_template_mnookin_has_frontmatter_keys(self):
        path = os.path.join(REPO_ROOT, "references", "mnookin.md")
        with open(path) as f:
            text = f.read()
        fm, _ = dbmod.parse_frontmatter(text)
        # Even if values are empty for the candidate to fill in, the keys
        # must exist so council members know what to populate.
        for key in ("must_haves", "must_nots", "soft_preferences"):
            self.assertIn(key, fm, f"references/mnookin.md missing frontmatter key: {key}")

    def test_template_cmf_has_frontmatter_keys(self):
        path = os.path.join(REPO_ROOT, "references", "cmf.md")
        with open(path) as f:
            text = f.read()
        fm, _ = dbmod.parse_frontmatter(text)
        for key in ("voice_anchors", "target_scenarios", "hard_constraints"):
            self.assertIn(key, fm, f"references/cmf.md missing frontmatter key: {key}")


if __name__ == "__main__":
    unittest.main()
