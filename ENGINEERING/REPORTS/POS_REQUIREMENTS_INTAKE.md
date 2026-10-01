# SM-POS-001 — Owner POS v1 Requirements Intake

Observed: 2026-10-01 UTC.
Repository: n923760-rgb/smart-merchant.
Verified official main: 737facd48180d7920540f93032ba0a827c9d1ef2.
Foundation PR #1: 42c33b761204c1195b686f2519e419d8bf979f7a.
Governance PR #2: 3ed9172c93f39b95a1ead6274af44656aa653481.
Execution: repository API/MCP; no shell/runtime.

## Authority and scope

Owner supplied “POS Transaction Flow & Business Rules v1”, status DECIDED — Foundation v1, for restaurants/cafés while asking to continue building Smart Merchant.
This round records that baseline and derives delivery/acceptance documents. It does not authorize merge, paid provider operations, production fiscal identity, signing, deployment or application-base promotion.
Telegram remains deferred.
One documentation branch/PR from official main; no edits to pending PR #1/#2 or competing roadmap.

## Output

- docs/product/POS_TRANSACTION_FLOW_V1.md: structured transcription with all 150 original rule numbers and POS-001–POS-150 trace IDs. Compact prose/layout are normalized; not a byte-for-byte chat archive.
- docs/product/POS_DELIVERY_PLAN_V1.md: subordinate dependency slices, invariants, policy register and consistency diagnoses.
- docs/product/POS_ACCEPTANCE_V1.md: original POS-148 journey plus 25 required regression/evidence groups.
- This report: source/authority/provenance and truthful execution boundary.

## Facts

The owner fixed deterministic sale flow, backend authority, decimal money, immutable financial snapshots, outbox completion, durable offline identity/import, refund/payment bounds, cash reconciliation and separate cashier/owner surfaces.
The document also labels some behavior as recommendation, example, future or configurable. Such values do not become new defaults.
Official main still contains README only; foundation/governance candidates remain separate.

## Inferences requiring diagnosis

Shared offline/server calculation mechanism, provider/DB reconciliation, completion/profit-event timing, offline legitimacy/cost snapshot admission, held/reopened/zero-total/payment transitions and durable replay/consumer uniqueness need concrete contracts before their dependent implementations.
These diagnoses preserve the owner's rules; they do not amend them.

## Validation and evidence

Static API-session review: all rule IDs 001–150 appear exactly once; acceptance/delivery references target existing IDs; relative Markdown links resolve to planned files; expected added paths and full diff reviewed.
Local builds/tests, application runtime, provider/hardware/device tests: NOT RUN; this round changes documentation only and has no shell.
Governance CI from PR #2 is not evidence for this separate source. Main has no workflow; CI availability is checked after opening this PR.
Initial acceptance cases remain NOT RUN.
Record final branch/head/PR in PR metadata after creation; commits cannot contain their own resulting SHA.

## Remaining work

Review/merge requirements and governance under owner authority; resolve canonical application source; qualify lab; select the policy details needed for the first dependent slice; execute one bounded task at a time against live source.
Existing project roadmap is in PR #2. Reconcile it with these adopted POS requirements after governance/source decisions instead of silently copying or editing the pending roadmap.
