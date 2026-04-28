---
name: intake-screenshot
description: Process job posting screenshots dropped into the inbox/ folder. Use when the candidate says "process my inbox", "check the folder", "I dropped some screenshots", or when new images appear in inbox/. Reads each image, extracts job details, scores fit using CLAUDE.md logic, writes to pipeline.db, and moves processed files to inbox/processed/.
---

# Intake Screenshot — Output Template

All fit scoring logic and voice rules are in CLAUDE.md.
Database operations use db/db.py.

## Step 1: Enumerate All Files First

```bash
ls inbox/ | grep -Ev "^processed$"
```

**Before reading any images:**
- Print the full filename list — every file, exactly as it appears
- Count them
- State the count explicitly: "Found N files to process:"
  ```
  1. Screenshot 2026-02-23 at 9.00.14 PM.png
  2. Screenshot 2026-02-23 at 9.00.28 PM.png
  ...
  ```

Do not begin reading until the full list is printed. the candidate can catch unexpected files before any processing starts.

## Step 2: For Each Image — Log Filename First, Then Extract

**The filename is ground truth. Write it before anything else.**

For each file, process in this exact order:

1. **Note the exact filename** — this is the `source_file` that will be written to the DB
2. **Company name** — read from the top of the screenshot (header, logo text, URL bar). Literal text only — never infer from JD body content. If you cannot read it with confidence, write `[UNREADABLE — flag for manual review]`.
3. **Role title** — exact text from the posting
4. **Location / remote policy**
5. **Compensation** (if visible)
6. **Posting URL** (if visible in URL bar)
7. **Top 5–7 requirements** from the JD body
8. **Seniority signals** (scope, years, IC vs manager language)

Job postings on LinkedIn, Greenhouse, Lever, and Ashby always display the company name prominently at the top of the screenshot (in the header, logo area, or URL bar). Read it directly.

**If company name is [UNREADABLE]:** Stop. Do not write to the DB. Flag the file in the summary and ask the candidate to identify the company before proceeding.

If company is confirmed but ambiguous (two companies could match): run a quick web search to identify. Do not guess.

## Step 3: Score Fit

Using scoring rubric from CLAUDE.md:
- Technical fit: X/10
- Culture fit: X/10 (from JD language only — flag if more research needed)
- Overall: X/10
- Level check: Senior PM tier? Flag anything below.

## Step 4: Write to Database

For roles scoring 6+ AND Senior PM tier:

```python
import db.db as db
role_id = db.add_role(
    company_name  = "[extracted]",
    title         = "[extracted]",
    url           = "[extracted or None]",
    source        = "screenshot",
    source_file   = "[exact filename, e.g. 'Screenshot 2026-02-23 at 9.00.14 PM.png']",
    tech_fit      = X,
    culture_fit   = X,
    overall_fit   = X,
    remote        = "[remote/hybrid/onsite]",
    jd_text       = "[full extracted text]",
    fit_notes     = "[2-3 sentence summary]",
    next_action   = "Run company-research",
    next_action_due = "[date 2 days out]"
)
```

For roles below 6 or below Senior PM tier — still add with disqualify:

```python
role_id = db.add_role(company_name=..., title=..., source="screenshot",
                      source_file="[filename]", overall_fit=X)
db.disqualify(role_id, reason="[fit <6 / below senior level / wrong domain]")
```

## Step 5: Move Processed File

```bash
mv inbox/[filename] inbox/processed/[filename]
```

## Step 6: Self-Check Before Printing Summary

Before reporting results, verify:
- [ ] Every file in the original list from Step 1 has an entry (added, screened, or flagged)
- [ ] No file was silently skipped
- [ ] Every added role has a company name that was read directly from the screenshot (not inferred from JD content)
- [ ] Every added role has `source_file` set to the exact filename
- [ ] Any file where company name was uncertain is listed as `[UNREADABLE — awaiting candidate identification]` and NOT written to the DB

If any file is unaccounted for: re-read it before reporting.

## Step 7: Print Summary

After processing all files:

```
## Inbox Processed — [date]

[n] files found
[n] added to pipeline (6+, Senior PM tier)
[n] screened out — [reasons]
[n] flagged — company name unreadable, candidate identification needed

Roles added:
- [filename] → [Role] at [Company] — fit X/10 → Run company-research
- ...

Screened out:
- [filename] → [Role] at [Company] — [reason]

Flagged (company unreadable — do not process until the candidate confirms):
- [filename] — [what was visible in the screenshot]
```

**Include the filename in every summary line.** This makes it trivial to cross-reference a result against the original screenshot.

Then: `db.needs_action()` to show the candidate what requires immediate attention.

## On Verbal Timestamp Corrections

If the candidate corrects a filename verbally (e.g. "9.05.036"), echo back the full filename before updating the DB:

> "Confirming: `Screenshot 2026-02-23 at 9.05.36 PM.png` — is that correct?"

Timestamps like "9.05.036" are ambiguous (9:05:03 vs 9:05:36). Always confirm the exact filename match before committing.
