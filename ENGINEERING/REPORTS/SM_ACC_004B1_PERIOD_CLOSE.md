# SM-ACC-004B1 — organization period close barrier (candidate result)

Repository: n923760-rgb/smart-merchant. Base main: `a316e492eb6348cfdfefe19e155beea64f737cdf`, which includes qualified SM-ACC-004A. Actor: assistant via GitHub repository API (not a local checkout). Date: 2026-10-29.

## Bounded implementation
- Optional organization-wide inclusive period date ranges with OPEN/CLOSED, no auto-creation and no forced calendar.
- Owner-only global create/close; owner/accountant global read; cashier and branch-only rights do not grant closure.
- Prevent overlap in domain and PostgreSQL trigger with organization lock.
- One-way closure, immutable period bounds and no period deletion. Audit creation/closure.
- Block new POSTED journal records on closed booking dates even for direct SQL; serialize with period closure via organization row. Preserve historical confirmed-request replay and date-open reversals.
- No modifications to previously posted records and no requirement for terminal, POS, inventory, or branch.
- Explicit non-goals: reopening, mandatory calendar, opening balances, invoices/AR/AP, tax/fiscal, external providers, physical/production migration.

## Required source-specific qualification
- Task packet: `ENGINEERING/EVIDENCE/SM-ACC-004B1-task.json`.
- ADR 0014: `docs/adr/0014-accounting-period-close.md`.
- Migrations upgrade/check/downgrade/upgrade on disposable PostgreSQL 16.
- API and direct SQL tests of overlap, closure, tenant grants, no-calendar legacy, reversal, historical replay, close/post race, audit boundaries.
- Foundation CI, Accounting Web CI and Governance CI with exact SHA.
- Complete changed-source review and separate issue/PR for any unrelated defects.

**Until checks finish:** source state CANDIDATE, local shell/runtime NOT RUN, external provider/production/pilot NOT RUN. Do not call all SM-ACC-004 complete.
