---
name: company-research
description: Build a structured company profile for the candidate's job search. Use when the candidate names a target company, asks "what do you know about X", or needs background before outreach or an interview. Fetches current info and frames it through the candidate's fit lens from CLAUDE.md.
---

# Company Research — Output Template

Use web search to find current information. All fit logic is in CLAUDE.md.

## Search Queries to Run
- "[Company] product overview site:company.com"
- "[Company] funding 2024 2025"
- "[Company] engineering blog OR product blog"
- "[Company] glassdoor reviews"
- "[Company] senior PM OR principal PM jobs"
- "[Company] email format site:rocketreach.co OR site:leadiq.com"

## Output

```
## Company Research: [Company Name]
Research date: [today] | Role context: [if known]

### The Quick Take
[3–4 sentences: what they do, who buys it, why it matters for the candidate's search]

### Business Profile
- Founded / Size / Stage:
- Business model:
- Primary customers:
- Revenue signals: [ARR, logos, customer count if public]
- Regulatory context: [HIPAA, SOC2, regulated industry?]
- Email format: [e.g. first.last@domain.com — cite source: RocketReach / LeadIQ / Hunter]

### Product
- Core product: [plain English]
- Key workflows:
- AI/data component: [central / adjacent / absent]
- Technical complexity signals: [API-first? Integrations? Data volume?]

### Team & Culture Signals
- Leadership: [CEO/CPO background]
- Glassdoor: [overall rating + 2–3 patterns from recent reviews]
- Growth trajectory: [hiring / stable / contracting]
- Any public engineering or product culture signals

### Recent News
- [Most relevant item]
- [Second item]
- [Third item]

### the candidate's Fit Analysis
Why this could be right: [2–3 specific reasons grounded in his background]

Questions to probe in interviews:
1. [Specific question about ownership/process]
2. [Specific question about AI/data depth]
3. [Specific question about culture/management]

Red flags: [Or "None identified"]

### Outreach Angle
[1–2 sentences: the specific, non-generic reason the candidate would reach out here.
What shared context or product detail makes the connection authentic?]
```

## Output Persistence (Auto-Save)

After generating the company research, automatically save it:

1. **Write markdown file** to `references/analyses/{role-id:03d}-{company-slug}-company-{date}.md`
2. **Log to database** via `db.log_company_research`:
   ```python
   import db.db as db
   db.log_company_research(
       role_id   = role_id,
       file_path = f"references/analyses/{role_id:03d}-{slug}-company-{date}.md",
       verdict   = "research",   # or "pursue" if clear go
   )
   ```

No user confirmation required.
