# SM-ACC-004C1 — Initial opening balances candidate implementation

**Date:** 2026-10-29  
**Repository:** n923760-rgb/smart-merchant  
**Observed starting main:** `79c4592df139d5249d6622597d1ad0bdf06c5635` (period close PR #29 merged).  
**Executor:** assistant through authorized GitHub repository APIs; no local Postgres or production access.

## Bounded outcome

1. Initial organization-only opening journal uses exact balanced decimals, existing postable-leaf accounts and existing immutable ledger.
2. One unique `opening_balance_batches` row per organization references a posted journal in the same transaction; direct SQL update/delete rejected.
3. Posting with the same immutable request ID/payload is safe to replay; distinct or altered requests cannot create a second opening.
4. Existing posted journals on/before opening date block cutover. Once created, later journal dates on/before opening date are denied by service and SQL guard. Ordinary later transactions are allowed.
5. Opening journal is not reversed via ordinary reversal endpoint; an approved later-date adjustment is required for correction.
6. Owner-only global `accounting.opening.manage`; owner/accountant read; tenant isolation; branch access does not grant financial initialization.
7. An existing closed period forbids creation of an opening dated inside it.
8. The new endpoint is API-first. No final UI wizard, importing historical ledgers, fiscal-year carry-forward, invoice/AR/AP, POS, external connectors, ZATCA or production deployment.

## Evidence and acceptance gates

- Task packet: [SM-ACC-004C1](../EVIDENCE/SM-ACC-004C1-task.json)
- Architecture policy: [ADR 0015](../../docs/adr/0015-opening-balance-cutover.md)
- Tests: `backend/tests/test_opening_balances.py` for replay, duplicate, validation, tenant permissions, history, period closure, SQL bypass and concurrent creation.
- Foundation CI: **NOT RUN until candidate checks complete**; requires Ruff/Mypy, migrations and disposable PostgreSQL tests.
- Accounting Web CI: **NOT RUN until candidate checks complete**; must preserve real ledger/BFF behavior.
- Governance CI: **NOT RUN until candidate checks complete**.
- Physical/POS/provider/merchant pilot/production DB migration: **NOT RUN**.

## Risks and limitations

- One-time initial cutover may not be appropriate for an organization with historical journals dated earlier than the proposed opening; do not override it with hidden adjustments.
- A merchant must select accounts and complete balancing figures. The application never invents retained earnings.
- This is an initial organization cutover, **not** fiscal-year closing or period rollover.
- The exact-source CI verdict, review and merge decision must be recorded on the PR. Source documentation alone is not proof of accounting readiness.
