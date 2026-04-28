---
name: draft-outreach
description: Draft LinkedIn or email outreach for the candidate's job search. Use when the candidate asks to reach out to someone at a target company. All voice rules, hook requirements, and self-check logic are in CLAUDE.md — this file defines the output format only. Always run the self-check from CLAUDE.md before presenting a draft.
---

# Draft Outreach — Output Template

All voice rules, hook requirements, and the self-check gate are in CLAUDE.md.
Apply that logic before presenting any draft.

## Required Inputs (ask if missing)
- Target person: name, title, company
- Platform: LinkedIn request / LinkedIn message / Email
- Hook: which of the 4 hook types from CLAUDE.md applies?
- Goal: connection / intro to role / informational / follow-up
- Email format: [if platform is Email — pull from company research file or look up via RocketReach / LeadIQ]

## Platform Constraints
- LinkedIn connection request: 300 characters max
- LinkedIn message: 4 short paragraphs max
- Email: 4–5 sentences, specific subject line

## Output

```
## Outreach Draft: [Person] at [Company]

Platform: [LinkedIn request / message / Email]
Goal: [What this achieves]
Hook used: [Which hook type + 1 sentence explaining the specific angle]
Email format: [first.last@domain.com — include if platform is Email]

Self-check:
- [ ] Specific to this person/company (not generic)
- [ ] Uses the candidate's actual work, not vague claims
- [ ] Clear, low-friction ask
- [ ] Sounds like the candidate (checked against voice rules in CLAUDE.md)

---

### Variant A — [Label, e.g. "Direct"]
[Draft]
[Character count if LinkedIn request]

---

### Variant B — [Label, e.g. "Warmer"] (include when tone choice is non-obvious)
[Draft]

---

### Notes
[Timing, context, suggested follow-up if no response in X days]
```

## Output Persistence (Auto-Save)

After generating outreach drafts, automatically save them:

1. **Write markdown file** to `references/analyses/{role-id}-{company-slug}-outreach-{date}.md`
   - Include all variants, self-check, hook rationale, and sequencing notes
2. **Log to database**:
   ```python
   import db.db as db
   db.log_analysis(
       role_id      = [role_id],
       skill_type   = 'draft-outreach',
       file_path    = 'references/analyses/004-gravie-outreach-2026-02-23.md',
       overall_fit  = None,
       verdict      = None,
       tool         = 'claude-code'
   )
   ```

No user confirmation required to save. Sending still requires the candidate's explicit approval.
File naming: `{role-id:03d}-{slug}-outreach-{date}.md`
