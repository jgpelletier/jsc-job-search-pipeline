# references/

Personal context the agents read to do their work. Fill these in once at
setup; update as your story evolves.

| File | Purpose |
|------|---------|
| `resume.md` | Master resume in markdown. Source of truth for bullets and metrics. |
| `cmf.md` | Candidate Market Fit — your one-line pitch, target scenarios, hard constraints, voice anchors. |
| `mnookin.md` | Hard must-haves and must-not signals used by `score-fit` and `analyze-jd`. |
| `stories/` | Verified work stories. One file per story. Used instead of reconstructing facts from resume bullets. |
| `analyses/` | Per-role artifacts produced during the pipeline (jd, fit, bullets, outreach, etc.). |

## YAML frontmatter convention

`mnookin.md` and `cmf.md` carry a small YAML frontmatter block bracketed by
`---` lines at the top of the file. The narrative body underneath is what
the LLM reads at session start; the frontmatter is what code reads via
`db.load_references()`, `db.get_must_haves()`, `db.get_must_nots()`,
`db.get_voice_anchors()`.

**Edit both.** The body and frontmatter should agree. We chose this dual
representation because:

- The LLM reads markdown perfectly well — it doesn't need YAML.
- Tests, dashboards, and any non-LLM tooling want structured access without
  re-parsing prose each turn.

The parser is intentionally tiny (in `db/db.py`) and supports only the
patterns these files actually use: `key: value`, `key:` + indented
`- item`, and `key:` + indented `subkey: value`. Stick to those.

If you skip the frontmatter entirely the agent still works — `db.get_*`
functions return empty lists. Skills that need structured fields will fall
back to reading the markdown body.
