# ADR 0013 — Append-only account hierarchy and posting leaves (SM-ACC-004A)

Status: **proposed implementation direction under owner-approved accounting-first Hybrid V6**, 2026-10-29. This ADR covers only the account-tree slice of [issue #25](https://github.com/n923760-rgb/smart-merchant/issues/25); periods and opening balances remain separate tasks and decisions.

## Existing baseline
ADR 0010 provides tenant-scoped, exact-SAR-decimal, immutable posted ledger entries. Existing accounts have no hierarchy. Their identifier, account type and posted history must not change. ADR 0012 uncertain-result recovery, organization-serialized journal commands and branch grants remain unchanged.

## Decisions

1. New accounts may specify an optional `parent_id` and `is_postable`. Existing rows migrate as root **postable** accounts (default true), preserving all journal links and response semantics.
2. A parent must already exist within the same organization and be **non-postable**, active, and of the same account type (ASSET/LIABILITY/EQUITY/REVENUE/EXPENSE). Roots can be either a postable leaf or a summary group; a new summary can have any number of same-type children.
3. Accounts are **append-only structurally** in this slice. Do not change an existing account's `organization_id`, `parent_id`, `account_type` or `is_postable` via API or SQL. There is no reparent/conversion endpoint. This eliminates hierarchy cycles by construction and protects historical ledger meaning. Account name/status management remains outside this slice.
4. Explicit summary/postable distinction is independent of whether a root has children. Only postable leaf accounts may receive journal lines. The domain service rejects summary account postings, including reversals; previously posted historical entries refer only to migrated postable accounts.
5. PostgreSQL composite FK `(parent_id, organization_id) -> accounts(id, organization_id)` enforces tenant isolation. A DB trigger enforces structural immutability and checks parent type/postability/active status. A separate `journal_lines` insert trigger prevents direct SQL from posting to summary accounts. The existing immutable journal trigger and balanced constraint trigger remain untouched.
6. Account management requires organization-level `accounting.accounts.manage`, never branch-only permissions. Read access remains the existing scoped `accounting.accounts.read`. No new role defaults are granted.
7. No period/fiscal policy is implicitly selected. Opening balances and period lock need a separate ADR and tests for close-vs-post races; no period-gating assumptions are introduced.

## Rejected choices

- Automatically converting a postable account to a summary account while preserving historical entries (would create ambiguous rollups and reversal edge cases).
- Treating every parent account as postable by default (allows duplicate bookings to parent and child).
- Client-only validation (bypassable through API/SQL).
- Building hierarchical UI, closing periods, and opening balances in the same migration (too wide for safe review).

## Qualification

Require PostgreSQL and API tests for legacy compatibility, proper nesting, wrong kind, inactive/postable/foreign parent, role denial, direct SQL structural mutation and summary journal insert, unmodified reversal/idempotency, Alembic upgrade/check and downgrade/upgrade. A green CI does **not** qualify live merchant migration or production/pilot accounting.

## Future

A future controlled chart reorganization must have its own migration and audit policy, including which historical rollups can move and how pending financial commands are handled. Periods and opening balances follow as SM-ACC-004B/C in the single engineering roadmap.
