# Story: Beacon Pay Card-Issuing Migration

## Situation

Beacon Pay's 1.4M active cards were running on a third-party issuer-processor under a contract that was repricing in 14 months. The processor's per-auth fees had grown to roughly $3.2M annual run-rate, and the contract terms made it expensive to scale beyond ~2M cards. The CFO and the Head of Issuing wanted out before the repricing window closed.

The constraint that mattered: no card reissuance. Reissuing 1.4M cards would have generated millions of customer-support contacts and broken every recurring-payment relationship across the customer base. The migration had to be invisible to cardholders.

## Action

Negotiated a BIN sponsorship arrangement with a sponsor bank that let Beacon Pay keep the same BINs and the same card numbers under a new processor. That single decision is what made the migration possible without reissuance — it took eleven weeks of legal and risk work to land.

Designed the parallel-processing model: every auth was sent to both processors during a six-week shadow window, with the legacy processor as system of record and the new processor scored in shadow. Built the reconciliation tooling that compared decision outputs in real time and flagged any divergence > 0.5% on a one-hour rolling window.

Wrote the cutover playbook with the engineering and risk leads. The cutover was BIN-by-BIN over four weekends, with automated rollback wired to the same divergence detector that ran in shadow.

Owned the executive comms — weekly status, one-page risk register, and a single named decision-maker for any migration-affecting trade-off. That last part is what kept the program moving when the sponsor bank's compliance team raised a late objection on velocity-limit handling.

## Result

1.4M cards migrated over four weekend cutovers. Zero reissuance. $3.2M annual processor-fee reduction realized in the quarter following final cutover. p99 auth latency improved from 210ms to 140ms in the process — not the original goal, but a side effect of the in-house decisioning service that replaced the legacy rules engine.

Eleven months from kickoff to final cutover.

## Verified metrics

- 1.4M active cards — Beacon Pay internal dashboard, screenshot saved in personal records
- $3.2M annual processor-fee reduction — finance VP shared the post-migration variance analysis at the Q1 all-hands
- p99 latency 210ms → 140ms — observability dashboard, tracked as a migration KPI
- 11-month execution window — kickoff and final-cutover dates in the project tracker
- Zero reissuance — confirmed by absence of reissuance volume in the card-ops monthly report

## Not verified — do not claim

- Customer-support contact volume during migration. Anecdotally low but I do not have the actual ticket numbers.
- "First sponsor-bank-managed BIN migration of this size in the cohort" — I have heard this said internally but have not seen a source I would cite externally.
- Specific NPS or retention impact. The migration did not move either metric in a measurable way that I can attribute.

## Short version (outreach / cover letter)

Beacon Pay needed to exit a third-party issuer-processor before a repricing window closed, but reissuing 1.4M cards was off the table. I negotiated a BIN sponsorship arrangement that kept the same card numbers under a new processor, designed a six-week shadow-processing window with real-time divergence detection, and ran the BIN-by-BIN cutover over four weekends. 1.4M cards migrated, zero reissuance, $3.2M annual fee reduction, p99 latency 210ms → 140ms as a side effect. Eleven months end to end. The migration was the product.
