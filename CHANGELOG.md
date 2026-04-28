# Changelog

All notable changes to this template are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html); the public API
covered by SemVer is the `db.*` function names, the skill names, the
`references/` layout, and the `python3 db/init_db.py` bootstrap idiom.

## [Unreleased]

(No changes since v0.2.3.)

## [0.2.3] — 2026-04-28

### Added
- `tests/test_judgment.py` — 13 deterministic gate tests on the judgment
  surface:
  - `update_status` rejects invalid statuses; accepts every valid one
  - `update_status` writes a `status_change` activity entry
  - `disqualify` is a soft remove (no DELETE), reason persisted, row
    excluded from `pipeline_summary`
  - `log_application` auto-advances to Applied with a 7-day follow-up
  - `log_outreach` auto-advances Researching → Outreach Drafted, but only
    from Researching
  - `log_response` writes activity without changing status
  - `log_jd_analysis` writes a `score_revision` activity row when the
    score changes; not when it doesn't

  These cover the deterministic edges. LLM-graded scoring (whether a JD
  contains a must-not in prose, whether a draft sounds generic) is
  intentionally not tested — it isn't deterministic by definition.

### Fixed
- **`log_outreach` deadlock.** v0.1.0's `log_outreach` called
  `update_status` from inside an open `con()` context, which deadlocked
  against its own write lock for SQLite's 5-second timeout before
  succeeding. Restructured to mirror `log_application`: collect the
  intended advance, exit the with-block, then call `update_status`.

### Compatibility
- No DB or public API changes. Existing callers behave the same — they
  just no longer wait 5 seconds.

## [0.2.2] — 2026-04-28

### Added
- **YAML frontmatter on `references/mnookin.md` and `references/cmf.md`.**
  Structured fields (`must_haves`, `must_nots`, `soft_preferences`,
  `voice_anchors`, `target_scenarios`, `hard_constraints`) are now machine-
  readable. The narrative body is unchanged — the LLM still reads it at
  session start.
- New `db.*` functions for structured access:
  - `db.load_references(directory=None)` — returns `{file: {frontmatter, body, path}}`
  - `db.get_must_haves()`, `db.get_must_nots()`, `db.get_voice_anchors()`
  - `db.parse_frontmatter(text)` — exposed for tests and tooling
- Stdlib-only YAML mini-parser (no third-party dep). Handles
  `key: value`, `key:` + indented `- item`, and `key:` + indented
  `subkey: value`. Stick to those patterns when writing frontmatter.
- `tests/test_references.py` — 11 cases covering parser edge cases, load
  semantics, and the shipped template files.
- `references/README.md` documents the dual-representation convention and
  the parser's supported subset.

### Changed
- `CLAUDE.md` Database Operations cheat-sheet adds the new functions.
- `docs/decision-logic.md` mentions the structured access path.

### Compatibility
- No DB changes. Council members who haven't adopted frontmatter still
  work — `db.get_must_haves()` etc. return `[]` when the field is missing.

## [0.2.1] — 2026-04-28

### Changed
- **CLAUDE.md split into focused passive-context files.** The judgment logic
  that previously lived in a single 451-line CLAUDE.md is now spread across
  three files in `docs/`:
  - `docs/decision-logic.md` — fit scoring, must-haves, language signals, transferable skills
  - `docs/workflow.md` — workflow paths, gates, application logging, data integrity, subagent rules, inbox folder
  - `docs/voice-and-drafting.md` — voice rules, outreach hooks, bullets, cover letter, stories
