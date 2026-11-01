# ADR 0017 — Stable operator-created customer identities (SM-ACC-005B1A)

Status: implementation candidate under the owner's 2026-10-31 continuation.
Base: `b866fee7edc42e9add3bb4733200ad25642cb281`. First bounded prerequisite
of [issue #35](https://github.com/n923760-rgb/smart-merchant/issues/35).

## Boundary and outcome

Provide a canonical UUID for a customer inside one organization, independent of
terminals, shifts, stock and external channels. This is an **operator-created
record**, not verification of a real person's identity, legal entity or tax status.
Its API reports `identity_status=OPERATOR_CREATED`. No fuzzy merge, KYC, provider
alias, financial amount or tax qualification is implied.

An owner/accountant can create a minimal display-name snapshot and optional email,
read it, page through the registry, and recover a creation by its original request
ID. They must select the future customer ID explicitly when approving a financial
document; a matching name/email alone must never establish that relationship.
Same contacts and a different request ID deliberately create a different customer.

## Identity, replay and authorization

- Mandatory `organization_id`, UUID primary key and unique `(id, organization_id)`
  support future tenant-safe financial FKs. No new financial FK is introduced here.
- `(organization_id, request_id)` is permanently unique. Request IDs are generated
  by the caller before submission. Normalized name/email content has an
  operation-specific digest; same identity/content returns the original record,
  changed content conflicts. No retry generates a fresh identity automatically.
- Creation serializes on the existing organization PostgreSQL row across workers.
  Registry insertion and its append-only audit commit in one transaction.
- Organization-global `customers.create` and `customers.read` are independent
  grants. OWNER/ACCOUNTANT receive both on existing and newly bootstrapped tenants.
  Branch-only roles, CASHIER and MANAGER do not receive global customer access.
  Permissions are rechecked for replay and recovery; no client navigation is trusted.
- All ID/request reads include the current organization. Authorized foreign/missing
  records return 404. Request lookup is an observation, not proof a still-running
  operation cannot commit. Explicit retry must retain the original request/payload.
- Pagination is stable by creation timestamp and ID, capped at 100 records per page.
  Audit contains only entity, actor and request IDs; names/emails are not copied.

## Initial snapshot policy

Rows are immutable in this bounded implementation, including profile fields,
tenant, request identity and actor. PostgreSQL rejects UPDATE/DELETE. This avoids
silently invalidating replay acknowledgements and future document snapshots.
There is no edit, merge, delete or erasure endpoint. This is **not** a complete
customer lifecycle or privacy/retention policy. Before merchant deployment, design
controlled profile revisions, correction and retention/erasure with historical
document semantics. Do not tell operators to fix a customer by creating duplicates.

## Financial boundary and next contract

Existing service drafts remain immutable, unlinked and `NOT_EVALUATED`; their
before-tax amount is not a final customer debt. Creating a customer cannot post
AR, service revenue, tax, payment or an opening balance.

The next bounded obligation task must define explicit customer and source-draft
IDs, approval/rejection, account mappings, tax/gross amount policy, period/cutover
rules, atomic journal and subledger linkage, replay/collision handling, reversal
protection and reconciliation. Drafts must not be relabeled as issued invoices.
Official Saudi policy/SDK and applicable taxpayer/cohort verification remain
required before a fiscal issuance claim. This ADR does not choose those policies.

## Required evidence

API/PostgreSQL tests for replay/conflict/concurrent submission, distinct same-contact
customers, bounded pagination, actor-controlled fields, tenant/global-vs-branch
RBAC, permission removal, SQL duplicate/mutation/blank-name rejection, rollback on
audit failure and absence of financial effects. Alembic upgrade/check/downgrade/
upgrade and exact-source Foundation, Accounting Web and Governance CI must pass.
Real merchant, physical devices, production migration and financial/fiscal
acceptance remain NOT RUN. Review is same-session unless separately identified.
