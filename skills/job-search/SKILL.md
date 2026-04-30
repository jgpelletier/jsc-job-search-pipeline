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

## Step 4: Verify the role is open, then fetch JD text (required before writing to DB)

**Drop the role if it is closed. Add the role only after canonical confirmation.**

The risk being managed: search engines and aggregator mirrors keep cached job pages live long after the role closes. A mirror's "open until [date]" is descriptive metadata from a snapshot, not a live signal. Acting on a mirror without canonical confirmation produces confidently-wrong "strong match" recommendations to closed roles.

### Canonical-page precedence rule

The canonical posting URL is the source of truth on open/closed status. The canonical URL is:
- The company's own ATS posting page — `*.greenhouse.io`, `jobs.lever.co`, `*.ashbyhq.com`, `*.workable.com`, `*.workday.com`, `*.myworkdayjobs.com`, `*.bamboohr.com`
- Or the company's own `careers` / `jobs` page if no ATS URL is available

**Mirrors are NOT canonical** — `remotive.com`, `wellfound.com`, `ycombinator.com/jobs`, `sportstechjobs.com`, `remoterocketship.com`, `weworkremotely.com`, LinkedIn job-clones, and any aggregator. Mirrors are useful for discovery, not for verification.

### Verification flow

For each qualifying role:

1. **Locate the canonical URL** — usually linked from the mirror's "Apply on company site" button, or by searching `"<role title>" site:greenhouse.io` / `site:lever.co` / `site:<company>.com/careers`.

2. **WebFetch the canonical URL** and check, in order:

   a. **HTTP error or redirect to a generic index** (404, 410, redirect to `/careers` with no role-specific content) → role is closed. Drop it. Note in summary as `[Company] [Role] — closed (canonical 404)`.

   b. **Page renders but the role is not on it** (e.g., the company's `/careers` page returns successfully but the specific role title and JD body are absent) → role is closed. Drop it.

   c. **Closure phrase present** in canonical page text — any of:
      - "no longer accepting applications"
      - "this position has been filled"
      - "this position is no longer available"
      - "this job has expired"
      - "this position is closed"
      - "we have filled this role"

      → role is closed. Drop it.

   d. **Canonical page returns full JD with apply form / Submit button** → role is open. Capture `jd_text` and proceed to write.

3. **If you cannot locate any canonical URL** (rare — usually means the company is too small to have an ATS and the only listing is on a mirror): do NOT promote to "Strong Match." Add with `next_action="VERIFY OPEN: only mirror data; canonical not located"` and surface to the candidate explicitly.

### Excluded-company check (closed-loop with CLAUDE.md)

Before writing the role: check `references/cmf.md` `current_employment` and `Excluded companies`. If the role's company matches, drop it and note `[Company] — excluded (matches cmf.md current/excluded)` in the summary. Never silently surface a role at the candidate's current employer or a company they have already excluded.

**Write to Database only after canonical confirmation:**

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
