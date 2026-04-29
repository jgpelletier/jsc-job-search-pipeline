# Story: Fraud-Signals Evaluation Harness at Beacon Pay

## Situation

Beacon Pay's risk team was rolling out fraud models the way most teams do — train, evaluate against a held-out set, ship to a small percentage of traffic, watch the false-positive rate, expand. The problem was that the evaluation step happened *before* a model touched the auth path, and the auth path was where the real distribution lived. Twice in the prior year a model had passed offline evaluation and then driven the consumer false-decline rate up by ~2 percentage points within hours of expanded rollout. Both incidents required a manual rollback and a postmortem.

The risk org was about to ship a new behavioral-signals model that the team felt strongly about. The Head of Risk asked whether there was a way to gate the rollout so that another two-point false-decline excursion was structurally impossible, not just unlikely.

## Action

Designed an evaluation harness that ran the new model in *shadow mode* against live auth traffic — every real authorization decision was simultaneously scored by the candidate model, but the candidate's score never affected the actual decline. That gave the team a real-distribution evaluation set without any customer-facing risk.

The harness wrote three streams: the live decision, the candidate decision, and the divergence record. A streaming job computed false-positive-rate drift between champion and challenger on a one-hour rolling window. If FP-rate drift exceeded 0.4 percentage points sustained for 30 minutes, the rollback channel fired automatically and paged the on-call. The threshold and window were tunable per model class — fraud models got tighter gates than informational models.

Wrote the contract for what "promoted to challenger" and "promoted to champion" meant. Defined the four artifacts a risk modeler had to produce before requesting promotion: shadow window length, divergence summary, FP-rate-by-segment breakdown, and a written rollout plan with a named on-call. No promotion request was reviewed without all four.

Worked with the Head of Risk to make the harness the *only* path into the auth decisioning service. Direct deployment to the auth path was disabled at the infrastructure level — the only way for a model to affect a real authorization was through the harness.

## Result

The behavioral-signals model rolled out through the harness with no false-decline excursion. Three subsequent fraud models shipped through the same path in the following nine months, with zero rollbacks triggered by FP-rate drift. The harness caught one model in shadow that would have driven a measurable false-decline increase — the divergence detector flagged it at hour four of the shadow window and the team pulled the candidate before it ever reached challenger.

The risk org adopted the harness as the standard gate for any model touching the auth path. The platform org adopted the same divergence-detection pattern for a separate model gating effort on the dispute-routing path.

## Verified metrics

- 3 fraud models shipped through the harness in the 9 months after launch — model-registry log
- Zero rollbacks triggered by FP-rate drift on those 3 models — incident tracker
- One pre-promotion catch — incident summary written by the risk team and shared at the monthly platform review
- 0.4 percentage point FP-rate drift threshold — codified in the harness config, reviewed with the Head of Risk
- Direct deployment to auth disabled at the infrastructure level — confirmed via the deployment-config audit

## Not verified — do not claim

- "Saved the company $X in prevented false declines." Plausible but I do not have a calculation I would defend in a hiring conversation.
- That the dispute-routing team's adoption was caused by the harness specifically. The two efforts overlapped in time and the lead on dispute-routing had been thinking about this independently.
- Any claim about how this compared to other companies' practices. I have heard a lot of secondhand descriptions of how peers do model rollouts but have not personally validated any of them.

## Short version (outreach / cover letter)

Beacon Pay's risk team had twice rolled out fraud models that passed offline evaluation and then drove the consumer false-decline rate up two points within hours of going live. I built the evaluation harness that made that excursion structurally impossible — every candidate model runs in shadow against live auth traffic, with FP-rate drift > 0.4pp triggering automated rollback, and direct deployment to the auth path disabled at the infrastructure level. Three subsequent models shipped through the harness with zero drift-driven rollbacks. The risk org adopted it as the standard gate. Risk tooling is a developer experience problem in a trench coat.
