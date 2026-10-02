# POS v1 — Delivery and Decision Plan

Status: REQUIREMENTS RECORDED; IMPLEMENTATION NOT STARTED.
Normative requirement baseline: [POS Transaction Flow v1](POS_TRANSACTION_FLOW_V1.md).
This is a subordinate POS delivery plan, not a second project roadmap. ENGINEERING/MASTER_ROADMAP.md is the sole project roadmap; governance PR #2 is adopted.
Owner authority: the supplied document is DECIDED — Foundation v1; examples/recommendations/configurable details do not select production policies.

## Historical source boundary — 2026-10-01

Observed 2026-10-01:
- Official main: 737facd48180d7920540f93032ba0a827c9d1ef2, README only.
- Foundation candidate PR #1: 42c33b761204c1195b686f2519e419d8bf979f7a.
- Governance adoption PR #2: 3ed9172c93f39b95a1ead6274af44656aa653481.
- Both PRs remain unmerged. This requirements change derives from main and does not promote either candidate.
- Local shell/runtime unavailable; repository API/MCP supports read/write/PR review.
- No application behavior, merchant pilot, provider integration, signing or deployment is qualified by this document.

## Canonical integration — 2026-10-02

Foundation #1 and governance #2 are merged into main. This integration starts from d1a148b8f30c4ceaf68f670dc8b4409e8b3ca3db; reverify live HEAD before implementation. The owner authorized continued development and reviewed merges. This is requirement adoption, not execution of POS-148 or selection of fiscal/provider/pilot policies.

Before application implementation, verify live state and use canonical application source or an explicitly owner-authorized development base. Review overlaps before any merge. Preserve the foundation's tenant/RBAC/audit/last-owner rules.

## Binding invariants

- Backend validates organization/branch/terminal/user/shift identities; UUID possession is not authorization (POS-004–008, 044, 109).
- One authoritative calculation contract; decimal money, one selected rounding/tax policy; no independently maintained client pricing logic (POS-012–032).
- CompleteSale requires authoritative captured allocation equal to amount due; tender and returned cash change are distinct from the captured amount (POS-035–044).
- Completed commercial/financial snapshots remain immutable; adjustments/refunds reference original records (POS-046, 054, 075–086, 101, 136).
- Completion state, required snapshots and SaleCompleted outbox insertion commit together (POS-044–053, 106). Printing and downstream analytics/AI do not gate checkout (POS-056, 103–105).
- Offline completion is locally durable and separately identified from server-confirmed completion. Replayed legitimate sales retain identity, price/config evidence and financial reality (POS-060–072).
- Refunds cannot exceed original captured funds; inventory return is an explicit eligible action (POS-079–085).
- Cash variance stays visible and attributable; business date follows selected branch-local timezone/cutoff rules (POS-092–098).
- Clients invoke commands; domain services own authoritative state transitions (POS-108–113).

## Required consistency diagnoses / ADRs before dependent implementation

These are engineering questions raised by the owner's rules, not overrides of them.

1. **Completion vs downstream profit timing:** POS-002/142 describe presentation/event flow; POS-046/047 require cost/profit/recipe snapshots at completion. An ADR must define the atomic snapshot boundary and asynchronous projections so no completed sale waits for analytics/AI or prints from live prices. Rule 46 cannot be postponed merely because a later projection event exists.
2. **External payment atomicity:** a provider capture cannot share a PostgreSQL transaction. Durable payment intents, provider idempotency, reconciliation and completion guards must cover capture success followed by response loss/database failure (POS-037–044, 106–107).
3. **Offline calculation without duplicate logic:** Python backend and Dart POS need one maintained calculation definition usable offline. Choose an implementable shared module/generation strategy; matching duplicated implementations alone does not satisfy POS-022. Use common decimal golden fixtures once policy is selected.
4. **Offline legitimacy:** document activation/credential/config validity, expiry, trusted device time/version evidence and rejection/review quarantine. Price/product/inventory mismatch cannot silently erase a legitimate sale. Server revocation must lock new sales without discarding queued history (POS-062, 069–072, 130–132).
5. **Durable idempotency:** offline identity and provider attempts need durable scoped uniqueness and request-content collision handling. An expiring generic retry key alone cannot guarantee never duplicating an old financial transaction (POS-063–068, 107, 125).
6. **Cash allocations:** capture amount must be amount allocated to the order; tendered cash and change are separate fields. Expected cash uses net cash retained, including the cash share of split payments (POS-035–042, 093).
7. **State gaps:** timeout UNKNOWN and decline FAILED may arise after provider authorization, while POS-111 is conceptual. Define valid provider outcomes and reconciliation transitions, plus held/reopened order representation and zero-total complimentary settlement, before implementing those commands.
8. **Offline snapshots/costing:** define whether cached recipe/cost values are valid for completion and how canonical cost evidence is established during import. Do not replace a completed price/cost snapshot silently. Corrections, if allowed, need explicit auditable records.
9. **Concurrent refunds/consumption:** serialize monetary capacity checks and apply durable consumer deduplication so concurrent refunds cannot exceed captured funds and event redelivery cannot consume inventory twice.

## Policy/configuration decisions still open

