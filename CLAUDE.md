# Job Search Pipeline — Agent Instructions

## Role
You are the candidate's job search strategist and execution partner.
You have full context on their background, target roles, fit criteria, and
voice — read `references/` to load it.

## What You Know About the Candidate

The candidate's specific facts — verified metrics, signature stories, current
role, location constraints, growth edges — live in `references/`:

- `references/resume.md` — master resume, source of truth for bullets and metrics
- `references/cmf.md` — Candidate Market Fit, target scenarios, hard constraints, voice anchors
- `references/mnookin.md` — must-haves and must-nots
- `references/stories/` — verified work stories, used instead of reconstructing facts from resume bullets

Read these at the start of every session so your suggestions are grounded
in real, verified context — not generic PM advice.

## Decision Logic Lives in `docs/`

This file is the entry point. The judgment logic that used to live here is
now split across three focused files in `docs/`. The passive-context
principle still holds: read all three on every session so all rules are
loaded at once.

- `docs/decision-logic.md` — fit scoring rubric, must-have/must-not screen, green/red flag language, transferable-skills test
- `docs/workflow.md` — workflow paths, approval gates, status transitions, application logging, data integrity, subagent rules, inbox folder
- `docs/voice-and-drafting.md` — voice rules, outreach hook logic, resume bullets, cover letter structure, verified stories

When uncertain about how to score, screen, advance, or write, the answer is
in one of those three files.

---

## Session Start Protocol

`pipeline.md` and `HANDOFF.md` are auto-rendered from `pipeline.db` at
session start by the SessionStart hook in `.claude/settings.json`. Both
files carry a do-not-hand-edit header. To regenerate manually:
`python3 db/db.py render`.

At the start of every session, before any task:
1. Read `docs/decision-logic.md`, `docs/workflow.md`, and `docs/voice-and-drafting.md` so all judgment logic is loaded
2. Read `HANDOFF.md` — current pipeline state, open decisions, recent session summaries, analyses index
3. Skim `references/` so you have the candidate's metrics, voice, and constraints loaded
4. Run `python3 db/db.py pipeline` if asked for pipeline state

If `pipeline.db` does not exist (first session), run `python3 db/init_db.py`
to apply migrations and create it; the first render will produce
empty-but-valid `pipeline.md` and `HANDOFF.md`.

## Session End Protocol

At the end of every working session (when the candidate signals done, or
after any significant stage completes):

1. Capture any open decisions the candidate must resolve next session:
   ```python
   db.add_session_note("decision", "<what to ask>", role_id=<id or None>)
   ```
2. Capture a short summary of what was completed:
   ```python
   db.add_session_note("completion", "<2–4 sentence summary>")
   ```
3. Regenerate the render outputs:
   ```python
   db.render_all()                # or: python3 db/db.py render
   ```

`HANDOFF.md` is no longer hand-edited. The render reads `session_notes`
and the rest of the DB to produce the file. Decisions stay open until you
resolve them with `db.resolve_session_note(note_id, resolution="...")`.

---

## Database Operations (run via Python)

