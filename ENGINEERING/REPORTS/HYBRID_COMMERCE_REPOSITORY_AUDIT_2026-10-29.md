# Repository-wide engineering audit — Hybrid Commerce V6
**Audit date:** 2026-10-29
**Repository:** n923760-rgb/smart-merchant
**Observed main:** `07dfd1e84ad978c33ae7dbdce5c9a6ee9294e86a` (merge of #19)
**Scope/method:** enumerated full Git tree (301 entries, non-truncated); reviewed active product, architectural, governance, security, deployment and CI documents, backend API/accounts/RBAC/auth/migration, web BFF/session/navigation/accounting/overview, Flutter POS/owner shells, worker/event stubs and representative tests. This is a **structured repository audit**, not a claim of manually inspecting every line or executing all tests locally. No live business data or production access used.

## Executive findings

| Area | Observed behavior | Hybrid V6 gap | Priority |
| --- | --- | --- | --- |
| Repo/build governance | Single roadmap, AGENTS, ADRs, task packets, Foundation/Governance/Accounting Web CI, extensive tests | Ensure V6 dependencies and acceptance stay in single roadmap; prove branch protection/current CI | P0 |
| GitHub browser CI | `ubuntu-latest` resolved to Ubuntu 26.04; Playwright 1.55.1 rejects Chromium install before browser execution on V6 doc PR | Pin supported runner instead of masking failed tests; isolate fix in #21 | P0 **BLOCKER** |
| Identity/tenancy/RBAC | Organization/membership/branch-aware backend and tests; shared user/branch/terminal CRUD | Merchant onboarding modes, cross-channel roles, scoped business events; test all new endpoints | P0-P2 |
| Web BFF/session | HttpOnly cookie BFF, context binding, bounded transport, cross-tab refresh controls | Owner UI needs safe organization switch (currently auto selects first active membership), clearer operational role journeys | P1 |
| Accounting | Decimal balanced posted journal, reversible, immutable SQL-level invariants, confirmed UI command and result recovery integrated | Account hierarchy, periods, opening balances, invoices/AR/AP/document posting, reconciled reports | **P1 BLOCKER for sales** |
| Current overview | `overview/page.tsx` only shows organization name and generic text | No trusted business pulse, no active tasks or linked orders; first bounded factual UX offered in #22 | P1 |
| Owner mobile | Flutter sign-in/session and home/account shell, no reliable business metrics | Genuine authorized owner views after API/projections exist | P2 |
| Native POS | Flutter device state and local foundation tables; transaction contract POS-001..150, acceptance not run | Real sale/shift/receipt/stock/payment/offline recovery and physical hardware | P2 |
| Catalog and inventory | No production catalog/stock domain, only skeleton directories | Canonical product/SKU/source mappings; movement ledger, reservations and cost/stock policy | P2 |
| Orders and omnichannel | No operational sales/order domain or external adapters | Canonical source identity, ingestion dedupe, workflow, read-only first integration and reconciliation | P3 |
| Event/worker framework | `DomainEvent` shape and worker heartbeat only | Durable outbox/inbox, queues, retry, dead-letter, sync health and bounded commands | P3 prerequisite |
| UX/design system | RTL web shell, utilitarian CSS, simple navigation; design_tokens package is a placeholder | Role-adaptive shell, responsive merchant command center, design tokens, accessibility and empty/error states | P1-P4 |
| Financial compliance | Scope and ZATCA guidance documented; no production fiscal qualification | Per-merchant tax/fiscal policy, device/SDK/issuer evidence, official acceptance | P5 |
| Deployment/operations | Compose development stack; infrastructure backup/monitor folders are placeholders | Production credentials, backup/restore, metrics, alerts, rollback/capacity testing for shared VPS | P5 |
| AI/merchant tools | Not operationally implemented | Allowed tools and approval workflow, barcode/label/picking/quotation modules after source data | P4 |
| Pricing/merchant go-to-market | Product hypotheses in V2/V6 | Real pilots for online-only/physical-only/hybrid/services and subscription-cost validation | P5 |

## Critical evidence / source paths

- `AGENTS.md`; `governance/START_HERE.md`; `ENGINEERING/MASTER_ROADMAP.md`; `docs/adr/0010-general-accounting-core.md`; `docs/adr/0012-confirmed-journal-command.md`
- `backend/app/api/routes.py`: auth, organizations, branches, users, roles, terminals, audit; not commerce orders.
- `backend/app/domains/accounting/{models,routes,service}.py` and `backend/migrations/versions/0002_accounting.py`: financial foundation; no invoice lifecycle yet.
- `apps/web/{components/shell.tsx,app/(dashboard)/overview/page.tsx,lib/session.ts}`: original overview placeholder; session and org automatic selection.
- `apps/pos/lib/main.dart`: only durable device/config/session foundation; NOT a transactional offline POS.
- `backend/app/workers/main.py`: heartbeat, no genuine operational worker tasks.
- `backend/app/events/base.py`: event interface only; no durable outbox/inbox.
- `apps/owner/lib/main.dart`: owner/auth shell; no verified aggregated reporting.
- `infrastructure/backups/.gitkeep`, `infrastructure/monitoring/.gitkeep`: no tested production restore/monitor in repo.
- `.github/workflows/ci.yml`, `.github/workflows/accounting-web.yml`: Playwright installs pinned at 1.55.1 under rolling runner.
- `docs/product/POS_TRANSACTION_FLOW_V1.md`, `POS_ACCEPTANCE_V1.md`: existing POS constraints and explicit NOT RUN gates.

## CI root cause and limited corrective change

On V6 scope doc-only PR #20, run IDs `40797333536` (Foundation) and `40797333619` (Accounting Web) attempted Playwright Chromium installation; job logs show:
`ERROR: Playwright does not support chromium on ubuntu26.04-x64`.
Failure is runner compatibility **before** browser execution, so neither browser behavior nor accounting correctness can be concluded from these failed jobs. The separate PR #21 pins only browser-dependent jobs to Ubuntu 24.04; final test results/merge must be checked on the exact new SHA. Do not mark browser E2E as PASS based on compilation/other green jobs alone.

## Product-first UX boundary

The initial V6-compatible owner experience should start from verified organization, allowed branch listing and permission-scoped audit events, not fake sales, offline stock or unconnected providers. PR #22 builds that limited home on top of #21 and leaves accountant-only landing intact. Further sales/fulfillment cards must wait for live canonical documents, cross-channel projections and freshness evidence.

## Required domain design decisions before code expansion

1. **Identity across systems:** internal organization and provider connections; unique `(organization, provider, source_account, external_entity_type, external_id)`, collision policy, migration.
2. **Authority matrix:** seller's selected system of record for catalog, pricing, stock, order, payment, accounting journal; read-only as first bridge.
3. **Order effects:** canonical orders and lines, distinct fulfillment/payment/sync statuses; avoid doubled financial/stock events when POS is imported and same checkout appears upstream.
4. **Inventory ledger:** on-hand/reserved/available, atomic holds, outbox plus cross-source discrepancy review; do not mirror stock both ways without conflict policy.
5. **Financial document path:** service invoice → receipt/partial receipt → receivable → journal → reconciled report; immutable/auditable adjustments and eligible ZATCA path.
6. **Role/organization UX:** organization switch must coordinate cookie context rotation and query cache invalidation; no cross-org cached dashboard results.
7. **Worker durability:** durable event identity, PostgreSQL outbox/inbox, at-least-once delivery and idempotent consumers; make Redis ephemeral, not finance identity source.
8. **Operational telemetry:** source and event received time, freshness SLA, replay/dedup counts, failure/Retry queue, human resolution.

These are proposed design constraints to record in ADRs before implementation where existing policy does not already specify a decision.

## Recommended bounded execution, not a big-bang rewrite

**First:** qualify and integrate CI runner correction #21 with browser/real-ledger tests, then V6 docs #20 and truthful home #22 after their own full checks. Preserve PR dependency and source evidence.

**Second:** SM-ACC-004 source check and task packet: scoped account hierarchy/period-close/opening balances (do not combine with hybrid adapters). Test organization/branch authorization, close/write race, DB constraints and deterministic journal replay.

**Third:** complete one real service invoice through partial/full receipt, AR and reconciled report, with no POS requirement.

**Fourth:** optional native POS and inventory, then one read-only storefront connector, followed by external POS and additional connectors after proof of nonduplication and reliable recovery.

**Fifth:** actual merchant pilots, product UX, compatibility, fiscal/provider, privacy/security, backup/restore and final release gates.

## Audit limitations

No full repository clone or local runtime test was performed here; this review relied on GitHub's current tree, file contents and hosted CI logs. Every new claim of PASS must cite an exact commit and run. Do not quantify overall completion percentage from file counts or this structural audit. No customer/financial records, external merchant credentials, VPS deployment or production resources were touched.
