---
name: draft-cover-letter
description: Draft a differentiated cover letter for the candidate tailored to a specific role. Use when the candidate asks for a cover letter, when applying to a role that requires one, or when a stronger narrative differentiator is needed beyond resume bullets. Requires analyze-jd to have been run. All voice rules, differentiators, and metrics are in CLAUDE.md. Never produces a templated opener. Always anchors to a specific problem the company has that the candidate has solved.
---

# Draft Cover Letter — Output Template

All voice rules, differentiators, exact metrics, and fit logic are in CLAUDE.md.
Requires analyze-jd output in context. Uses company-research output if available.

## What Makes This Different From a Template

Most cover letters fail because they restate the resume or open with
"I am excited to apply for..." The differentiator is problem-specificity:
open with the company's actual challenge, then demonstrate the candidate has solved
an equivalent problem at scale.

Structure:
1. **Hook** — Name the specific problem this company/team is facing
2. **Proof** — One the candidate story that maps directly to that problem (with metric)
3. **Bridge** — Why that makes him the right builder for this role
4. **Ask** — Specific, confident close

Length: 3 short paragraphs + close. Maximum 300 words. No bullet points.

## Step 1: Identify the Company's Core Problem

From company-research and analyze-jd, identify the most specific answer to:
"What is the hardest operational or product problem this team is working on
right now that a Senior PM needs to own?"

Not: "They're building AI products"
Yes: "They're trying to move from a rules-based benefits quoting system to
a real-time API-driven platform while maintaining carrier compliance"

If the problem isn't specific enough from available context, note it and
ask the candidate before drafting.

## Step 2: Match the candidate's Strongest Story

From CLAUDE.md differentiators and resume metrics, select the single
the candidate story that most directly maps to the problem identified. One story,
one metric, clearly connected. Not a list of accomplishments.

Story selection hierarchy:
1. Exact domain match (same industry, same type of system)
2. Equivalent operational complexity (same scale, same constraints)
3. Same pattern (0→1 platform build, compliance migration, API-first redesign)

## Step 3: Draft

**Opener rule:** Never start with "I", "My name", or "I am excited."
Start with the company's problem or a specific observation about their work.

**Proof paragraph rule:** One story. Verb + what was built + outcome + metric.
Maximum two sentences. If it's longer, cut it.

**Bridge rule:** Make the connection explicit. Not "I believe I would be a great fit."
Something like: "That's the same migration pattern I ran at [prior company] — and
the same reason I'm interested in this role specifically."

**Close rule:** Confident, specific ask. Not "I look forward to hearing from you."
Something like: "I'd like to talk about how I'd approach the first 90 days
on this problem."

## Output Format

```
## Cover Letter: [Role Title] at [Company]

Problem anchored to: [1 sentence — the specific company challenge]
Story used: [Which story from references/stories/ + the metric used]
Voice check: [Confirm it passes the voice rules in CLAUDE.md]

---

[Company name or team name],

[Hook paragraph — company's problem, 2-3 sentences]

[Proof paragraph — the candidate's matching story, 2-3 sentences, one metric]

[Bridge paragraph — explicit connection + why this role specifically, 2-3 sentences]

[Close — specific ask, 1-2 sentences]

[Name]

---

Word count: [N] / 300 max

Notes:
[Anything the candidate should know — e.g., "This opener references their recent
Series C announcement — verify it's still current before sending"]
```

## Quality Gates Before Presenting

- [ ] Opener does NOT start with "I", "My name", or "I am excited"
- [ ] Specific company problem named in paragraph 1
- [ ] Exactly ONE the candidate story with ONE metric in paragraph 2
- [ ] Bridge makes the connection explicit, not implied
- [ ] Under 300 words
- [ ] Passes all voice rules from CLAUDE.md
- [ ] Contains zero buzzwords (passionate, results-driven, leverage, synergy)
- [ ] Could NOT have been written for a different company

If any gate fails, fix before presenting.