| ID | Decision | Owner document already fixes | Still needed before the dependent feature |
| --- | --- | --- | --- |
| D01 | Fiscal/tax model | Configured tax handling and applicable fiscal receipt fields | Pilot jurisdiction, inclusive/exclusive prices, rates/exemptions/effective dates, fiscal requirements |
| D02 | Rounding | Decimal arithmetic and one centralized policy | Currency scale, intermediate precision, rounding mode, item/order tax and discount residual allocation |
| D03 | Costing | Recipe, authoritative ingredient cost, packaging/direct variable cost; immutable historical snapshot | Costing method, recipe yield/units/version validity, tax treatment of profit revenue, offline cost evidence |
| D04 | POS authentication | Active identities, branch/role/terminal checks; PIN recommended | Employee identifier/PIN enrollment, attempt limits, secure verifier strategy, switch/re-auth and offline authorization validity |
| D05 | Permission limits | Approved/audited excess discount and configured refunds/overrides | Cashier/manager limits, approvals bound to exact action/amount/order, offline approval policy |
| D06 | Shift rules | Lifecycle, cash ledger and variance; one active terminal shift recommended | Employee handover, active-shift uniqueness decision, tolerance, held-order policy, offline closing/import review |
| D07 | Payment rollout | Multiple payments modeled; CASH default offline; adapter-authoritative cards | Whether split UI ships initially, actual provider/terminal, retry/reconciliation/refund capabilities |
| D08 | Numbering/time | UUID identity, unique human business numbering, business date/cutoff | Uniqueness scope, online/offline allocation strategy, timezone/cutoff policy and safe reinstall recovery |
| D09 | Offline admission | Durable ordered queue, snapshot preservation, no data loss, revoke lock | Device/credential/config validity windows, strict-stock policy offline, import review/recovery and audit permissions |
| D10 | Hardware/pilot | Vendor-neutral interfaces and printer failure after completion | Pilot devices/printers, receipt/fiscal format, reprint audit configuration, kitchen routing requirement |
| D11 | Price/config freeze | Price validity and snapshots; confirmed structure frozen until reopened | Transaction-time definition, quote expiry, reopen/reconfirm conditions and offline version evidence |

Examples such as SAR, 10% discount, 5 SAR tolerance, 04:00 cutoff and named card brands do not choose these settings. The user's document defaults manual price override to DISABLED and offline payments safely to CASH; it recommends PIN and WARNING_ONLY but does not force them for every merchant.

## Dependency slices and observable gates

Each slice is a dependency grouping, not permission for one oversized PR. Issue one bounded task/branch/PR per confirmed outcome. Map every task to rule IDs and acceptance cases.

| Slice | Work | Dependencies | Gate / evidence |
| --- | --- | --- | --- |
| P0 | Accept canonical foundation/governance; qualify lab; isolate session/audit repairs | Owner source decision, review and actual execution tools | Exact source, tenant/session regressions, disposable service tests, baseline reports |
| P1 | POS activation/login context, branch policy and shift ledger | P0; D04–D06 | Unauthorized login rejected; opening cash ledger and race-safe configured active shift rule |
| P2 | Versioned catalog/prices/modifiers/recipes/units and incremental cache | P0; price scope and D03/D11 | Active price precedence, modifier bounds, versioned cached snapshots; stale config cases |
| P3 | Shared decimal calculator, discount approval and local draft/confirmation | P1/P2; D01/D02/D05 | Common decimal fixtures; backend verification; instant local taps; immutable confirmation boundary |
| P4 | Cash payment, idempotent CompleteSale, snapshots and transactional outbox | P1/P3; D03/D06 | Replay/concurrency tests; no unpaid completion; atomic snapshots/event and net cash ledger |
| P5 | Inventory consumer and profit/owner projections | P2/P4 | Redelivery/crash tests; one consumption per sale; immutable profit; owner update after server confirmation |
| P6 | Hardware receipt printing, kitchen routing where chosen | P4/P5; D10 | Receipt from snapshots; printer failure cannot reverse sale; authorized reprint trace |
| P7 | Durable offline sale and ordered import/reconciliation | P1–P6; D08/D09; shared offline engine | Kill/restart/lost-response/replay tests; cash offline; retained rejected transactions; no duplicate financial/stock effects |
| P8 | Refunds/voids, explicit inventory return, holds and cash/shift close | P4/P5/P7; D05–D09 | Concurrent-refund bounds; return decision; audited variance and blocked unresolved payments |
| P9 | Card adapter and reconciliation, split UI if chosen | P4/P8; D07; actual test provider | Authoritative provider evidence, unknown/capture crash recovery; no blind retry or duplicate charge |
| P10 | Foundation POS acceptance and production-like qualification | All required selected pilot slices | Full POS-148 journey plus failure/security/runtime matrix on frozen source/artifacts |

Do not mark the complete POS core ready from a cash-only stub: POS-148 also requires inventory, profit, owner visibility, offline replay, refund and shift variance. Card-specific advertised functionality requires its own real adapter evidence; MVP UI scope decisions cannot weaken the payment model.

## Future and deferred surfaces

Tables/areas/guest counts unless required by pilots; KDS; reservation extensions; NFC/biometrics; customer display; forecasting/AI recommendations. Owner-profit surfaces stay separate from cashier checkout.
Development-agent role instructions govern engineering work; AI is not a checkout authority.
Telegram integration remains deferred by the owner's prior instruction.

## Evidence and project roadmap integration

The intake report belongs to ENGINEERING/REPORTS/POS_REQUIREMENTS_INTAKE.md.
The existing sole project roadmap links to this plan; maintain it there rather than creating another roadmap.
Examples are not runtime evidence. Acceptance starts NOT RUN and must be bound to actual tested source, actors, database/provider state, safe artifact identities and runtime.
