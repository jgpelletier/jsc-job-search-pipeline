---
name: setup
description: First-time setup for a new candidate. Use when the candidate says "help me set this up", "I just cloned the repo", "walk me through onboarding", or when references/resume.md and references/cmf.md are still the unedited stubs. Checks prerequisites (pipeline.db), interviews the candidate to populate references/resume.md, references/cmf.md, references/mnookin.md, and references/stories/, then writes the first HANDOFF.md. Stops the moment the candidate has enough configured to run their first intake.
---

# Setup — Onboarding Interview

All judgment logic lives in CLAUDE.md. This skill is the interview script that gets the candidate from a freshly cloned template to a configured pipeline. It writes files; it does not score, search, or draft.

## Step 0: Prerequisites Check

The pipeline depends on `pipeline.db`. If it is missing, the first intake will fail with a SQLite "no such table" error and the candidate will not know why.

Check for it before anything else:

```bash
ls pipeline.db 2>&1
```

**If `pipeline.db` exists** — print "Database initialized." and continue to Step 1.

**If `pipeline.db` does not exist** — do not silently run the init script. Surface it to the candidate and ask before running:

> "I do not see `pipeline.db` yet. The init script creates it — `python3 db/init_db.py`. It is a one-time setup and writes only that file. Run it now?"

On confirmation:
```bash
python3 db/init_db.py
```

Then verify:
```bash
ls pipeline.db
```

If the script errors (most commonly because `python3` is not installed or is aliased to `python`), surface the error verbatim and stop — do not retry, do not try alternative interpreters. The candidate needs to resolve their Python environment before setup can continue.

## Step 1: Detect State

Read the four reference files and decide what is already done. A new clone has stub content; a partial setup has some real content.

```bash
ls references/
cat references/resume.md references/cmf.md references/mnookin.md
ls references/stories/
```

A file counts as "stub" if it still contains the placeholder phrases shipped with the template (`[Your Name]`, `Replace this stub`, `One or two sentences. What you build`, etc.). A file counts as "filled" once those are gone.

If `references/example/` exists and the candidate has not yet looked at it, mention it once: "There is a worked example in `references/example/` — same shape, fictional persona. You can skim it at any point."

Print the detected state before continuing:

```
Setup state:
- pipeline.db   — initialized
- resume.md     — stub (will interview)
- cmf.md        — stub (will derive from resume + stories)
- mnookin.md    — stub (will interview)
- stories/      — empty (will prompt for 3)
- HANDOFF.md    — does not exist (will create at end)
```

Skip any section already filled. Do not overwrite filled content without asking.

## Step 2: Resume First

The resume is the source of truth for every metric reused downstream. Get it right before anything else.

**Ask:** "Paste your current resume — markdown, plain text, or copy from LinkedIn is fine. I'll restructure it into the format the agents read."

When the candidate pastes:
1. Restructure into the schema in `references/resume.md` (Contact / Summary / Experience / Education).
2. **Extract every number you find** into a working list — revenue, volume, savings, percentage gains, headcount, scope. The candidate will need these in Step 3 and Step 4.
3. Ask one clarifying question per ambiguous metric: "You wrote '40% support reduction' — over what baseline, and what time window?"
4. Write `references/resume.md`.

**Hard rule:** do not invent metrics. If the candidate gave a vague claim ("improved performance"), keep it vague in the resume — do not estimate a number.

## Step 3: Stories — Pick Three to Start

Stories are the long form of resume bullets. The agents read these instead of reconstructing from compressed claims, which is how metrics drift.

**The long-term target is one story per resume bullet.** Three is the floor for setup — enough to demo and to start drafting. Once the pipeline is running, the candidate adds a story whenever a draft references a bullet that does not yet have one. Over a few weeks of real use, the resume and the stories folder converge.

**Ask:** "Looking at your resume, pick three achievements you would actually tell in an interview or cover letter. They should be the work you are proudest of, where you can name what you specifically did and what changed because of it. We will add more over time — one per bullet eventually — but three is enough to get you running."

For each of the three, run the interview in this order — one question at a time, do not batch:

1. **Situation** — "What was the context? Company, team, problem, stakes."
2. **Action** — "What did you specifically do? Be concrete about scope and decisions."
3. **Result** — "What changed? Numbers, dates, follow-on impact."
4. **Verified metrics** — "Of the numbers you just told me, which can you point to a source for? Dashboard, report, internal doc, public announcement."
5. **Not verified — do not claim** — "What sounds good in this story but you cannot actually prove? Leave it here so the agent does not pull it into a cover letter."

