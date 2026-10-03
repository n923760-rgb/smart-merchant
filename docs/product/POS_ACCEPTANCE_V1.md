# POS v1 — Acceptance and Regression Matrix

Status: **ALL CASES NOT RUN**. This document specifies evidence to collect; no application acceptance is claimed.
Source: [owner requirements](POS_TRANSACTION_FLOW_V1.md).
Dependency and unresolved-policy register: [delivery plan](POS_DELIVERY_PLAN_V1.md).
Numeric examples are illustrative; selected tax/rounding/costing policies must define expected monetary assertions before execution.

## Applicability — 2026-10-03

This is the acceptance matrix for the optional POS module of the [general accounting platform](SMART_MERCHANT_MASTER_PROMPT_V2.md). It remains entirely NOT RUN. Add separate ledger/accounting/service-business acceptance; a service invoice must not need a cashier shift, terminal, recipe or stock movement. Activity examples do not define a required vertical.

## Minimum end-to-end gate — POS-148

Run on one frozen source with an activated terminal, scoped cashier/manager/owner, supported hardware and disposable production-like data.

1. Activate terminal; log in cashier; open shift and verify opening-cash ledger.
2. Sell product, apply valid modifiers/discount, accept cash and complete exactly once.
3. Generate/print completed-snapshot receipt; verify linked inventory consumption and profit snapshot.
4. Verify owner feed sees the server-confirmed sale without manual refresh.
5. Disconnect; complete another allowed cash sale locally; keep identity/sequence, immutable snapshots and durable sync queue.
6. Restart POS and reconnect; simulate replay/lost response; reconcile to one server sale and one downstream consumption.
7. Refund selected transaction under permissions; verify monetary bounds, refund trace and explicit inventory-return decision.
8. Close shift; assert expected/actual cash and visible variance under configured tolerance.

A screenshot of the success screen or a green unit suite does not prove this journey. Record source/artifact, device/runtime, users/roles/tenant/branch/terminal/shift, command/provider identities, safe before/after evidence and observed result.

## Scenario matrix

