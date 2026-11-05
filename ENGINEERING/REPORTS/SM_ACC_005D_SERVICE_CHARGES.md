# SM-ACC-005D — internal service-charge qualification

Repository n923760-rgb/smart-merchant; base main d2c7f82a7f664ce89969db2477b08fe27e5c764a,
verified 2026-11-05 with no open PRs. Actor: Codex, sole source writer with a distinct
same-session review phase (not independent review). Owner continued development
and expressly authorized appropriate reviewed merges; no deployment.

[ADR 0022](../../docs/adr/0022-internal-service-charges.md) defines one bounded outcome:
explicit owner internal approval atomically creates an immutable source/customer
subledger debit and matching organization-wide journal. Permanent request recovery,
unique source effect even across reassessments, SQL reconciliation and reversal
barriers protect it. Tax declaration/classification is still operator supplied.
No fiscal invoice, collection, correction or production acceptance is claimed.

Local ruff, mypy and governance contract fixtures PASS. 48 accounting/money unit tests
PASS. Local PostgreSQL/Redis/Docker unavailable: actual integration, schema comparison,
migration cycle, real browsers and mobile builds must qualify through current-head
GitHub Actions. Historical 230-test baseline is not evidence for this source.
Candidate until all exact-head checks pass and same-session source review completes.
