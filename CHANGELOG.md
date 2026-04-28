# Changelog

All notable changes to this template are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html); the public API
covered by SemVer is the `db.*` function names, the skill names, the
`references/` layout, and the `python3 db/init_db.py` bootstrap idiom.

## [Unreleased]

### Pending for v0.2.0
- DB-authoritative `pipeline.md` and `HANDOFF.md` (rc2).
- Skills decoupled from raw SQL (rc3).

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

[Unreleased]: https://github.com/jgpelletier/jsc-job-search-pipeline/compare/v0.2.0-rc1...HEAD
[0.2.0-rc1]: https://github.com/jgpelletier/jsc-job-search-pipeline/compare/v0.1.0...v0.2.0-rc1
[0.1.0]: https://github.com/jgpelletier/jsc-job-search-pipeline/releases/tag/v0.1.0