- CLAUDE.md is now 168 lines: role, candidate context, session protocols,
  database cheat-sheet, and a pointer block telling the agent to read all
  three docs/* files at session start. Passive-context principle preserved.

### Added
- `tests/test_docs_loaded.py` — drift guard. Asserts each required docs/*
  file exists, is referenced from CLAUDE.md, and is named in the Session
  Start Protocol.

### Compatibility
- No DB changes. No public API changes. Existing skills and `db.*`
  functions are unchanged. Council members who customized their CLAUDE.md
  should diff against v0.2.0 and re-apply local edits to the new file
  structure.

## [0.2.0] — 2026-04-28

Cumulative release of the rc1 + rc2 + rc3 changes. Council members
upgrading from v0.1.0 should read the per-rc entries below for the full
detail. The high-level summary:

- Schema is versioned. `python3 db/init_db.py` is now an idempotent
  migration runner over `migrations/NNN-*.sql`. Existing v0.1.0 DBs upgrade
  in place; the v0.1.0 schema bug (missing `roles.source_file` and
  `roles.previous_fit`) is repaired automatically.
- `pipeline.md` and `HANDOFF.md` are render outputs of `pipeline.db`. Both
  files carry a do-not-hand-edit header and regenerate on session start
  (via `.claude/settings.json` SessionStart hook) and on demand
  (`python3 db/db.py render`). Open decisions and end-of-session summaries
  live in the new `session_notes` table.
- Skills no longer embed SQL or column names. New helpers in `db.py`
  (`get_role_state_for_skill`, `log_jd_analysis`, `log_culture_revision`,
  `log_company_research`, `log_find_contacts_run`) own all schema-touching
  logic. A drift guard (`tests/test_skills_no_raw_sql.py`) keeps it that way.
- Stdlib-`unittest` coverage in `tests/`: 26 cases across migrations, render,
  and skill helpers.

### Compatibility
- `python3 db/init_db.py`, all v0.1.0 `db.*` function names, all skill
  names, `references/` layout, and `pipeline.db` location are unchanged.
- This is the breaking-change minor version called out in the v0.2 plan.
  Subsequent v0.2.x releases (CLAUDE.md split, references frontmatter,
  judgment tests) are additive and non-breaking.

## [0.2.0-rc3] — 2026-04-28

### Added
- **Skill-helper functions in `db/db.py`** — schema knowledge stays in `db.py`;
  skills call named functions:
  - `get_role_state_for_skill(role_id)` — returns the dict skills need for
    pre-flight gate checks (company, status, fit, flagged, open_decisions).
  - `log_jd_analysis(role_id, tech_fit, culture_fit, file_path, ...)` —
    enforces the canonical 0.6·tech + 0.4·culture formula, saves
    `previous_fit` on revision, writes the analysis snapshot. Returns
    `(old_overall, new_overall, snapshot_id)`.
  - `log_culture_revision(role_id, culture_fit, file_path, ...)` — score-fit
    counterpart: reuses existing `tech_fit`, recomputes overall.
  - `log_company_research(role_id, file_path, verdict)` — thin wrapper.
  - `log_find_contacts_run(role_id, file_path)` — thin wrapper.
- `tests/test_skill_logging.py` — 12 cases covering pre-flight state,
  formula, previous_fit semantics, snapshot logging, thin wrappers.
- `tests/test_skills_no_raw_sql.py` — drift guard: greps SKILL.md files for
  `sqlite3.connect`, `INSERT INTO`, `UPDATE roles`, etc. Fails if any
  SKILL.md leaks past `db.*`.

### Changed
- `skills/analyze-jd/SKILL.md` — pre-flight check uses
  `db.get_role_state_for_skill`; persistence uses `db.log_jd_analysis`. No
  raw SQL.
- `skills/score-fit/SKILL.md` — persistence uses `db.log_culture_revision`.
  No raw SQL.
- `skills/company-research/SKILL.md` — uses `db.log_company_research`
  instead of `db.log_analysis(...)` for symmetry.
- `skills/find-contacts/SKILL.md` — uses `db.log_find_contacts_run` for
  symmetry.

### Compatibility
- The original `db.log_analysis(...)` is unchanged and still works; the new
  helpers are wrappers. Council members who have not edited their copy of
  the skill files inherit the new helpers automatically.

## [0.2.0-rc2] — 2026-04-28

### Added
- **DB-authoritative `pipeline.md` and `HANDOFF.md`.** Both files are now
  render outputs of `pipeline.db` and carry a do-not-hand-edit header.
  Regenerate with `db.render_all()` or `python3 db/db.py render`.
- **SessionStart hook** in `.claude/settings.json` runs the render on session
  start so the markdown views are always current.
- New table `session_notes` (migration 003) for state HANDOFF.md needs but
  isn't naturally derivable: open decisions, completion summaries, free-form notes.
- New `db.*` functions:
  - `add_session_note(kind, body, role_id=None)` — kinds: decision, completion, note
  - `resolve_session_note(note_id, resolution=None)`
  - `list_open_decisions(role_id=None)`, `list_recent_completions(limit=3)`
  - `render_pipeline_md(path=None)`, `render_handoff_md(path=None)`, `render_all()`
- New CLI subcommands: `python3 db/db.py render | migrate | note <kind> <body>`.
- `tests/test_render.py` — 6 unittest cases covering empty/seeded/resolved/
  determinism/grouping behaviour.

### Changed
- `CLAUDE.md` Session Start and Session End protocols updated to use the
  render flow. End-of-session: capture notes via `db.add_session_note(...)`,
  then `db.render_all()`. No more hand-editing HANDOFF.md.
- Subagent rules now name both `pipeline.md` and `HANDOFF.md` as files
  subagents must not write.
- Pipeline Files section in `CLAUDE.md` documents both as render outputs.

### Compatibility
- v0.1.0 users: existing roles, contacts, applications, etc. all continue to
  work. The first session after upgrade applies migrations 002 and 003,
  regenerates `pipeline.md` (overwriting any hand edits), and creates
  `HANDOFF.md` from DB state.

## [0.2.0-rc1] — 2026-04-28

### Added
- **Schema versioning.** New `migrations/` directory; the runner in `db/db.py`
  applies pending migrations on first `con()` call per process. `db/init_db.py`
  now delegates to the runner and reports the final schema version.
- `migrations/001-initial.sql` faithfully captures the v0.1.0 schema. Safe to
  run on a fresh DB or on an existing v0.1.0 DB (`CREATE ... IF NOT EXISTS`
  throughout).
- `migrations/002-roles-add-source-file-and-previous-fit.sql` repairs the
  v0.1.0 schema bug below.
- `tests/` directory with stdlib-`unittest` migration coverage. Run via
  `python3 -m unittest discover tests`.
- `migrations/README.md` — discipline rules (append-only, idempotent, etc.).

### Fixed
- **v0.1.0 schema bug.** `db.add_role` wrote to `roles.source_file` and
  `roles.previous_fit`, but `db/init_db.py` never created those columns. Any
  fresh v0.1.0 install would fail on the first `add_role` call. Migration 002
  adds them. The runner tolerates `duplicate column name` errors so council
  members who hand-patched their DB upgrade cleanly.

### Compatibility
- `python3 db/init_db.py` still works exactly as documented in v0.1.0; the
  command now applies migrations instead of executing one big `CREATE TABLE`
  script.
- All `db.*` function names from v0.1.0 are unchanged.
- Skill names, `references/` layout, and `pipeline.db` location are unchanged.

## [0.1.0] — 2026-04-28 (initial public release)

### Added
- Passive-context architecture: judgment logic in `CLAUDE.md`, output
  templates in `skills/*/SKILL.md`, SQLite as source of truth in `pipeline.db`.
- Database tables: companies, roles, contacts, applications, activity,
  search_runs, analysis_snapshots. Views: pipeline_summary, needs_action,
  application_log.
- Skills: intake-screenshot, job-search, analyze-jd, company-research,
  score-fit, find-contacts, draft-resume-bullets, draft-cover-letter,
  draft-outreach, prep-interview.
- References scaffolding: `resume.md`, `cmf.md`, `mnookin.md`, `stories/`,
  `analyses/`.
- Inbox flow: drop screenshots into `inbox/`, processed files moved to
  `inbox/processed/`.
- Daily ops: `python3 db/db.py pipeline | action | stats`.

[Unreleased]: https://github.com/jgpelletier/jsc-job-search-pipeline/compare/v0.2.3...HEAD
[0.2.3]: https://github.com/jgpelletier/jsc-job-search-pipeline/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/jgpelletier/jsc-job-search-pipeline/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/jgpelletier/jsc-job-search-pipeline/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/jgpelletier/jsc-job-search-pipeline/compare/v0.1.0...v0.2.0
[0.2.0-rc3]: https://github.com/jgpelletier/jsc-job-search-pipeline/compare/v0.2.0-rc2...v0.2.0-rc3
[0.2.0-rc2]: https://github.com/jgpelletier/jsc-job-search-pipeline/compare/v0.2.0-rc1...v0.2.0-rc2
[0.2.0-rc1]: https://github.com/jgpelletier/jsc-job-search-pipeline/compare/v0.1.0...v0.2.0-rc1
[0.1.0]: https://github.com/jgpelletier/jsc-job-search-pipeline/releases/tag/v0.1.0
