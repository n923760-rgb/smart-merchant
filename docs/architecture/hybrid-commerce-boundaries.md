# Hybrid Commerce — Domain Boundary & Integration Design Notes (V6)

**Status: PROPOSAL — product direction approved, detailed policies require ADRs and tests before implementation.**  
**Owner context:** 2026-10-29. **Execution:** ENGINEERING/MASTER_ROADMAP.md remains sole roadmap.

## Objective

Support merchants who already use an online store, physical POS, our native POS, or any combination, with **one trustworthy operating view**. An integration is not a second authority for all data by default. Preserve the accounting-only path for service merchants and the strict financial ledger.

## 1. Authority matrix (merchant-configurable within supported adapter capabilities)

| Entity | Candidate source | Import direction | Writeback |
| --- | --- | --- | --- |
| Financial journal | Native accounting engine | Derived from approved source documents | Never overwrite external journals blindly |
| Service/product invoices | Qualified invoice issuer | Issuer-specific | Only where an approved contract exists |
| Product attributes | Selected catalog owner | Read/import | Explicit edits only |
| SKU/variant identifiers | Internal catalog plus source mapping | Read/import | Never guess same SKU means same item |
| Stock ledger | Native stock engine **when enabled** | External snapshots/events require reconciliation | Separate explicit policy, not default |
| Online order | Origin storefront | Inbound verified | Status updates only if capability/scope allows |
| Native POS sale | Native POS authoritative | Internal event | Nonduplication on reconciliation |
| Payment settlement | Payment provider/bank evidence | Signed/verified provider read | Never infer a captured payment from a client click |
| Customer identity | Internal ID + provider-scoped alias | Bounded import | No fuzzy cross-channel merge by name/phone alone |

The authority owner may vary by merchant and by field. Accountants retain their current no-POS journal workflow.

## 2. Core identities (conceptual; NOT migrations)

- `organization_id` mandatory on every business row and adapter credential/alias.
- `merchant_connection_id`: one authorized provider account, with OAuth state, permissions, lifecycle and redacted health.
- `external_entity_mapping`: `(organization_id, connection_id, entity_kind, external_id)` unique, mapped to one canonical entity ID.
- `external_event_receipt`: signed provenance, provider event ID/digest, received and occurred timestamps, processing state.
- `integration_job`: cursor, attempt count, retry_after, failure kind, last_success and last_known_good snapshot.
- `order`: internal UUID, source account/ID, immutable imported reference, separate order/fulfillment/payment states.
- `order_line`: immutable external line identity, internal SKU mapping and quantities/amounts as exact decimals.
- `inventory_movement`: durable signed quantity delta with idempotent source operation key; reservations and holds scoped to stock location.
- `business_event/outbox`: durable event identity transactionally tied to original domain change.
- `operator_discrepancy`: conflict evidence, source versions, human decision and audit.

No new table is authorized by this file; review indexes/FKs, migrations, retention and data classification at task time.

## 3. Ingestion stages and event guarantees

1. Authenticated/authorized merchant connects provider with explicit scopes and reconnect rules.
2. Verify webhook signature and metadata **before** trusting payload; reject invalid source.
3. Persist authenticated source event identity and receipt in controlled tenant scope.
4. Normalize to typed provider-neutral snapshot; store unavailable fields as unknown rather than zero.
5. Resolve product/customer/order aliases deterministically; unresolved mappings go to review.
6. Create only idempotent canonical domain commands subject to business rules and permissions.
7. Commit internal state + audit + outbox atomically, then dispatch projections/notifications.
8. Retry at least once with same durable identity; DLQ and reconciliation for exhausted failures.
9. Give the merchant an explicit health view: last webhook, last sync success, stale/missing data, conflicts.

Ordering can be partial/out of order; do not assume provider sends exactly once. Runtime mutation must re-validate organization, branch and permission, not trust a webhook's label alone.

## 4. The hard boundary: one sale cannot become two

A sale from a connected POS may also appear as an online order if the provider mirrors its origin; **never** treat matching amount/time as a confirmed duplicate. Require explicit source mapping / reference evidence. Store both external receipts but create one canonical accounting/stock effect only when identity is verified. Unresolved collisions require reconciliation rather than speculative deletion.

Online order placement may **reserve** stock, but realization/refund occurs according to selected financial and fulfillment policies. Refund does not automatically restock perishable/damaged inventory.

## 5. Security and financial correctness

- Tenant/branch grants enforced on server and all writes; token refresh scoped to connection.
- External credentials encrypted, rotated, redacted, separated from web and logs.
- No client-side floating arithmetic, unrestricted AI SQL or mutable posted journal.
- No automatic new UUID retry for uncertain financial commands.
- Dedup persistence belongs to PostgreSQL, not expiring Redis only.
- Bounded payload size, provider rate limits, backoff, circuit-breaking and observability.
- Confirm ZATCA/PDPL/payment requirements for the merchant before claiming compliance.
- Support disconnect without corrupting historical invoices, journal and audit references.

## 6. UX and merchant control plane

- Onboarding asks online / physical / hybrid / services and enables only chosen implemented modules.
- Owner home first shows real organization and permitted activity; never fake sales or branch totals.
- Later real-time-looking cards must include source, timestamp and health indicator and allow drill-down.
- Operator sees: incoming orders, sync failures, duplicate candidates, stock conflicts, approvals.
- A branch staff member cannot see organization-wide finance by rendering a summary client-side.
- Accountant-only view has no terminal or shift dependency and must remain a first-class route.

## 7. Adapter acceptance gate

A proposed Salla/Zid/external POS adapter is **NOT RUN** until tested against a current permitted sandbox account: valid/invalid OAuth, signature, event duplicates, pagination, out-of-order events, malformed payload, data mapping collision, rate limit, revoke/reconnect, source health, authorization and reconciliation. Read-only is first milestone; writebacks are separate reviewed tasks with documented provider support. No success status based on mocks alone.

## 8. Decisions requiring explicit ADR before dependent work

- Canonical order vs invoice identity and accounting event boundary.
- Organization-selected catalog/stock/price system of record and conflicting writes.
- Reservation/cost/return policy for native vs external fulfillment.
- Merchant session switching semantics and cross-organization cache invalidation.
- Provisional/confirmed offline POS transaction and online reconciliation.
- Provider-specific fiscal/payment data storage and compliance.
- Subscription metering for branches/channels/AI without leaking merchant data.

**Next:** complete the ledger/invoice dependency first. Implement the integration substrate only after the canonical domain model and acceptance tests exist.
