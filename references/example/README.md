# references/example/

A worked example of a fully configured `references/` set. The persona is fictional — Maya Chen, a Senior PM in B2B fintech — so nothing here should be copied as-is. The point is to show what "filled in" looks like before you write your own.

## Files

| File | What good looks like |
|------|----------------------|
| `resume.md` | Markdown resume with metrics that are specific, attributable, and reused verbatim downstream |
| `cmf.md` | One-line pitch, conversation version, target scenarios, hard constraints, and differentiators that each cite a story file or a resume metric |
| `mnookin.md` | Must-haves and must-nots in the candidate's own phrasing, not generic PM language |
| `stories/01-card-issuing-migration.md` | Infrastructure / migration story with verified metrics and an explicit "not verified" section |
| `stories/02-fraud-signals-platform.md` | Product launch story with the same structure |

## How the agents use these

- `analyze-jd` and `score-fit` read `cmf.md` and `mnookin.md` to filter roles.
- `draft-resume-bullets` and `draft-cover-letter` pull from `resume.md` and `stories/`.
- `draft-outreach` reads `cmf.md` for voice anchors and `stories/` for hooks.

If you cite a metric in any of these files that is not in `resume.md` or in a story's "Verified metrics" section, the agents are instructed to flag it as unverified. That is intentional — the example shows the discipline, not just the format.

## When to delete this folder

Once your own `references/*` files are in place and you are confident in the structure, you can delete `references/example/` — nothing in the template depends on it. Keep it around if you want a reference shape for adding new stories later.
