# ADR 0023 — Internal service receipts and receivable settlement

Status: CANDIDATE — not accepted, not production, not fiscal payment validation.
Date: 2026-11-16. Base main: `f7fea13626c8cf8c3f37ebf72940abdf989aacd9`.
Dependencies: ADR 0010 (general ledger), ADR 0012 (confirmed journal), ADR 0022 (internal service charges).

## Context
SM-ACC-005D creates an immutable customer charge and exact balanced AR/revenue/tax journal. Its original gross amount becomes an internal receivable; there is currently **no recorded collection**, partial payment or settlement. A journal-only cash entry cannot be allowed to claim that a customer debt is settled.

## Decision — bounded first settlement
- Only pre-existing POSTED INTERNAL_SERVICE_CHARGE documents with original SAR gross from their pinned immutable assessment may be settled. An internal receipt is **operator-reported** rather than verified bank/PSP capture. No tax invoice issuance.
- Each receipt references one charge and one global active/postable ASSET cash/bank account distinct from the receivable account; a concrete, explicit amount in SAR with strict decimal-string input, two-decimal precision and > 0; booking date, `CASH` or `BANK_TRANSFER`, optional operator reference, evidence basis and explicit confirmation.
- Serialize at organization scope, then recompute total received for that charge; refuse a new receipt that would make collected > gross. Same request and normalized payload replay the same persisted effect; mutated payload or journal UUID collision fails. Do not use timeout-only replay keys.
- In a single transaction insert an immutable receipt, a matched POSTED journal (debit settlement asset, credit original charge AR), and minimal audit. Composite tenant references, immutable SQL constraints and insertion-time reconciliation checks reject forged or orphaned receipts, incorrect amounts, invalid journal links and raw SQL over-collection.
- Verify per-organization permissions server-side: global `billing.receipts.record` plus read grants, `billing.charges.read`, `accounting.accounts.read`, `accounting.journals.post`; read grants remain distinct. Existing and future organizations grant OWNER record/read, ACCOUNTANT read. No branch-only shortcut or app-inferred authority.
- Underlying generic journal reversal must reject source receipt journals (API **and database**). Refund/charge correction require a **separate balanced subledger correction design** rather than reversal alone.
- Charge balance is derived as original gross minus posted immutable receipt amounts, returning UNPAID/PARTIALLY_PAID/PAID. No claim that cash was received from an external gateway or bank.
- Prevent bookings before the originating charge, after the organization's current local date, into closed periods, or on/before immutable opening cutover. Do not require POS, stock, shifts or a printer.

## Exclusions and follow-up
No e-invoice, ZATCA validation, automatic banking/provider status, payment links, installment schedule, external references reconciliation, refunds/chargebacks/write-offs, customer balance UI, multi-currency or deployment.

## Qualification gates
Contract and exact-money regression; two partial receipts and final settlement; overpay (including parallel requests); invalid/cross-tenant account, customer and charge; RBAC/branch-only denial; same-ID stable replay and changed-ID rejection; audit failure rollback; SQL direct insertion, update, delete, reversal, wrong-journal and overpay; date, currency and cutover gates; Alembic upgrade/check/downgrade/upgrade; all exact-head CI including real PostgreSQL/browser/Android/iOS builds. This ADR remains candidate until evidence and full diff review.
