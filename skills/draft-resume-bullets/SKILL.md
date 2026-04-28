---
name: draft-resume-bullets
description: Rewrite or generate resume bullets for the candidate tailored to a specific JD. Use when the candidate needs to tailor his resume or strengthen bullets for a role. All bullet logic, exact metrics, and quality rules are in CLAUDE.md — this file defines the output format only. Requires analyze-jd to have been run first.
---

# Draft Resume Bullets — Output Template

All bullet logic, exact metrics to use, voice rules, and quality checks
are in CLAUDE.md. Apply that logic here. Never fabricate metrics.

## Required Inputs
- JD or analyze-jd output in context
- Which roles/sections to focus on

## Output

```
## Resume Bullets: [Role Title] at [Company]

Tailored for: [Top 3 JD themes being addressed]

---

### Priority Bullets (lead with these)

**[Most relevant prior employer for this JD]**
• [Verb + what the candidate built + outcome + metric]
• [Verb + what the candidate built + outcome + metric]
• [Verb + what the candidate built + outcome + metric]

---

### Supporting Bullets
• [Bullet]
• [Bullet]

---

### Suggested Drops for This Role
[Bullets strong generally but less relevant here — be specific]

---

### Gap Note
[What the JD emphasizes that isn't well-covered + how to address it:
cover note, outreach framing, or honest acknowledgment]
```

## Quality Check Before Presenting
- All metrics trace to the exact values in CLAUDE.md
- No fabricated scope, inflated claims, or estimated numbers
- No buzzwords (leveraged, spearheaded, passionate)
- Each bullet readable in 5 seconds — impact is front-loaded
