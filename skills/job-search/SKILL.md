---
name: job-search
description: Search the internet for Senior PM and Principal PM roles matching the candidate's profile. Use when the candidate asks to "run a search", "find new jobs", "what's out there", or on any periodic basis. All fit criteria and target profile are in CLAUDE.md. Deduplicates against pipeline.db before adding. Writes results to database and logs the search run.
---

# Job Search — Output Template

All fit criteria, target role profile, and scoring logic are in CLAUDE.md.
Database operations use db/db.py. Check pipeline.db for duplicates before adding.

## Step 1: Load Existing Pipeline (for deduplication)

```python
import db.db as db
db.show_pipeline()
```

Note all company names currently tracked — skip duplicate companies unless different role.

## Step 2: Run Search Queries

Build queries from the candidate's `references/cmf.md` — use their target titles, target scenarios, and hard constraints. Generate three to five query variations covering:

**Title + domain** — combine the candidate's target titles with their domain keywords and remote/location requirement.

**Company-targeted (careers pages of active pipeline targets):**
```python
# Pull companies in Researching status to check their job boards
db.show_pipeline(status="Researching")
```

**Domain-targeted** — narrower queries built from specific domain terms in the candidate's CMF (regulatory frameworks, technical patterns, industry verticals).

Fetch promising job board pages with web_fetch for full JD text.

## Step 3: Score Each Result

For each role found, apply fit scoring from CLAUDE.md:
- Technical fit (1–10)
- Culture fit from JD language (1–10)
- Overall (60/40 weighted)
- Level check: Senior PM tier?
- Duplicate check: already in pipeline.db?

## Step 4: Fetch JD Text (required before writing to DB)

**For every qualifying role, fetch the full JD text from the specific posting URL before adding to DB.**
Do not add a role with a blank `jd_text` — that breaks `analyze-jd` downstream.

```
# For each promising result:
# 1. Identify the specific posting URL (Lever, Greenhouse, Ashby, Workday, LinkedIn — not a jobs homepage)
# 2. WebFetch that URL and extract full JD text
# 3. If WebFetch returns 404 or empty:
#    - Try a job board mirror (remotive.com, wellfound.com, ycombinator.com/jobs, linkedin.com/jobs)
#    - If still not found: add role but set next_action="VERIFY OPEN: JD text not captured — confirm posting live"
#    - Log fit_notes: "Posting URL [url] returned 404 on [date] — verify before analyzing"
```

**Write to Database only after JD text is in hand:**

```python
role_id = db.add_role(
    company_name    = "[name]",
    title           = "[title]",
    url             = "[specific posting URL — not company jobs homepage]",
    source          = "search",
    tech_fit        = X,
    culture_fit     = X,
    overall_fit     = X,
    remote          = "[remote/hybrid/onsite]",
    jd_text         = "[full extracted JD text from WebFetch]",
    fit_notes       = "[2-3 sentence fit summary]",
    next_action     = "Run company-research",
    next_action_due = "[date 2 days out]",
    company_domain  = "[domain]",
    company_stage   = "[stage if known]"
)
```

**Below threshold — add and immediately disqualify:**

```python
role_id = db.add_role(company_name=..., title=..., source="search", overall_fit=X)
db.disqualify(role_id, "[fit <6 / below senior / wrong domain / consumer]")
```

**Log the search run:**

```python
db.log_search_run(
    queries_run    = N,
    roles_found    = N,
    roles_added    = N,
    roles_duped    = N,
    roles_screened = N,
    notes          = "[any observations about the market]"
)
```

## Step 5: Present Results

```
## Job Search — [date]
Queries: N | Found: N | Added: N | Dupes: N | Screened: N

### Strong Matches (8–10)
[Role] at [Company] — fit X/10
URL: [link]
Why: [2 specific reasons tied to the candidate's background]
Gap: [1 honest concern]
→ Run company-research

### Worth a Look (6–7)
[Role] at [Company] — fit X/10
URL: [link]
Interesting: [1-2 sentences]
Uncertain: [1-2 sentences]
→ the candidate's call

### Screened Out
[Company] — [Role] — [Reason]
```

Then: `db.needs_action()` to show full pipeline priority view.

## Search Cadence
- Weekly: title + domain queries, active pipeline company career pages
- Bi-weekly: domain-targeted queries, Wellfound for new Series B/C
- Monthly: broader sweep (Staff PM, Group PM, Product Lead adjacent titles)
