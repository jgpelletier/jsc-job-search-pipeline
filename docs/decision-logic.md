# Decision Logic

Fit scoring, must-have/must-not screening, language signals, transferable
skills. Read together with `references/mnookin.md` (the candidate's specific
must-haves and must-nots).

`CLAUDE.md` references this file from its session-start protocol — load it
on every session.

---

## Push back on poor fit — don't just execute

Before drafting materials for any role, run a quick fit check:
- Does this role require a must-have from `references/mnookin.md` that is missing?
- Does the JD contain a must-not signal?
- Is the company profile misaligned with the candidate's target profile (`references/cmf.md`)?

If fit is weak (score < 6/10), say so directly before proceeding.
Don't draft outreach for a role the candidate shouldn't be pursuing.

---

## Must-haves and must-nots

The candidate's specific must-haves and must-nots live in
`references/mnookin.md`. Read that file before scoring any role.

Read both representations:
- The narrative body (always loaded — has nuance and examples)
- The YAML frontmatter at the top — also accessible programmatically via
  `db.get_must_haves()` and `db.get_must_nots()`. Useful when you need to
  iterate the structured list rather than re-parsing prose.

Score each must-have as ✅ Present / ⚠️ Unclear / ❌ Missing.
A role with 3+ missing must-haves is a no-go regardless of title or comp.
Any confirmed must-not warrants a direct conversation with the candidate
before proceeding.

## Green flag language (JDs and Glassdoor)
- "Outcome-driven" / "measurable impact" / "data-informed"
- "Discovery" / "user research" / "JTBD"
- "Autonomy" / "ownership" / "end-to-end"
- "Engineering partnership" / "technical PM"
- "Learning culture" / "psychological safety"

## Red flag language (JDs and Glassdoor)
- "Fast-paced" with no mention of learning or reflection
- "Stakeholder management" as top responsibility
- "Requirements gathering" / "PM as coordinator"
- Heavy ceremony language without outcome measurement
- "Move fast" without "and measure things"

---

## Fit scoring rubric

**Technical fit (1–10):**
- 8–10: Strong overlap with the candidate's core domains and delivery patterns (see `references/cmf.md`)
- 6–7: Adjacent domain, transferable skills, manageable gaps
- 4–5: Weak overlap, significant ramp required
- 1–3: Wrong domain entirely

**Culture fit (1–10):**
- 8–10: Must-haves mostly ✅, no confirmed must-nots
- 6–7: Mixed signals, manageable, probe in interviews
- 4–5: Multiple ⚠️, 1–2 possible must-nots
- 1–3: Must-nots confirmed or must-haves mostly ❌

**Overall = 60% technical + 40% culture**
The canonical formula is enforced inside `db.log_jd_analysis` and
`db.log_culture_revision`. Skills do not recompute it.

- 8–10: Strong pursue
- 6–7: Pursue with eyes open, flag gaps
- 4–5: Weak fit, only if there is a specific reason
- 1–3: Don't pursue

---

## Transferable skills — what actually moves the score

"How you built it" transfers further than "how you learned it."

✓ High-transfer angles (domain-agnostic delivery evidence):
- Specific infrastructure or migration stories the candidate has shipped
- Systems they have designed with measurable outcomes attached
- Cross-system or multi-party diagnoses where they found the root cause and built the fix
- Enterprise / regulated work at volume, with verifiable metrics

✗ Low-transfer angles (methodology without delivery proof):
- Discovery methods, user research, frameworks — harder to transfer without domain credibility
- "I care about the problem" framing without a specific delivery story

The test before scoring a gap as "manageable": can the candidate tell a
specific delivery story (from `references/stories/`) that maps directly to
the JD requirement? If yes, raise technical fit. If the only bridge is
methodology or interest, keep it lower.
