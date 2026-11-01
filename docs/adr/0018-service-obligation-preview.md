# ADR 0018 — Read-only service-obligation qualification preview

Status: candidate, SM-ACC-005B1B, owner continued development on 2026-11-01.
Dependency: customer PR #36 at `e1a2c547ea2fa427deb3fcea027c1612efe9dd64`.
This is the next bounded contract of issue #35, not the full financial posting engine.

## Decision

`POST /api/v1/billing/service-obligation-previews` accepts explicit draft/customer,
receivable-account and revenue-account UUIDs plus a booking date. Despite its HTTP
method, it is a structured read: no saved link, approval, document, request ID,
journal, audit mutation or other database effect. Repeating a preview cannot post
anything, so durable mutation idempotency is not introduced for this endpoint.

All five global read grants are required: `billing.drafts.read`, `customers.read`,
`accounting.accounts.read`, `accounting.periods.read` and `accounting.opening.read`.
The latter two prevent period/cutover inference without those read grants.
Branch-only grants are insufficient. Every referenced
row is scoped to the authenticated organization; foreign or missing IDs return 404.
No posting permission is inferred from a preview. Existing permission defaults remain.

The selected receivable account must be an active postable ASSET leaf, and the
selected service-revenue account an active postable REVENUE leaf. Types are an
initial semantic validation, not accountant certification that an arbitrary asset
account is suitable as an AR control account. No permanent account mapping is set.
The draft must be a sealed positive SAR draft and the organization qualified for SAR.
No POS, branch, shift, terminal or inventory is required.

Return a precisely formatted two-decimal pre-tax debit/credit **allocation**, using
the immutable source total (including its per-line HALF_UP rounding). It is not a
JournalIn command: there is no `lines`, journal UUID or posting request UUID. Explicit
customer selection never fuzzy-matches name/email; show source-name/email and selected
customer ID/name separately so the caller can review a mismatch without mutating it.

## Fail-closed financial semantics

Every response has `can_post=false`, `approval_status=NOT_APPROVED`,
`tax_status=NOT_EVALUATED`, `tax_total=null` and `amount_due=null`. It must retain
`TAX_POLICY_UNQUALIFIED`, `FINANCIAL_APPROVAL_REQUIRED` and
`POSTING_NOT_IMPLEMENTED` blockers even when accounts/date look valid. Unknown tax
is never zero, and pre-tax value is never presented as a final enforceable debt.
Client-supplied tax, totals, approval/posting flags and branch/request fields are rejected.

Report closed-period and on/before-opening-cutover blockers, including a booking
date equal to the cutover, without mutating the ledger or discarding the useful preview. A later
date removes only the date blockers. The preview is not a reservation: account status,
permissions and date rules can change after reading, and **all** rules must be checked
again inside the eventual posting transaction.

There is no hidden automatic-post path, queued job or approval token. Reversal,
receipts and reconciliation therefore cannot be implied by this implementation.

## Verified official fiscal boundary (2026-11-01)

Read official ZATCA sources before designing this contract:

- [Compliance SDK](https://www.zatca.gov.sa/en/E-Invoicing/SystemsDevelopers/ComplianceEnablementToolbox/Pages/DownloadSDK.aspx): passing SDK checks does not itself mean authority approval; integration, specification and security requirements still apply.
- [Detailed technical guideline](https://zatca.gov.sa/en/E-Invoicing/Introduction/Guidelines/Documents/E-invoicing-Detailed-Technical-Guideline.pdf): onboarding, CSID and reporting/clearance are distinct technical stages.
- [Developer specifications](https://www.zatca.gov.sa/en/E-Invoicing/Pages/default.aspx): invoice data dictionary, XML and security specifications exist as distinct requirements.

This research is not a taxpayer/cohort assessment, legal opinion, installed SDK
version check or sandbox test. No tenant's legal/tax status is assumed. No fiscal
number, QR, XML, cryptographic stamp or ZATCA acceptance is implemented or claimed.

## Future posting contract — not authorized by a preview

Before enabling a separate approval command, specify:

1. Qualified organization/customer/tax identities and immutable source snapshot;
   explicit operator confirmation, selected AR/revenue/output-tax mappings and
   deterministic assessed net/tax/gross rules including rounding and discounts.
2. Organization-serialized permanent request digest and unique approved source
   identity, same-request replay and collision detection; repeated source approvals
   with different UUIDs must not double-book a charge.
3. Atomic immutable charge/subledger/journal/audit links with composite tenant FKs;
   recheck account/period/opening and grants inside the transaction.
4. Explicit charge vs legal invoice state, qualified issuance/reporting gates and
   no reuse of this pre-tax allocation as a final collectable obligation.
5. Credit/reversal rules that keep source, AR and ledger reconciled; no generic
   reversal may silently orphan a future financial subledger.

These are implementation acceptance requirements, not a choice of fiscal policy
or proof that such an engine already exists.

## Validation

Real PostgreSQL/API tests cover exact 34.99 SAR source rounding, separate source and
selected customer identity, global/branch/composed-grant denial, each missing/foreign
reference, unsuitable/inactive/summary accounts, zero/non-SAR rejection, closing and
cutover boundaries, client spoofing, repeated reads and no audit/ledger/draft effects.
Require exact-source Foundation, Accounting Web and Governance CI. Stacked PR must
not be merged independently of #36. UI, physical device, merchant, production and
fiscal/provider acceptance remain NOT RUN.
