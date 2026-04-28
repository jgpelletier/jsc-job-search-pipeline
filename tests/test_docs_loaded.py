"""
Drift guard for the CLAUDE.md split.

CLAUDE.md must reference every docs/*.md file and instruct the agent to
read them at session start. Tests fail if a file disappears or is forgotten.

Run: python3 -m unittest tests.test_docs_loaded
"""

import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
CLAUDE_MD = os.path.join(REPO_ROOT, "CLAUDE.md")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")

# Files that must exist and must be referenced from CLAUDE.md.
REQUIRED_DOCS = [
    "docs/decision-logic.md",
    "docs/workflow.md",
    "docs/voice-and-drafting.md",
]


class DocsLoadedTests(unittest.TestCase):

    def test_all_required_docs_exist(self):
        for rel in REQUIRED_DOCS:
            self.assertTrue(
                os.path.isfile(os.path.join(REPO_ROOT, rel)),
                f"Missing required passive-context file: {rel}"
            )

    def test_claude_md_references_each_doc(self):
        with open(CLAUDE_MD) as f:
            text = f.read()
        for rel in REQUIRED_DOCS:
            self.assertIn(
                rel, text,
                f"CLAUDE.md does not reference {rel}; passive context will not load."
            )

    def test_session_start_protocol_lists_docs(self):
        """The session-start protocol must explicitly tell the agent to read docs/."""
        with open(CLAUDE_MD) as f:
            text = f.read()

        # Find the Session Start Protocol section.
        start = text.find("## Session Start Protocol")
        end = text.find("## Session End Protocol", start)
        self.assertGreater(start, 0, "CLAUDE.md missing Session Start Protocol")
        self.assertGreater(end, start, "CLAUDE.md missing Session End Protocol marker")
        section = text[start:end]

        for rel in REQUIRED_DOCS:
            basename = os.path.basename(rel)
            self.assertTrue(
                rel in section or basename in section,
                f"Session Start Protocol does not mention {rel}; "
                f"agent will not load it."
            )


if __name__ == "__main__":
    unittest.main()
