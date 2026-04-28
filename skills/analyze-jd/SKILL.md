---
name: analyze-jd
description: Analyze a job description for the candidate. Use when the candidate pastes a JD, shares a posting URL, or asks to evaluate a role. All scoring logic is in CLAUDE.md — this file defines the output format only.
---

# Analyze Job Description — Output Template

All scoring criteria, fit logic, green/red flags, and rubrics are in CLAUDE.md.
Apply that logic to produce the following output.

## Before Running — Check Role State

Look up the role's pre-flight state via `db.get_role_state_for_skill`:

```python
import db.db as db
state = db.get_role_state_for_skill(role_id)
# state == {company, title, status, overall_fit, tech_fit, culture_fit,
#          next_action, disqualified, flagged, open_decisions}
```

**If `state["flagged"]` is True (next_action mentions "recommend close" or "caution"):**
Stop. Do not run analysis. Say:

> "id=X ([Company]) is currently flagged [recommend close / caution]. Run analyze-jd anyway, or should I close it?"

Wait for the candidate's explicit direction before proceeding.

**If `state["overall_fit"]` is not None:**
Note it before starting — you'll need it for the score revision gate after analysis.

## Required Inputs
- Job description text (or fetch from URL)
- Company name

## Pre-Analysis Gate

Before computing `overall_fit`, verify the four hard gates from `docs/analysis-checklist.md`.
These can be populated from the JD, from prior company-research output, or from the candidate directly.

| Gate | How to check |
|---|---|
| Remote / location status | Read the JD — "remote," "hybrid," or office location |
| Domain | JD or company description — confirm it's one of the candidate's target domains |
| PE-owned check | If company-research was run, use that result. If not, search "[Company] private equity OR PE-backed" |
| Must-not screen | Run the must-not list from CLAUDE.md against the JD and company profile |

**If any gate is missing, stop and surface it:**
> "Analysis gate: [field] not confirmed. Run company-research first, or provide this directly. Proceed anyway?"

Wait for the candidate's direction. Do not estimate or assume.

**If all four gates are populated, proceed.**
Note any missing soft gates (size, model, comp, leadership) in the Role Snapshot section — they don't block scoring but should be visible.

## Output

```
## JD Analysis: [Role Title] at [Company]

**Overall Fit: X/10** — [one-line verdict]

### Role Snapshot
- Title & level:
- Domain:
- Location/Remote:
- Comp: [if listed, otherwise "not listed — confirm before proceeding"]
- Level check: [Senior PM tier? Flag if below]

### Technical Fit: X/10
[2–3 sentences using scoring rubric from CLAUDE.md]

### Culture Fit: X/10
[2–3 sentences using must-have/must-not logic from CLAUDE.md]

### Top Alignment Points
1. [JD requirement] → [the candidate's specific experience + metric]
2. [JD requirement] → [the candidate's specific experience + metric]
3. [JD requirement] → [the candidate's specific experience + metric]

### Gaps
1. [Gap] — Severity: [dealbreaker / manageable / minor]
2. [Gap] — Severity: [dealbreaker / manageable / minor]

### Must-Not Flags
[List any confirmed must-nots from CLAUDE.md, or "None identified"]

### Recommendation
[Strong pursue / Pursue with eyes open / Weak fit / Don't pursue]
[2–3 sentences. If weak fit, say so directly.]

### Next Step
[What the candidate should do — proceed to score-fit, pass, research first, etc.]
```

## Output Persistence (Auto-Save)

After generating the JD analysis, automatically save it:

1. **Write markdown file** to `references/analyses/{role-id:03d}-{company-slug}-jd-{date}.md`
   - Slug convention: lowercase, hyphens, no special characters (e.g. `frontrowmd` not `frontrow-md`)
   - Include the full JD text at the bottom of the file

2. **Persist to the DB via `db.log_jd_analysis`** — handles previous_fit,
   the canonical fit formula (0.6·tech + 0.4·culture), and the analysis snapshot:

   ```python
   import db.db as db
   old, new, snapshot_id = db.log_jd_analysis(
       role_id     = role_id,
       tech_fit    = tech_fit,        # 1–10
       culture_fit = culture_fit,     # 1–10
       file_path   = f"references/analyses/{role_id:03d}-{slug}-jd-{date}.md",
       verdict     = "pursue",        # or "pass" or "research"
       fit_notes   = "[2-3 sentence summary]",
   )
   if old != new:
       # Present the change explicitly — never silently overwrite.
       print(f"Score updated: {old} → {new} (previous_fit saved)")
   ```

3. **Do not advance status.** Present the score and recommendation, then wait:
   > "Overall fit: X/10 — [verdict]. Move to Qualified and proceed to score-fit?"
   the candidate confirms before status changes.

4. **When a role closes** (offer, rejection, or withdrawn): update the scoring calibration log in
   `docs/analysis-checklist.md` — add a row with role, role_id, predicted score, and outcome.
   This table is how we detect if scoring is drifting over time.
