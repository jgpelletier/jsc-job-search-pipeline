---
name: prep-interview
description: Activate when an interview is scheduled. Pulls the application record, maps JD competencies to verified stories, generates delivery scripts, and produces a one-page prep sheet. Use when the candidate says "I have an interview" or "interview scheduled."
---

# Interview Prep — Activation Template

## Inputs Required

Before running, confirm:
- `role_id` — the DB id for the role
- `interview_type` — phone screen / hiring manager / panel / executive
- `interviewer` — name and title if known
- `date` — when the interview is scheduled

---

## Step 1 — Pull the Application Record

Run `db.get_application(role_id)`.

Retrieve:
- Which resume version was submitted
- Which bullets were used (`resume_bullets_used`)
- Any notes logged at application time

If no application record exists, ask the candidate which resume was sent before proceeding.

---

## Step 2 — Pull JD Competencies

Read the JD fit file for this role from `references/analyses/`.
Identify the top 3 competencies the role cares about most.

Common competency signals to look for:
- "lead cross-functional teams" → leadership / influence without authority
- "translate user workflows" → analytical / structured thinking
- "own end-to-end product lifecycle" → execution / ownership
- "navigate ambiguity / greenfield" → judgment / prioritization
- "data-driven" → analytical / metrics fluency
- "work directly with customers / health systems" → communication / discovery

---

## Step 3 — Map Competencies to Verified Stories

Read `references/stories/` — use verified files only (check Status field).
Do not reconstruct facts from memory or from resume bullets alone.
If a story is unverified, flag it before using it.

Select the 3-5 most relevant stories for this interview.

For each story, generate three delivery layers:

### 30-second version
Result first → what I did → context.
Spoken, not read. No hedging. Lead with the outcome.

### 3-minute version
Situation (brief) → my specific contribution → constraints I navigated →
trade-offs I made → outcome → what I'd do differently.
Business-first framing throughout.

### Deep-dive (if they ask "tell me more")
Additional technical or organizational detail. Team dynamics.
What engineering built vs. what I designed. Lessons learned.

---

## Step 4 — Flag High-Probability Asks

Cross-reference `resume_bullets_used` from the application record against the
story files. Any bullet that maps directly to a verified story = high-probability
interview ask. Flag these first — they're what the interviewer already read.

---

## Step 5 — Culture Probe Questions

Pull company research from `references/analyses/` for this role.
Generate 3 culture probe questions based on known signals:
- Glassdoor themes (management, autonomy, WLB)
- Leadership flags (instability, PE ownership, recent restructuring)
- Role structure concerns (backfill vs. new headcount, builder vs. order-taker)

---

## Step 6 — Questions to Ask the Interviewer

Generate 3 questions specific to this company and role. Not generic.
Anchor to the JD, company research, and any open questions from HANDOFF.md.

Good question types:
- What does success look like in the first 90 days?
- How does the PM team own discovery vs. execute a defined backlog?
- What changed about this team / role in the last 12 months?

---

## Step 7 — One-Page Prep Sheet

Output a single prep sheet structured as:

```
INTERVIEW PREP — [Company] | [Role] | [Date]
Interviewer: [Name, Title]
Type: [Phone screen / HM / Panel / Executive]

TOP 3 STORIES
1. [Story name] — [30-second version]
   Competency: [tag] | High-prob ask: [yes/no]

2. [Story name] — [30-second version]
   Competency: [tag] | High-prob ask: [yes/no]

3. [Story name] — [30-second version]
   Competency: [tag] | High-prob ask: [yes/no]

CULTURE PROBES
- [Question 1]
- [Question 2]
- [Question 3]

QUESTIONS TO ASK
- [Question 1]
- [Question 2]
- [Question 3]

OPEN FLAGS
[Anything unresolved — comp, role scope, team structure]
```

---

## Quality Gates

Before presenting the prep sheet, verify:
- [ ] All story facts trace to verified story files — no reconstructed metrics
- [ ] Delivery scripts lead with result, not with "I" or context
- [ ] At least one trade-off or constraint named per story
- [ ] Culture probes are specific to this company, not generic
- [ ] Questions to ask are not answerable from the JD alone

---

## Post-Interview

After the interview, log what was asked and what landed:

```python
db._log(conn, company_id=X, role_id=Y, type='note',
        detail='Interview [date]: asked about [topic]. Story [N] landed well.
                Weak on [area]. Follow-up needed on [open item].')
```

Advance status to Interviewing if still in Screening.
