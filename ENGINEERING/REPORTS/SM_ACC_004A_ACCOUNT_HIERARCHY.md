# SM-ACC-004A — account hierarchy (candidate evidence report)

- **Repository:** n923760-rgb/smart-merchant
- **Owner direction:** 2026-10-29, continue accounting-first Hybrid V6.
- **Observed base main:** `930f5c6e4831a63ca33deb744af8f62cfbd10ea8` (post-merge Foundation, Accounting Web, Governance CI PASS).
- **Actor:** assistant, API-based source writer; initial design and implementation performed in same session. Independent technical review: NOT RUN.
- **Task record:** [SM-ACC-004A-task.json](../EVIDENCE/SM-ACC-004A-task.json). Detailed rule selection: [ADR 0013](../../docs/adr/0013-account-hierarchy.md).

## Bounded changes

- Root accounts retain their historical posting behavior (`is_postable=true`, `parent_id=null` by DB default).
- New group accounts are non-postable and may contain only same-type children. A parent must be active and within the same tenant.
- Structurally immutable group classification and parent links at PostgreSQL boundary; no rename/reparent/update UI in this slice.
- Journal domain code and a separate SQL-level insert trigger refuse postings to groups, including direct DB insertion.
- API creation/listing exposes `parent_id` and `is_postable` without changing existing account/journal identities or roles.
- Disposable PostgreSQL regressions cover existing posting, nesting, malformed/foreign parents, cashier denial, direct SQL edits/group journal lines, no ghost journal.
- No POS, periods, opening balances, financial document, invoices, integration, AI, production or secrets changes.

## Validation and qualifications

This is a **candidate implementation** until exact-source hosted checks complete. Local isolated PostgreSQL/Docker/mobile/production execution: NOT RUN. Required:
1. Task-packet schema validation (governance validator).
2. Foundation: Python ruff/mypy, Alembic upgrade/check/downgrade/upgrade, pytest integration and audit.
3. Accounting Web: real ledger browser regression.
4. Governance: existing rules and packet fixtures.
5. Same-session review of complete diff for cross-tenant or financial effects.

**Known boundaries:** no period close or opening balances, no account-type migration, no merchant deployment. Do not call the full SM-ACC-004 complete merely because SM-ACC-004A passes. Record exact CI run IDs and final SHA in PR review when available.