Write each story to `references/stories/NN-short-slug.md` using the structure in `references/stories/README.md`. Number them `01`, `02`, `03` in the order the candidate told them.

**The "Not verified" section must exist in every story file, even if empty.** It is the drift prevention.

## Step 4: Mnookin — Hard Constraints

Direct interview, no derivation. Ask three questions in sequence.

1. **Must-haves:** "What does a role need to have for it to be worth pursuing? Three to seven items. These are walk-away criteria — if any are missing, you would pass even on a strong-looking role."
2. **Must-nots:** "What is an automatic no? Three to seven items. A single match disqualifies the role."
3. **Soft preferences:** "What raises a role's ranking but would not kill it if missing? Two to five items."

Write `references/mnookin.md` with the candidate's exact phrasing — do not paraphrase into PM-speak.

## Step 5: CMF — Derive, Then Confirm

CMF is built from resume + stories, not asked cold. The candidate has already told you most of it.

Draft the file from what you already have:

- **The one line** — derive from the resume Summary plus the through-line across the three stories. Show the candidate two options, ask them to pick or rewrite.
- **Conversation version (3 sentences)** — extend the one line into "what you build / what makes you different / proof". Pull the proof point from the strongest verified story.
- **Search-ready versions** — ask: "What exact title phrases do you want to appear in saved searches?"
- **Target scenarios** — ask: "What three to five problem spaces or company shapes is your best work? Use the language you would use out loud."
- **Hard constraints** — copy from `mnookin.md` (location, domain anti-patterns).
- **Differentiator** — pull two or three verifiable claims, each tied to a story file or a resume metric. Write the story filename next to each one as a citation.

Show the draft to the candidate before writing. Ask: "Does this sound like you? Any phrase here you would not actually say?"

## Step 6: Voice Anchors

Voice anchors live inside `cmf.md` (or as a separate section the candidate prefers).

**Ask:** "Give me three to five phrases you have actually said or written about your work — short sentences that capture how you talk. Verbatim, not invented."

**Hard rule from CLAUDE.md:** do not invent voice anchors. If the candidate cannot name three, write what they have given you and add a note: `# Voice anchors — incomplete, expand as more emerge in real outreach`.

## Step 7: First HANDOFF.md

Write a minimal first-session HANDOFF so the next session has scaffolding to overwrite.

```markdown
# Session Handoff

> Read this at the start of every session before touching the DB or drafting anything.
> Overwrite at the end of every session with current state.

---

## Last Session

**Date:** [today]
**Tool:** Claude Code
**Type:** Initial setup

---

## Active Roles — Current State

None yet. Pipeline is empty.

---

## Next Session — Start Here

Drop a job posting screenshot into `inbox/` and say "process my inbox" to run the first intake.

Or paste a JD directly and say "score this role".

---

## What Was Completed This Session

- pipeline.db                — initialized (or pre-existing)
- references/resume.md       — populated
- references/cmf.md          — populated
- references/mnookin.md      — populated
- references/stories/        — N stories written

---

## Open Decisions

None.
```

## Step 8: Ready-to-Demo Summary

Print a closing summary. Keep it short, and tell the candidate what to expect from future
sessions so they do not have to remember the skill catalog.

```
Setup complete.

Configured:
- Database: pipeline.db
- Resume:   references/resume.md
- CMF:      references/cmf.md
- Mnookin:  references/mnookin.md
- Stories:  references/stories/01-..., 02-..., 03-...
- Handoff:  HANDOFF.md

From now on, every session opens with a short dashboard — pipeline state,
open decisions, and a list of things you can ask for. You will not need
to remember the skill names; the dashboard reminds you.

To run your first intake right now, try one of:
  • Drop a screenshot into inbox/ and say "process my inbox"
  • Paste a JD directly and say "score this role"
  • Say "run a job search" to seed the pipeline from scratch
```

Do not score, draft, or research in this session. Setup ends here. The next conversation is the
first real intake — and the agent will open it with the dashboard.

## What This Skill Does Not Do

- Does not run `python3 db/init_db.py` without the candidate's explicit confirmation. The check is automatic; the execution is gated.
- Does not invent stories, metrics, voice anchors, or constraints from generic PM knowledge.
- Does not overwrite a file the candidate has already filled in without explicit confirmation.
- Does not advance into `analyze-jd`, `company-research`, or any other skill in the same session — those are separate runs.
