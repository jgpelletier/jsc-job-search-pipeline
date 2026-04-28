# Workflow, Gates, and Data Integrity

How roles move through the pipeline, what requires the candidate's go-ahead,
how applications get logged, and the rules that keep `pipeline.db` honest.

`CLAUDE.md` references this file from its session-start protocol — load it
on every session.

---

## Workflow Sequence

**Intake path (screenshot dropped into `inbox/`):**
1. `intake-screenshot` → extract JD, score fit, write to `pipeline.db`
2. Candidate reviews summary → go/no-go per role
3. If go: `company-research` + `find-contacts` (run together)
4. `analyze-jd` → full fit score
5. `draft-resume-bullets` → `draft-cover-letter` → `draft-outreach`
6. Candidate approves all materials before anything goes out
7. `db.log_application()` after submitting — captures resume version + cover letter used
8. `db.log_outreach()` after sending outreach
9. `db.update_status()` at each funnel stage

**Search path (periodic internet search):**
1. `job-search` → find new roles, deduplicate against `pipeline.db`, write results
2. Present strong matches + worth-a-look list
3. Candidate selects which to pursue → `company-research` + `find-contacts` on selected

**Manual path (candidate pastes a JD directly):**
1. `analyze-jd` → fit score + recommendation
2. `db.add_role()` if proceeding
3. `company-research` + `find-contacts`
4. `draft-resume-bullets` → `draft-cover-letter` → `draft-outreach`

Valid statuses (in order):
`Researching` → `Qualified` → `Outreach Drafted` → `Applied` → `Screening`
→ `Interviewing` → `Offer` → `Closed Won` / `Closed Lost`

---

## Approval Gates

### Always requires explicit confirmation:

- Sending or finalizing any outreach message
- Finalizing a cover letter
- Submitting an application
- Marking a company as "not pursuing"
- Any task that involves real contact with a real person

### Workflow stage gates — check role state before running any skill:

| Role state | Permitted without confirmation | Requires go-ahead first |
|------------|-------------------------------|-------------------------|
| Recommend-close (agent flagged) | `disqualify()` only | Override to pursue → candidate says "keep it" |
| Caution — decision pending | company-research only | "Proceed" or "pursue" → then analyze-jd |
| Active / pursuing | Full workflow | Standard gates above |

Use `db.get_role_state_for_skill(role_id)` to check `flagged` and `disqualified`
before running `analyze-jd` or later skills. Running them on a recommend-close
or caution role without explicit direction is a gate violation.

### Status transition gate:

Status advances (Researching → Qualified → Applied) are not automatic.
After completing analyze-jd, present the score and recommendation — then
wait for the candidate to say "pursue" before moving status forward. Do not
self-advance status based on fit score alone.

### Fit score revision gate:

If a role already has `overall_fit` in the DB and new analysis produces a
different number:
- State the change explicitly: "Current score: X.X → New analysis: Y.Y. Update?"
- Do not overwrite silently
- `db.log_jd_analysis` and `db.log_culture_revision` automatically save
  `previous_fit` and write a `score_revision` entry to the activity table.
  Don't bypass them.

---

## Application Logging

After every submission, log immediately — interview prep depends on knowing
exactly what was submitted:

```python
db.log_application(
    role_id              = [id],
    method               = "LinkedIn Easy Apply" | "ATS Direct" | "Email" | "Referral",
    resume_version       = "[label — e.g. 'platform-pm v2']",
    resume_bullets_used  = "[paste the actual bullets submitted]",
    cover_letter_used    = "[paste the actual cover letter submitted]",
    ats_url              = "[link to application portal]",
    ats_name             = "[Greenhouse / Lever / Workday / etc.]",
    confirmation_code    = "[if provided]",
    screening_questions  = "[Q: ... A: ... for any application questions answered]"
)
```

To retrieve before an interview:
```python
db.get_application(role_id)   # shows exactly what was submitted
```

---

## inbox/ Folder

The candidate drops job posting screenshots here for batch processing.
- New files: `inbox/*.png` / `*.jpg` / `*.webp`
- After processing: moved to `inbox/processed/`
- Multiple screenshots of the same role: merge before scoring

---

## Data Integrity Rules

These rules exist because hard deletes, silent filtering, and field
overwrites are hard to reverse and create audit gaps. The candidate needs
to trust that the DB reflects reality — not a cleaned-up version of it.

### Never hard-delete pipeline records
Roles and companies represent real work. Hard deletes lose that history
permanently.

- To remove a role from active consideration: use `db.disqualify(role_id, reason="...")`
- If a row is genuinely a phantom/artifact: log to the activity table
  first, then confirm before deleting:
  ```python
  # Log it before removing
  db._log(conn, company_id=X, role_id=Y, type="deleted",
          detail="Phantom artifact — [what it was, why it has no screenshot, why removing]")
  # Then delete only after the candidate confirms
  ```
- When in doubt: disqualify instead of delete. Disqualified rows stay
  visible with their reason.

### Log before overwriting key fields
Before changing `company_id`, `source_file`, `title`, `overall_fit`, or
`status` on an existing role, state the before/after explicitly in your
response:

> "Changing id=22 company from [old] → [new], source_file from [old] → [new]"

This gives a visible audit trail without requiring a full DB history query.

### Never filter silently
When running queries that filter out disqualified/screened roles, always
report what's hidden:

- "Showing 28 active roles — 8 screened/disqualified not shown"
- Never present a filtered view as if it's the complete picture
- The `pipeline` command already filters; remind the candidate of the count
  discrepancy if it comes up

### Confirm before any hard DELETE or multi-row UPDATE
These require explicit confirmation before executing, same as the Approval
Gates above. A disqualify operation (single role, reversible) can proceed
without confirmation when the candidate has clearly indicated the role
should be closed. A `DELETE FROM roles` statement or `UPDATE roles WHERE ...`
touching multiple rows requires confirmation first.

---

## Subagent Rules

Background research agents (launched via the Task tool) must NOT:
- Write to `HANDOFF.md` or `pipeline.md` — both are render outputs of
  `pipeline.db`. Edits will be overwritten on the next render and may be
  silently lost.
- Commit to `pipeline.db` beyond what is explicitly authorized for the
  specific task
- Create or modify any file unless explicitly tasked with writing that file

Background agents should return findings as text output only.
The main agent is responsible for all file writes and DB commits based on
those findings.

If a subagent has relevant summary information, it returns it as output —
the main agent decides whether to persist it via `db.add_session_note(...)`.
