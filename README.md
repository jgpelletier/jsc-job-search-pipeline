# AI-Native Job Search Operating System

A personal AI agent that runs your job search like a sales pipeline — screenshot intake, automated research, fit scoring, differentiated cover letters, contact identification, and a SQLite CRM tracking every interaction.

Built for senior PMs and knowledge workers who want to run a high-volume, measurable search without losing context between sessions.

---

## The Architecture

Most AI job search tools are chatbots with memory. This is different.

The design follows a finding popularized by Vercel's engineering team: **passive context that is always loaded outperforms on-demand skill retrieval**, because it eliminates the agent's decision point. All judgment logic — fit scoring, voice rules, approval gates — lives in one always-present file. Skills become thin output templates. A SQLite database becomes the CRM backbone.

Three layers:

| Layer | File | What it does |
|-------|------|-------------|
| **Context + behavior** | `CLAUDE.md` | All judgment logic, agent guardrails, approval gates, workflow sequencing — always in scope |
| **Personal facts** | `references/*` | Your resume, CMF, must-haves/must-nots, verified work stories |
| **Skills** | `skills/*/SKILL.md` | Output templates for each pipeline stage |
| **Database** | `pipeline.db` | Companies, roles, contacts, applications, activity log |

---

## Quickstart

**Prerequisites:** [Claude Code](https://claude.ai/code), Python 3.x

```bash
# 1. Clone and initialize
git clone https://github.com/yourhandle/job-search-pipeline
cd job-search-pipeline
python3 db/init_db.py

# 2. Fill in your personal context
# Edit references/resume.md   — your master resume
# Edit references/cmf.md      — your Candidate Market Fit
# Edit references/mnookin.md  — your must-haves and must-nots
# Add files to references/stories/  — verified work stories (one per major achievement)

# 3. Drop screenshots → process inbox
# Screenshot a job posting → drag to inbox/
# Tell Claude Code: "process my inbox"
```

Open the project in Claude Code. The agent reads `CLAUDE.md` and `references/*` on every turn — no setup prompts needed.

---

## The Pipeline

### Three ways roles enter

**Screenshot drop** — see a posting anywhere, screenshot it, drop in `inbox/`. Tell Claude Code "process my inbox." Agent reads each image, extracts the JD, scores fit, writes qualifying roles to the database, moves processed files to `inbox/processed/`.

**Periodic search** — "run a job search." Agent queries LinkedIn, Greenhouse, Lever, Ashby, and Wellfound using your target profile, deduplicates against existing pipeline, presents results in two tiers.

**Manual paste** — paste a JD directly. Agent scores immediately and adds to database if you say go.

### What happens after intake

```
Researching → Qualified → Outreach Drafted → Applied → Screening → Interviewing → Offer
```

Each stage has a skill:

| Skill | What it produces |
|-------|-----------------|
| `company-research` | Structured profile — product, culture, Glassdoor signals, outreach angle |
| `analyze-jd` | Technical fit score + culture fit score + alignment points + gaps |
| `score-fit` | Mnookin criteria assessment — must-haves, must-nots, interview questions |
| `find-contacts` | Tiered contact list with LinkedIn search queries for manual lookup |
| `draft-resume-bullets` | Tailored bullets anchored to your exact metrics — never fabricated |
| `draft-cover-letter` | Problem → proof → bridge structure. Quality gates. Under 300 words. |
| `draft-outreach` | Hook-required LinkedIn/email. Self-check runs before presenting draft. |
| `prep-interview` | Pulls the exact submitted materials and the verified stories that map to the role |

### Approval gates

A small set of actions require explicit confirmation before the agent executes:
- Finalizing any outreach message
- Finalizing a cover letter
- Submitting an application
- Disqualifying a role

Everything else — research, scoring, drafting — runs autonomously.

---

## Daily Operating Rhythm

```bash
# Morning queue — what needs attention today
python3 db/db.py action

# Full pipeline view
python3 db/db.py pipeline

# Funnel stats
python3 db/db.py stats
```

The `needs_action` view surfaces any role untouched for 5+ days or with a due date approaching. At 30+ simultaneous companies, this is what keeps things from going stale.

---

## Database Operations

```python
import db.db as db

# Read
db.show_pipeline()               # full pipeline
db.show_pipeline("Screening")    # filter by status
db.needs_action()                # daily queue
db.stats()                       # funnel counts
db.get_role(role_id)             # full detail + activity log
db.get_contacts(company_id)      # contacts + LinkedIn search queries
db.show_applications()           # all submitted applications
db.get_application(role_id)      # what was submitted — use before interviews

# Write
db.add_role(company_name, title, ...)
db.update_status(role_id, "Applied", next_action="...", next_action_due="...")
db.log_outreach(role_id, contact_name, channel="LinkedIn", message_summary="...")
db.log_response(role_id, contact_name, summary="...")
db.log_application(role_id, method="ATS Direct", resume_version="...", ...)
db.update_contact_linkedin(contact_id, linkedin_url)
db.disqualify(role_id, reason="...")

# Skill helpers (called by skills; keep schema knowledge inside db.py)
db.get_role_state_for_skill(role_id)          # pre-flight gate check
db.log_jd_analysis(role_id, tech_fit, culture_fit, file_path, ...)
db.log_culture_revision(role_id, culture_fit, file_path, ...)
db.log_company_research(role_id, file_path, ...)
db.log_find_contacts_run(role_id, file_path)

# Session notes (drives HANDOFF.md render)
db.add_session_note("decision",   "...", role_id=None)
db.add_session_note("completion", "...")
db.resolve_session_note(note_id, resolution="...")

# Render outputs (pipeline.md, HANDOFF.md regenerate from DB state)
db.render_all()
```

CLI shortcuts:

```bash
python3 db/init_db.py                # bootstrap (apply pending migrations)
python3 db/db.py render              # regenerate pipeline.md and HANDOFF.md
python3 db/db.py migrate             # apply pending migrations only
python3 db/db.py note decision "Comp band on Acme not confirmed"
```

---

## Cover Letter Design

The cover letter skill enforces a hard constraint: **it cannot produce a letter that could have been written for a different company.**

Structure (3 paragraphs, ≤300 words):
1. **Hook** — name the company's specific operational problem
2. **Proof** — one story, one metric, directly mapped to that problem
3. **Bridge + ask** — explicit connection and a specific close

Quality gates run before any draft is presented. If the opener starts with "I" or the proof paragraph has more than one story, it rewrites internally before showing you anything.

---

## Adapting This Framework

The framework is in `CLAUDE.md` and the skill files. The personal layer is `references/`.

To make this yours, only the personal layer needs to change:

- `references/resume.md` — your master resume in markdown
- `references/cmf.md` — your Candidate Market Fit (positioning, target scenarios, hard constraints, voice anchors)
- `references/mnookin.md` — your must-haves and must-nots
- `references/stories/` — one file per major work achievement, with verified metrics

Everything else — `CLAUDE.md`, the skills, the database — works without modification. The opinionated defaults (scoring rubric, voice rules, green/red flag language, approval gates) are reasonable starting points; tune them in `CLAUDE.md` as you learn what works for your search.

---

## File Structure

```
job-search-pipeline/
├── CLAUDE.md                          # all judgment logic, behavior, and guardrails
├── CHANGELOG.md                       # release history
├── HANDOFF.md                         # render output of pipeline.db (do not hand-edit)
├── pipeline.md                        # render output of pipeline.db (do not hand-edit)
├── pipeline.db                        # SQLite — single source of truth (created by init_db.py)
├── db/
│   ├── init_db.py                     # bootstrap: applies pending migrations
│   └── db.py                          # read/write operations + render functions
├── migrations/                        # versioned schema migrations (NNN-name.sql)
├── skills/
│   ├── intake-screenshot/SKILL.md     # processes inbox/ images
│   ├── job-search/SKILL.md            # periodic internet search
│   ├── analyze-jd/SKILL.md            # JD fit analysis
│   ├── company-research/SKILL.md      # company profile
│   ├── score-fit/SKILL.md             # Mnookin culture fit
│   ├── find-contacts/SKILL.md         # LinkedIn contact identification
│   ├── draft-resume-bullets/SKILL.md  # tailored bullets
│   ├── draft-cover-letter/SKILL.md    # differentiated cover letter
│   ├── draft-outreach/SKILL.md        # LinkedIn/email outreach
│   └── prep-interview/SKILL.md        # interview preparation
├── inbox/                             # drop screenshots here
│   └── processed/                     # processed screenshots archive
├── references/
│   ├── resume.md                      # your master resume
│   ├── cmf.md                         # Candidate Market Fit
│   ├── mnookin.md                     # must-haves and must-nots
│   ├── stories/                       # verified work stories
│   └── analyses/                      # per-role artifacts produced by the pipeline
├── docs/
│   └── analysis-checklist.md          # JD analysis hard/soft gates + scoring calibration log
└── tests/                             # stdlib-unittest coverage of migrations, render, skill helpers
```

---

## License

MIT. Fork it, adapt it, use it.

The only ask: if you build something materially different on top of this, consider writing up what you learned.
