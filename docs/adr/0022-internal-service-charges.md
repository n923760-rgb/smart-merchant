# ADR 0022 — Atomic internal service charges and customer receivables

SM-ACC-005D, 2026-11-05; base main d2c7f82a7f664ce89969db2477b08fe27e5c764a.

An explicitly approved INTERNAL_SERVICE_CHARGE is an internal accounting obligation,
not a fiscal invoice. It creates a customer receivable and immutable organization-wide
journal in one transaction. It has no official invoice number, XML, QR or issuance
claim. Operator-declared registration and classification remain unverified.

POST `/api/v1/billing/service-charges` requires global billing.charges.approve (owner
default), billing.charges.read (owner/accountant), billing.drafts.read, billing.tax.read,
customers.read, accounting.accounts.read and accounting.journals.post. Branch grants
are insufficient. The explicit approval includes `confirm: true`, a nonblank basis,
assessment/customer IDs, receivable ASSET, revenue REVENUE and tax LIABILITY posting
accounts, booking date and permanent request UUID. Accountants may read, not approve
by default. No inferred customer matching or account/tax selection occurs.

Require booking date = pinned assessment date and no later than today's organization
calendar date. Under the organization lock recheck SAR, sealed positive source,
current as-of REGISTERED profile equals pinned profile, all accounts active/postable,
closed-period and opening-cutover barriers. Backdated operator-approved internal
accounting is allowed only under those existing ledger barriers; no legal tax point
is certified. Missing or stale profile conflicts. Immutable source snapshots stay
unchanged; a separate unique `(organization_id, draft_id)` charge owns financial effect.

Debit AR gross, credit revenue net and credit tax liability VAT; omit a zero VAT
line (tiny taxable amounts may round to zero, not an exemption). ServiceCharge itself
is the initial immutable customer subledger debit; amounts derive from its immutable
assessment. There are no settlements yet, so report `original_amount` rather than an
unqualified live balance. Reads return a reconciled journal reference, not permission
to issue an invoice. GET by charge ID and GET `/service-charge-requests/{request_id}`
allow unknown-result recovery. Same request/content returns the original before
configuration/period rechecks; changed payload, other journal-domain UUID collision,
or a second source effect with another UUID conflicts. Authorization is always rechecked.

SQL composite tenant FKs, unique source/request/journal, immutable charge rows and an
insert integrity trigger verify source/profile/date/account mapping plus exact posted
journal lines, date, request hash, actor and no existing reversal. Org locking serializes
posting, profile changes, closing and generic reversal. SQL rejects any new reversal
of a charge journal; the API also gives a normal conflict. A future correction/credit
command must reverse both subledger and journal under a separate ADR. No corrections,
collections or customer-balance aggregate is exposed here. Manual journals can still
exist independently and are not automatically classified as customer transactions.

Audits contain IDs only; journal description is a fixed internal label, not customer
or approval text. Charge, journal, lines and both audit events commit or roll back
together. Require actual PostgreSQL API/SQL/concurrency/rollback/tenant/RBAC tests,
Alembic schema checks/cycle and all exact-head CI. Same-session review is not independent.
No production deployment or merchant/fiscal acceptance is authorized by this ADR.
