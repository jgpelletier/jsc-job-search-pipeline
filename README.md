# AI-Native Job Search Operating System

A personal AI agent that runs your job search like a sales pipeline — screenshot intake, automated research, fit scoring, differentiated cover letters, contact identification, and a SQLite CRM tracking every interaction.

Built for senior PMs and knowledge workers who want to run a high-volume, measurable search without losing context between sessions.

---

## The Architecture

Most AI job search tools are chatbots with memory. This is different.

**Passive context that is always loaded outperforms on-demand skill retrieval** — it eliminates the agent's decision point. All judgment logic — fit scoring, voice rules, approval gates — lives in one always-present file. Skills become thin output templates. A SQLite database becomes the CRM backbone.

Four layers:

| Layer | File | What it does |
|-------|------|-------------|
| **Context + behavior** | `CLAUDE.md` | All judgment logic, agent guardrails, approval gates, workflow sequencing — always in scope |
| **Personal facts** | `references/*` | Your resume, CMF, must-haves/must-nots, verified work stories |
| **Skills** | `skills/*/SKILL.md` | Output templates for each pipeline stage |
| **Database** | `pipeline.db` | Companies, roles, contacts, applications, activity log |

**Why SQLite over flat-file markdown:** A markdown CRM is readable by the agent, but it can't answer "what roles have gone five days without contact?" without scanning everything. SQLite gives you the `needs_action` view, deduplication on intake, and transactional writes that don't corrupt state mid-session. The tradeoff is opacity — `db.py` exists so you never need a SQL client.

**HANDOFF.md** is the session continuity mechanism. At the end of every working session the agent overwrites it with current pipeline state, open decisions, and exact next action per role. The next session reads it before doing anything else. This is how context survives across sessions without the agent reconstructing state from scratch — or hallucinating it.

---

## Quickstart

**Prerequisites:** [Claude Code](https://claude.ai/code), Python 3.x

```bash
git clone https://github.com/yourhandle/job-search-pipeline
cd job-search-pipeline
claude   # or open the folder in the desktop app
```

In your first conversation, say:

> **help me set this up**

The `setup` skill detects a missing `pipeline.db`, asks before running `python3 db/init_db.py`, then interviews you — paste your resume, walk through three work stories, name your must-haves and must-nots, confirm your positioning. It writes the four files in `references/` that the agents read every turn. Takes 15–25 minutes.

Prefer to configure by hand? Run `python3 db/init_db.py`, then edit `references/resume.md`, `references/cmf.md`, `references/mnookin.md`, and add story files to `references/stories/` directly. The worked example in `references/example/` shows what each one looks like filled in.

Once setup is done:
- Drop a job posting screenshot into `inbox/` and say "process my inbox"
- Or paste a JD in chat and say "score this role"
- Or say "run a job search" to seed the pipeline from scratch

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

## Testing

The database layer has a small stdlib test suite — no dependencies, runs in under a second.

```bash
python3 -m unittest tests.test_db
```

What it covers: schema completeness (every column the code writes to exists in the schema), `db.verify()` correctness on empty and drifted databases, `add_role` deduplication, and disqualified-role filtering. The schema-completeness test is the highest-leverage one — if you fork this and add a column to a write path, the test will fail until you also update `db/init_db.py`.

The skills, `CLAUDE.md`, and `references/*` are prompts and personal context, not code, and are intentionally not unit-tested.

---

## File Structure

```
job-search-pipeline/
├── CLAUDE.md                          # all judgment logic, behavior, and guardrails
├── HANDOFF.md                         # session-state file, recreated each session
├── pipeline.md                        # human-readable pipeline overview
├── pipeline.db                        # SQLite — single source of truth (created by init_db.py)
├── db/
│   ├── init_db.py                     # run once to create pipeline.db
│   └── db.py                          # all read/write operations
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
└── docs/
    └── analysis-checklist.md          # JD analysis hard/soft gates + scoring calibration log
```

---

## License

MIT. Fork it, adapt it, use it.

The only ask: if you build something materially different on top of this, consider writing up what you learned.
