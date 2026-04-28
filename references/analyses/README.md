# analyses/

Per-role artifacts produced by the pipeline. The skills (`company-research`, `analyze-jd`, `score-fit`, `draft-resume-bullets`, `draft-outreach`, `draft-cover-letter`, `find-contacts`, `prep-interview`) write their outputs here.

## File naming
`NNN-company-stage-YYYY-MM-DD.md`

- `NNN` — the role id from `pipeline.db` (zero-padded)
- `company` — short slug for the company
- `stage` — `company`, `jd`, `fit`, `bullets`, `cover-letter`, `outreach`, `contacts`, `interview-prep`, etc.
- `YYYY-MM-DD` — the date the artifact was produced

Example: `012-acme-fit-2026-04-15.md`

This directory is empty in the template. It will fill up as you run the pipeline.
