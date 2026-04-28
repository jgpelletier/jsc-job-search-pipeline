---
name: score-fit
description: Score a role against the candidate's Mnookin fit criteria. Use after company-research or analyze-jd when a deeper culture/values assessment is needed. All must-have and must-not criteria are in CLAUDE.md — this file defines the output format only.
---

# Score Fit (Mnookin) — Output Template

All must-have criteria, must-not flags, green/red flag language,
and scoring rubric are in CLAUDE.md. Apply that logic here.

## Output

```
## Mnookin Fit Score: [Company] — [Role Title]

**Culture Fit: X/10** — [one-line verdict]

### Must-Haves

| Must-Have | Status | Evidence |
|-----------|--------|----------|
| End-to-end ownership | ✅/⚠️/❌ | [JD language or research signal] |
| Access to operational data | ✅/⚠️/❌ | |
| Coaching manager | ✅/⚠️/❌ | |
| Learning culture | ✅/⚠️/❌ | |
| Deep work / maker time | ✅/⚠️/❌ | |
| AI grounded in outcomes | ✅/⚠️/❌ | |
| Strategy + delivery connection | ✅/⚠️/❌ | |

Must-Have Score: X/7

### Must-Not Flags

| Must-Not | Status | Evidence |
|----------|--------|----------|
| Prescribed solutions | ✅/⚠️/❌ | |
| No evaluation path | ✅/⚠️/❌ | |
| Focus-killing bureaucracy | ✅/⚠️/❌ | |
| No autonomy/data | ✅/⚠️/❌ | |
| Coordination-only role | ✅/⚠️/❌ | |
| Blame/political culture | ✅/⚠️/❌ | |
| Control-oriented leadership | ✅/⚠️/❌ | |

Confirmed Must-Nots: X

### Green Flags Found
- [Flag] — [Source]

### Red Flags Found
- [Flag] — [Source]

### Interview Questions to Resolve Unclear Items
[For each ⚠️ item, one specific question to ask in interviews]

### Verdict
[2–3 sentences: should the candidate pursue based on culture fit? What's the biggest
risk? What needs to be confirmed?]
```

## Output Persistence (Auto-Save)

After generating the fit score, automatically save it:

1. **Write markdown file** to `references/analyses/{role-id:03d}-{company-slug}-fit-score-{date}.md`
   - Slug convention: lowercase, hyphens, no special characters (e.g. `frontrowmd` not `frontrow-md`)

2. **Persist to the DB via `db.log_culture_revision`** — reuses the existing
   `tech_fit`, recomputes `overall_fit` via the canonical formula, saves
   `previous_fit`, and writes the analysis snapshot:

   ```python
   import db.db as db
   old, new, snapshot_id = db.log_culture_revision(
       role_id     = role_id,
       culture_fit = new_culture_fit,   # 1–10, from must-have/must-not assessment
       file_path   = f"references/analyses/{role_id:03d}-{slug}-fit-score-{date}.md",
       verdict     = "pursue",          # or "pass" or "research"
       fit_notes   = "[1-2 sentence summary of the verdict]",
   )
   if old != new:
       print(f"Score updated: {old} → {new} (previous_fit saved)")
   ```

3. **Do not advance status.** Present verdict and wait for the candidate's go-ahead before moving to Qualified or later stages.
