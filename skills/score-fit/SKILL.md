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

2. **Update culture_fit in DB** — save previous value if score changes:
   ```python
   import sqlite3
   import db.db as db
   conn = sqlite3.connect('pipeline.db')
   old = conn.execute('SELECT overall_fit, culture_fit FROM roles WHERE id=?', (role_id,)).fetchone()
   new_overall = db.compute_overall_fit(tech_fit, new_culture_fit)  # canonical: db/db.py
   if old[0] != new_overall:
       conn.execute('UPDATE roles SET previous_fit=?, culture_fit=?, overall_fit=?, updated_at=datetime("now") WHERE id=?',
                    (old[0], new_culture_fit, new_overall, role_id))
       conn.commit()
       print(f"Score updated: {old[0]} → {new_overall} (previous_fit saved)")
   ```

3. **Log to database**:
   ```python
   import db.db as db
   db.log_analysis(
       role_id      = role_id,
       skill_type   = 'score-fit',
       file_path    = 'references/analyses/001-pano-ai-fit-score-2026-02-23.md',
       overall_fit  = new_overall,
       verdict      = 'pursue',  # or 'pass' or 'research'
       tool         = 'claude-code'
   )
   ```

4. **Do not advance status.** Present verdict and wait for the candidate's go-ahead before moving to Qualified or later stages.