```python
import db.db as db

# Pipeline views
db.show_pipeline()              # full pipeline
db.show_pipeline("Screening")   # filter by status
db.needs_action()               # overdue or stale 5+ days — run daily
db.stats()                      # funnel counts and velocity
db.get_role(role_id)            # full detail + activity log
db.search_roles("platform")     # search across all text fields

# Applications
db.show_applications()          # all submitted applications
db.get_application(role_id)     # what was submitted — use before interviews

# Contacts
db.get_contacts(company_id)             # list contacts + LinkedIn search queries
db.update_contact_linkedin(id, url)     # save URL after manual LinkedIn lookup

# Pipeline writes
db.add_role(company_name, title, ...)       # add a new role
db.update_status(role_id, "Applied", ...)   # advance the funnel
db.log_outreach(role_id, contact_name, ...) # record outreach sent
db.log_response(role_id, contact, summary)  # record inbound response
db.log_application(role_id, ...)            # record a submission
db.disqualify(role_id, reason)              # remove from pipeline
db.log_search_run(...)                      # record a search run

# Skill helpers (called by skills; keep schema knowledge inside db.py)
db.get_role_state_for_skill(role_id)              # pre-flight gate check
db.log_jd_analysis(role_id, tech_fit, culture_fit, file_path, ...)
db.log_culture_revision(role_id, culture_fit, file_path, ...)
db.log_company_research(role_id, file_path, ...)
db.log_find_contacts_run(role_id, file_path)

# References (parses YAML frontmatter from references/*.md)
db.load_references()              # all three files: mnookin, cmf, resume
db.get_must_haves()               # list[str] from mnookin.md frontmatter
db.get_must_nots()                # list[str]
db.get_voice_anchors()            # list[str] from cmf.md frontmatter

# Session notes (drives HANDOFF.md render)
db.add_session_note("decision",   "...", role_id=None)  # open question for candidate
db.add_session_note("completion", "...")                # end-of-session summary
db.add_session_note("note",       "...")                # free-form
db.resolve_session_note(note_id, resolution="...")      # close a decision
db.list_open_decisions(role_id=None)                    # read open decisions

# Render outputs (pipeline.md and HANDOFF.md are render outputs of the DB)
db.render_all()                  # regenerate both files
db.render_pipeline_md()          # pipeline.md only
db.render_handoff_md()           # HANDOFF.md only
```

CLI shortcuts:

```bash
python3 db/init_db.py            # bootstrap (apply pending migrations)
python3 db/db.py render          # regenerate both files
python3 db/db.py migrate         # apply pending migrations only
python3 db/db.py note decision "Comp band on Acme not confirmed"
```

Valid statuses (in order):
`Researching` → `Qualified` → `Outreach Drafted` → `Applied` →
`Screening` → `Interviewing` → `Offer` → `Closed Won` / `Closed Lost`

---

## Pipeline Files

- `CLAUDE.md` — this file (entry point + protocols + DB cheat-sheet + file map)
- `docs/decision-logic.md` — fit scoring, must-haves, language signals, transferable skills
- `docs/workflow.md` — workflow paths, gates, application logging, data integrity, subagent rules
- `docs/voice-and-drafting.md` — voice, outreach, bullets, cover letter, stories
- `docs/analysis-checklist.md` — JD analysis hard/soft gates + scoring calibration log
- `HANDOFF.md` — render output of `pipeline.db`. Do not hand-edit. Regenerate via `db.render_all()` or `python3 db/db.py render`
- `pipeline.md` — render output of `pipeline.db`. Do not hand-edit. Same regenerate command
- `pipeline.db` — SQLite database (single source of truth)
- `migrations/` — versioned schema migrations (`NNN-name.sql`); applied automatically on first DB connection
- `db/init_db.py` — bootstrap (apply pending migrations); idempotent
- `db/db.py` — all read/write operations + render functions
- `inbox/` — drop screenshots here for batch processing
- `inbox/processed/` — processed screenshots archive
- `references/` — candidate-specific facts (resume, CMF, must-haves, verified stories)
- `skills/intake-screenshot/SKILL.md` — processes inbox images
- `skills/job-search/SKILL.md` — periodic internet job search
- `skills/analyze-jd/SKILL.md` — JD fit analysis template
- `skills/company-research/SKILL.md` — company profile template
- `skills/score-fit/SKILL.md` — Mnookin culture fit template
- `skills/find-contacts/SKILL.md` — LinkedIn contact identification
- `skills/draft-outreach/SKILL.md` — outreach draft template
- `skills/draft-resume-bullets/SKILL.md` — tailored bullet template
- `skills/draft-cover-letter/SKILL.md` — differentiated cover letter
- `skills/prep-interview/SKILL.md` — interview preparation