| Case | Rules | Required proof | Initial status |
| --- | --- | --- | --- |
| A01 — login and tenant context | POS-003–008, POS-114, POS-127, POS-130–132 | Reject inactive user/membership/branch access/role/terminal and cross-tenant identifiers; no raw password/PIN exposure; valid cached access per selected offline policy | NOT RUN |
| A02 — shift opening concurrency | POS-006–008, POS-090–098, POS-112 | Atomic opening ledger, configured active-shift uniqueness, retained opening amount, rejected invalid shift operations and administrative cancellation | NOT RUN |
| A03 — local catalog interaction | POS-009–014, POS-019–021, POS-121–129, POS-137–140 | Immediate local tap/update, valid product/variant/version/price precedence, barcode ambiguous/not-found handling, configured order type and unique numbering | NOT RUN |
| A04 — modifiers and recipe quantities | POS-011, POS-016–019, POS-047–050, POS-144 | Enforce min/max/required selections; snapshot modifier prices; notes alone do not alter recipe; quantity scales units/recipe/packaging | NOT RUN |
| A05 — stock policy | POS-014–015, POS-048–050, POS-071–072 | STRICT vs WARNING_ONLY per policy; no cart-tap consumption; legitimate offline import retained with negative-stock alert | NOT RUN |
| A06 — decimal calculation | POS-012–013, POS-017, POS-022–026, POS-032, POS-143–145 | Shared calculation contract runs with decimal values; selected inclusive/exclusive taxes, rounding and residual-allocation golden fixtures agree across clients/backend/receipts/reports | NOT RUN |
| A07 — discounts and overrides | POS-026–030, POS-114 | Permission limits, bound manager approval/reason/audit, explicit free-item reason, manual override disabled by default; rejected unauthorized/self-escalating actions | NOT RUN |
| A08 — confirm/reopen/cancel/hold | POS-031–033, POS-073–076, POS-086–089, POS-108–110 | Domain-owned transitions; structure frozen; selected reopen/reconfirm and zero-total policy; approved cancellation; no deletion of captured sale; held/resumed/expired order trace | NOT RUN |
| A09 — cash and split allocations | POS-034–036, POS-040–043, POS-093 | Due 47, tender 50, change 3 gives captured allocation 47 under fixture policy; reject cash shortfall unless split; cash+card shares sum exactly to due | NOT RUN |
| A10 — payment provider outcomes | POS-033–043, POS-075–076, POS-106–107, POS-111 | Durable attempt/idempotency; success only from authoritative adapter; failure preserves payable order; UNKNOWN reconciled before retry; no unproven void/capture | NOT RUN |
| A11 — capture/completion crash | POS-037–044, POS-053, POS-106–109 | Capture succeeds then connection/database fails; recovery reconciles original attempt; repeated completion gives one sale; no completed order without authoritative payment | NOT RUN |
| A12 — financial snapshots | POS-013, POS-017, POS-044–047, POS-101, POS-133–136 | Completed price/discount/tax/cost/profit/recipe snapshot immutable; later catalog/cost updates do not alter receipt or historical profit; audited correction path only if explicitly supported | NOT RUN |
| A13 — outbox and consumer replay | POS-048–053, POS-099–107, POS-142, POS-150 | Completion and outbox atomic; consumer crash/redelivery cannot duplicate inventory/projections; analytics/notification/AI failure cannot block sale | NOT RUN |
| A14 — receipt and hardware | POS-054–059, POS-091, POS-119–120, POS-123–126 | Snapshot-derived receipt, selected fiscal fields, unique number scope, vendor-neutral interfaces, failure/reprint result separate from sale, optional reprint audit/drawer detection per configuration | NOT RUN |
| A15 — local crash durability | POS-060–065, POS-127, POS-130, POS-132, POS-146 | Kill during local confirmation/payment/completion/enqueue; recover consistent durable order, payment/sequence/queue; no completed receipt without recoverable local sale | NOT RUN |
| A16 — sync replay and ordering | POS-063–068, POS-107, POS-113, POS-146 | Lost server response and resend return original ID/result; terminal sequence persists across restart; same identity with changed payload is investigated/rejected without overwriting original; oldest-first retry/backoff per policy | NOT RUN |
| A17 — offline configuration conflicts | POS-012–015, POS-046–047, POS-069–072, POS-129–132 | Legitimate cached-price 18 sale stays 18 after price 20 change; disabled-product and negative-stock import retain financial reality with mismatch audit/alerts; invalid legitimacy quarantined, never silently deleted | NOT RUN |
| A18 — revocation/authorization import | POS-004–005, POS-060–072, POS-130–132, POS-135–136 | Reconnect revoked device locks new sale capability; authorized reconciliation retains unsynced history; cached credential/config expiry and clock/version proof obey selected policy | NOT RUN |
| A19 — refunds and reversal | POS-075–085, POS-107, POS-110–111, POS-147 | Partial/full/item refunds, authority and reason/approval trace, provider reconciliation; concurrency cannot over-refund; refund replay cannot reverse twice | NOT RUN |
| A20 — refund inventory and replacement | POS-080–086, POS-133–136 | Refund never auto-restocks; eligible RETURN_IN references refund and deduplicates; consumed meal stays consumed; replacement/complimentary order preserves original | NOT RUN |
| A21 — cash movement and closing | POS-007–008, POS-090–096, POS-112 | Opening + net cash sales + cash in - cash refunds - cash out; actual minus expected variance retained; reasons mandatory; unresolved payments block close under selected policy; above-tolerance approval trace | NOT RUN |
| A22 — business date and numbering | POS-009, POS-063–064, POS-097–098, POS-124–126 | Selected branch timezone/cutoff across midnight/boundaries; created_at distinct from business_date; offline/restart/parallel numbering cannot collide | NOT RUN |
| A23 — cashier UX and diagnostics | POS-001–002, POS-010, POS-103–105, POS-115–119, POS-127, POS-137–141, POS-149 | Tap/pay flow, actionable categories, network/sync state, durable failed count, no stack traces/tokens, no profit/AI management UI in cashier checkout | NOT RUN |
| A24 — owner visibility and traceability | POS-046–053, POS-099–102, POS-133–136, POS-141–145, POS-150 | Tenant-authorized owner feed after canonical confirmation; order→payment→shift→terminal→inventory→profit→refund trace and immutable historical projections | NOT RUN |
| A25 — full pilot journey | POS-148 plus affected rules above | Complete activation-to-offline/replay/refund/shift-close journey on frozen source with safe attributable browser/device/hardware/server evidence | NOT RUN |

## Future/conditional acceptance

Table/area/guest entities (POS-021), reservations (POS-050), KDS (POS-059), NFC/biometrics (POS-003), customer display (POS-123), optional card/split UI and hardware-specific detection must be explicitly scoped for the pilot. Mark SKIPPED only with an applicable scope/configuration reason; required architectural support remains governed by the owner requirements.

## Result recording

For each executed case retain task/case IDs, rule IDs, exact source/artifact, executor, selected policy/version, safe commands/results, failure injection, expected/actual behavior and evidence location.
Use PASS / FAIL / BLOCKED / UNKNOWN / NOT RUN / SKIPPED truthfully. Bind provider evidence to actual provider attempt IDs without credentials/card data.
No real customer, production database or paid-provider operations are authorized by this acceptance plan.
