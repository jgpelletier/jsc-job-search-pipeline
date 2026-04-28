# Analysis Readiness Checklist

Used by `analyze-jd` before computing `overall_fit`.
Hard gates block scoring. Soft gates are noted in output but do not block.

---

## Hard Gates — Must Be Populated Before Scoring

| Field | What "populated" means | Why it blocks |
|---|---|---|
| Remote / location status | "confirmed remote," "hybrid [city]," or "on-site [city]" — from JD | If the candidate requires remote or a specific location, this must be confirmed before scoring fit |
| Domain | One of the candidate's target domains (see `references/cmf.md`) — confirmed from JD or research | Domain mismatch is disqualifying |
| PE-owned check | "No PE signal found," "PE-owned: [firm name]," or "unknown — flagged" | PE-owned cost-cutting is a common must-not — confirm against `references/mnookin.md` |
| Must-not screen | Result documented — "None identified" is valid, but the check must be run | Gate must be checked, not skipped |

**Gate logic:**
- All 4 populated → proceed to scoring
- Any missing → surface the gap and stop:
  > "Analysis gate: [field] not confirmed. Run company-research first, or provide this directly. Proceed anyway?"
  Wait for the candidate's direction. Do not estimate or assume missing values.

---

## Soft Gates — Note If Missing, Do Not Block

| Field | What "populated" means |
|---|---|
| Company size / stage | Headcount range or funding series (e.g. "Series B, ~80 employees") |
| Business model | B2B/B2C, product vs. services, customer type |
| Comp | Listed range, or "not listed — confirm before proceeding" |
| Leadership signal | CPO or CEO name + one relevant background note |

For each missing soft gate, note it in the Role Snapshot section of the JD analysis output:
`[field]: Not researched — run company-research or provide directly`

---

## Scoring Calibration Log

Track predicted score vs. actual outcome to detect drift over time.
Update this table when a role closes (offer, rejection, or withdrawn).

### Applied / Outreach — Closed Outcomes

| Role | role_id | Predicted | Outcome | Notes |
|---|---|---|---|---|
| | | | | |

### Applied / Outreach — Outcome Pending

| Role | role_id | Predicted | Status | Notes |
|---|---|---|---|---|
| | | | | |

### Correctly Passed (Low Score — Not Pursued)

These confirm the lower bound of the score is working. Not hiring outcomes — calibration that the floor is set right.

| Role | role_id | Predicted | Reason for pass |
|---|---|---|---|
| | | | |

---

**Calibration target:** 8+ closed outcomes before adjusting scoring assumptions. Watch for patterns — consistent screen failures on scores ≥ 7.5 would suggest the scoring is optimistic on technical depth signals relative to what interviews actually surface.
