# stories/

Verified work stories. One file per story. The agents use these instead of reconstructing facts from resume bullets, which is how metrics get distorted.

## Why this exists
Resume bullets compress. Compressed claims drift when reused in outreach or interview prep. A story file is the long form: what the situation was, what you did, what changed, what numbers are verified, and what is *not* verified. The agent reads the story, not the bullet.

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
