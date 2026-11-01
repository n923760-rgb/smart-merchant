# SM-ACC-005B1B — Service-obligation qualification preview

Repository: `n923760-rgb/smart-merchant`. Actor: Codex /root, one writer,
distinct same-session review; no independent review claim. Date: 2026-11-01.
Main observed at `b866fee7edc42e9add3bb4733200ad25642cb281`.
Dependency PR #36 remains open, ready and tested at
`e1a2c547ea2fa427deb3fcea027c1612efe9dd64` (tree
`4902f0b51baa643784cf6687031013a2799bfd9f`). Local starting tree matches exactly.
New branch/PR is stacked on #36, preserving its source and main.

## Change

An organization-wide read-only API lets the accountant explicitly select source
draft, canonical customer, receivable/revenue accounts and booking date. It validates
tenant/permissions/account semantics and returns exact pre-tax allocations plus
closed-date/cutover blockers. It never declares tax zero, a final amount due,
approval or posting. Repeated previews have no financial or audit mutation effect.

No schema migration, new permission, UI, persisted relationship, financial transaction,
provider or production operation is introduced. ADR 0018 records verified official
ZATCA sources and the future approval/idempotency/subledger/reversal requirements.
This is B1 qualification groundwork, not the completed B1 posting or B2 fiscal engine.

## Acceptance

New PostgreSQL tests cover references, grants, exact math, blockers and no-side-effect
behavior. Local available static/unit checks and remote current-source Foundation,
Accounting Web and Governance qualification must be attributed to the PR's exact head.
Local PostgreSQL/Redis/Docker/Flutter are unavailable; use existing disposable CI.
Local candidate Ruff and Mypy (39 modules) passed. Governance profile/negative
fixtures and task validation passed. All 15 existing database-free unit tests
passed; 33 new preview integration cases were collected, not executed locally.
The source-specific CI results and review record belong to this PR's final description,
not historical passes from #36. Keep candidate until all required checks pass.

## Review and next dependency

Check all UUID lookups for organization filters, combined global read grants before
data access, no hidden commit/post/audit call, strict input, null unknown tax/due and
unconditional posting blockers. Preview validity never authorizes a later write.
Next bounded task: qualified tax/financial-approval contract and atomic reconciled
AR posting, then corrections/receipts and the Arabic management UI. No merchant,
financial/fiscal, production or physical-device acceptance is claimed here.
