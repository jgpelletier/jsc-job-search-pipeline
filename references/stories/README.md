# stories/

Verified work stories. One file per story. The agents use these instead of reconstructing facts from resume bullets, which is how metrics get distorted.

## Why this exists
Resume bullets compress. Compressed claims drift when reused in outreach or interview prep. A story file is the long form: what the situation was, what you did, what changed, what numbers are verified, and what is *not* verified. The agent reads the story, not the bullet.

## How many stories do I need?

The target is **one story per resume bullet**. Each bullet on `resume.md` is a compressed claim; the matching story is the verified source the agent uses when that bullet shows up in a draft.

You do not need to write all of them up front. The setup skill prompts you for three to start — enough to demo and start drafting. Add a new story whenever you notice a draft pulling from a bullet that does not yet have a backing story. Over a few weeks of real use, the folder catches up to the resume.

If a bullet is too small or too generic to support a full story, that is a signal the bullet itself is doing too little work — consider tightening or removing it.

## File naming
`NN-short-slug.md` — for example `01-platform-migration.md`, `02-feature-launch.md`. Numbering is just for ordering; the slug is what the agent matches against.

## Recommended structure

```markdown
# [Story Title]

## Situation
What was the context? Company, team, problem, stakes.

## Action
What did you specifically do? Be concrete about scope and decisions.

## Result
What changed? Numbers, dates, follow-on impact.

## Verified metrics
- [Metric] — [source / how confirmed]
- [Metric] — [source]

## Not verified — do not claim
- [Claim that sounds good but is not provable]
```

Keep the "Not verified" section even when empty. It is what prevents drift.
