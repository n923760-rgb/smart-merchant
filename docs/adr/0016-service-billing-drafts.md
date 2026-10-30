# ADR 0016 — Immutable internal service-billing drafts (SM-ACC-005A)

**Status:** Candidate, 2026-10-30. Accounting-first Hybrid V6. Drafts are **not issued tax invoices** and are never accepted as proof of ZATCA compliance. This ADR is the limited first slice of [issue #31](https://github.com/n923760-rgb/smart-merchant/issues/31).

## User-facing behavior
- An organization-level owner or accountant may prepare an **internal draft** containing a customer-name snapshot, optional email and 1–100 service lines. The operator may view the draft by ID and list their organization's drafts.
- No terminal/shift/stock connection is needed. No payment, tax, fiscal number, PDF/QR tax invoice, accounts-receivable or ledger entries are created.
- Explicit output: `status=DRAFT`, `document_kind=INTERNAL_SERVICE_DRAFT`, `tax_status=NOT_EVALUATED`, `currency=SAR`, `amount_before_tax`. These numbers are *not* final tax-inclusive amounts.
- A draft is an **immutable prepared snapshot** in this slice. To correct one, create a replacement draft with a new request ID; editing, voiding, conversion to legally issued invoice and credit notes are separate reviewed tasks. Never assign an official invoice number to this draft.

## Exact-money policy
- All incoming monetary values and quantities are **decimal strings**, not JSON floating-point numbers.
- Quantity positive with at most 3 fractional digits; unit price nonnegative with at most 2 fractional digits.
- Each line amount is `ROUND_HALF_UP(quantity * unit_price, 0.01)` in SAR, and the before-tax total is the sum of those exact line amounts.
- VAT and exemptions are deliberately NOT assessed; do not silently assume zero rate, exemption, or a Saudi tax category.
- Persist the calculated line totals and the total in numeric(18,2), with SQL constraints and a deferred transaction check that the totals match. This is a commercial draft, not fiscal reporting.

## Authorization, identity and privacy
- Only organization-level `billing.drafts.read` and `billing.drafts.create` grants; owner and accountant receive both by default. Branch-only access does not reveal company-wide customer names.
- A `request_id` is permanently unique under `organization_id`; the normalized request digest is persisted. Same request+same content returns the existing immutable draft; same request with different payload returns conflict.
- Serialized organization lock protects write races. Tenant-scoped uniqueness, FK and server filtering enforce isolation. The customer snapshot contains minimum required information; no fuzzy merging with a catalog customer or provider profile.
- No personal customer details in audit metadata or logs. Only the draft ID and request ID are included in audit records.

## Database write lifecycle
1. Atomically insert parent in `BUILDING` state, insert correctly typed lines, then transition once to `DRAFT`.
2. PostgreSQL guard rejects any second mutation, delete or later line addition. A deferred constraint trigger rejects transactions with incomplete or numerically inconsistent drafts. A partial `BUILDING` draft must never commit.
3. One transaction writes draft/lines and append-only audit. Failed transactions leave no partial draft or fake ledger journal.

## Qualification and limits
Tests must include replay/mismatch, tenant and role denial, zero/negative/large/precision inputs, exact rounding, no journal side effects, direct SQL tampering, one-transaction guarantee and concurrent requests. All exact-SHA Foundation, Accounting Web and Governance checks must pass. No merchant pilot, production schema migration, ZATCA or payment-provider qualification is implied.

## Future contract
The later issuing process will use a separately qualified `service_invoice` domain state machine that creates customer AR and exact posted journals at the documented issuance boundary, with fiscal number/QR/tax rules only after official provider qualification. Do not mutate these internal drafts into issued invoices retroactively.
