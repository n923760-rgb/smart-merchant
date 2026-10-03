# ADR 0010 — General accounting core and immutable journal posting

Status: accepted implementation direction under the owner's 2026-10-03 scope change.
Source: main 80de2647186d999e98e2ff77eff1e1dd1c7810d0. Task SM-ACC-001.

## Context

The owner merged the original POS/inventory/accounting vision with a multi-device/offline prompt, then explicitly required a general accounting application without a required business category. POS-001–150 remains an operational-module contract, not a requirement for accounting-only customers.

## Decisions

Accounting commands require an active authenticated organization/membership and accounting RBAC. They do not require terminals, cashier identities or shifts. Branch-tagged journals are scoped to the same organization and authorized branch; organization-level journals require global permission. Organization-level account management cannot be authorized by a branch grant.

The first slice implements ASSET/LIABILITY/EQUITY/REVENUE/EXPENSE accounts and manual balanced journals, initially qualifying SAR and decimal-string inputs with two places and NUMERIC(18,2). This is a currency qualification boundary, not a sector restriction. Multi-currency, account hierarchies, periods, invoices, settlement, tax or financial reports are not implied.

Each journal has a durable organization-scoped UUID request ID and normalized request digest. Serialize initial posting/reversal on the organization row across workers. This deliberately favors correctness over maximum parallel throughput; replace with a proven narrower durable concurrency protocol only when needed. Same identity/content returns the original journal; changed content conflicts. Authorization is rechecked before replay. No expiring Redis retry cache defines financial identity.

Posting inserts a transient DRAFT header and lines, then transitions to POSTED and writes audit in one transaction. No durable draft API exists. A deferred PostgreSQL constraint trigger requires final POSTED state, posted time, at least two positive one-sided lines and equal debit/credit totals at commit. Composite foreign keys prevent cross-organization account/branch/entry references.

Database triggers reject all updates/deletes of posted headers and journal lines, and insertions of additional lines into posted entries. API callers cannot set posted state, actor, organization, currency or totals. Ledger changes and success audit roll back together. Source permissions/active context remain checked by the server; database constraints are not a substitute for authentication.

An explicit full reversal has a new UUID and reason/date, copies original accounts, reverses every debit/credit and retains the original unchanged. One full reversal per original, enforced by uniqueness and organization serialization; reversal-of-reversal and partial corrections are intentionally not exposed in this slice. Deactivated accounts may be used for reversing historical entries; new postings reject them. Reads/reversal of historical branch entries remain possible under valid permissions even after branch deactivation; new postings need an active branch.

Only system OWNER/ACCOUNTANT roles receive the new accounting grants during migration; bootstrap gives those roles matching defaults. CASHIER and MANAGER do not gain ledger mutation by virtue of POS access. Existing custom grants remain intact.

## Qualification and follow-up

Meaningful checks include exact decimal balance, request collision, tenant/branch/role and inactive-context denials, simultaneous replay/reversal, SQL-level append/mutation/unbalanced/unfinished rejection, audit rollback, and Alembic upgrade/check/downgrade/upgrade.

The standalone API is the first accounting foundation. Accounting UI, chart hierarchies, closing periods, vouchers, customers/suppliers, AR/AP, fiscal invoices, automatic posting rules, tax/rounding policy, trial balance/statements and accountant/pilot review remain separate dependent outcomes. POS offline rules do not authorize offline manual ledger posting or bypass central accounting periods. No production acceptance is claimed.
