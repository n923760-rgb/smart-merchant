# Smart Merchant — V6 Hybrid Commerce Gap Review

**Review date:** 2026-10-29  
**Observed source:** main commit 07dfd1e84ad978c33ae7dbdce5c9a6ee9294e86a (merged PR #19).  
**Method:** repository README, AGENTS.md, sole roadmap, V2 master prompt, architecture, ADR 0010/0012, POS delivery plan, confirmed composer report, recent GitHub commits and current open PR search.  
**Scope:** document/product gap review; **no code implementation, runtime execution or fresh CI qualification** during this review. The repository's historical tests are attributed only to their historical SHAs.

## 1. Evidence-backed state

| Capability | State at observed source | Evidence / boundary |
| --- | --- | --- |
| Organization, branch, authentication, scoped RBAC and audit foundations | Implemented foundation | README and architecture; physical/production checks not established here |
| Decimal SAR double-entry ledger, account records, immutable posting/reversal, scoped request identity | Implemented foundation | ADR 0010 and README; hierarchy/periods/invoice posting not included |
| Explicit web journal confirmation and uncertain-result recovery | Source merged | PR #19 at main 07dfd1e; ADR 0012 and composer report; not offline accounting |
| Account hierarchies, period close, opening balances | Not yet accepted | Sole roadmap next; no completed implementation evidence in inspected sources |
| Service/product invoices, settlements, AR/AP, suppliers, expenses, financial reports | Not yet accepted | README says invoicing/reporting unimplemented; needs end-to-end finance journey |
| Catalog, option mapping and operational inventory | Not yet accepted | README; no completed live capability evidence |
| Native operational POS sale, offline, printing, refunds | Not yet accepted | Flutter POS/owner shells; POS delivery plan says implementation not started; POS-148 NOT RUN |
| Salla / Zid / external POS integrations | New V6 scope, NOT RUN | No verified adapters or contracts in inspected source |
| Hybrid orders, inventory conflict handling, external identifier mapping | New V6 scope, NOT RUN | Requires catalog/orders/inventory foundation and adapter policy |
| Cross-channel owner pulse, tasks, workflows, AI | Planned, NOT RUN | No data-backed hybrid source acceptance in inspected source |
| Merchant pilot, fiscal, payment-provider, physical hardware and production release | NOT RUN / unqualified | Explicit historic roadmap and README boundaries |

**Important:** This is a status classification using current repository documentation and merged-source review; not a quantified project completion percentage and not a claim that all files and live providers were tested.

## 2. Scope alignment and conflicts avoided

- Owner's V6 direction adds hybrid commerce **on top of** general accounting. It does not override the approved 2026-10-03 accounting-only capability or require stock/POS for service invoices.
- V6 includes both **native POS** and **external POS connectors**. Do not silently replace the native option or mandate an external vendor.
- The old V2 master remains a financial/technical invariant reference. V6 is the new hybrid product scope. ENGINEERING/MASTER_ROADMAP.md remains the sole implementation sequence.
- POS-001 through POS-150, especially POS-148, are preserved; no changes to tax, rounding, payment-provider or offline policy are implied by this documentation.
- No new production pricing, launch readiness, live payment/PSD2/ZATCA status, marketplace partner approval, or Shopify/Salla/Zid capability is asserted.

## 3. Product gap priorities / dependency logic

| Priority | Candidate bounded work | Dependency | Evidence of completion |
| --- | --- | --- | --- |
| P0 | Preserve/record V6 scope, keep one canonical roadmap | Observed main, review | Product doc, gap report, roadmap pointer, reviewed PR |
| P1 | Account hierarchy, accounting periods and opening balances | Current ledger and ADR 0010 | PostgreSQL migration, branch/tenant negative tests, period restrictions, exact numbers, CI |
| P1 | Document financial lifecycle: service invoice, partial/full receipt, AR and deterministic journal/report | Account/period policy | End-to-end accounting without POS/stock, exact balances, duplicate-request tests |
| P2 | Catalog/products/services and inventory ledger; native POS acceptance | Financial contract and POS invariant decisions | POS-148 incl offline/print/return; physical hardware and restore gates |
| P3 | First read-only online channel + source/event mapping | Canonical catalog/order identities and RBAC | OAuth/webhooks verified, retry/dedupe tests, dashboard freshness, no duplicate sales |
| P3 | Additional marketplace and external POS adapters | First adapter reliable and capability review | Two independent provider failure/recovery and reconciliation scenarios |
| P4 | Workflow/exception center, label/picking tools, AI | Trusted domain events and verified calculations | Reproducible action flows, approvals, no unauthorized mutation |
| P5 | Pilot and commercial readiness | All applicable runtime, fiscal and data protection gates | Merchant observations, device runs, data restoration, provider signoffs |

## 4. Next implementation task recommendation — SM-ACC-004 (proposal only)

**Outcome:** bounded accounting hierarchy/period/opening balance policy and implementation work, as already sequenced by the canonical roadmap. Do not combine with new connector or POS implementation.

**Before implementation:** check current HEAD, PRs, previous composer CI and migration state, permissions, account tree model and branch policies. Decide how periods and opening balances behave across an organization and branches in an ADR if unresolved.

**Must preserve:**
- Organization and branch RBAC; no terminal/shift dependency.
- Debit/credit exactness and immutable posted journals.
- Explicit reversal and durable same-request identity.
- Historical posting reads and period/close behavior consistent with policy.
- Database-level constraints as well as API/UX validation.

**Acceptance proposal:** opening balances reconcile; attempted posting into a closed period is refused in both API and transactional/database enforcement; allowed posting/reversal according to documented period policy behaves deterministically; concurrent requests cannot bypass close; rollback/migration and tenant/branch tests pass on exact task source. A separate subsequent bounded task handles full invoice/receipt lifecycle.

**Task packet authority:** this report is not a task packet nor a code-change authorization; create a scoped packet and validate under governance prior to implementation.

## 5. Review and operational follow-up

Do not mark PR #19's source merge as production acceptance. Verify its exact workflow results independently if current hosted evidence is needed. Once V6 docs are reviewed, start with the finance dependency, then test user-facing workflows before implementing hybrid adapters. No real merchant data, live tax/payment credentials, production infrastructure changes, or automated merges are involved in this documentation change.
