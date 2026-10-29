# Smart Merchant — Hybrid Commerce OS — Product Master V6.0

**Status:** Owner-approved product direction, 2026-10-29. Not an implementation or release acceptance.  
**Repository:** https://github.com/n923760-rgb/smart-merchant  
**Product:** مساعد التاجر الذكي / Smart Merchant Assistant  
**Positioning:** نظام واحد، أجهزة متعددة، مرجع واحد.

## 1. Decision and document precedence

Expand the existing general-accounting and optional-POS platform into a **hybrid, multi-channel merchant operating system** for online merchants, physical retailers, hybrid merchants, wholesalers, and service businesses. Support a merchant that wants only accounting, only an operations dashboard using external providers, a native POS, or combinations thereof.

This is a product-scope expansion, **not** authorization to replace the accounting core or to implement all modules concurrently.

- ENGINEERING/MASTER_ROADMAP.md remains the **only execution roadmap**; integrate new dependencies into it, never start a competing roadmap.
- Preserve root AGENTS.md, governance contracts, ADRs, existing database rules and POS-001–150 plus POS-148 acceptance.
- The approved general-accounting principle of SMART_MERCHANT_MASTER_PROMPT_V2.md remains binding: invoicing/accounting/services do not require a terminal, cashier shift, stock or an industry.
- This V6.0 controls **new hybrid product scope and user experience**; for underlying financial, security and POS technical invariants, existing stricter ADRs and acceptance contracts are not weakened. Record any genuine conflict in an ADR before dependent implementation.
- Historical reports and CI results are source-specific evidence, not current product qualification.

## 2. Product principles and competitive distinction

**High capability internally; minimal cognitive load externally.** The distinctive value is to connect signals and operations across channels and turn verified events into actionable work — not simply to present another sales dashboard.

1. One tenant-safe business core, optional modules and gradual adoption.
2. Never force merchants to leave Salla, Zid, their existing POS or accounting system.
3. Native POS **and** supported external-POS adapters, neither replacing the other.
4. Functional views by organization, branch, role, merchant type and permission.
5. Accurate provenance, timestamps, freshness, source of truth and reconciliation.
6. Server-side permission enforcement, financial immutability, reliable idempotency.
7. No untested button, fake metric, mock integration or "instant" label for stale data.
8. Arabic-first UX and correct RTL; English, light/dark and accessible responsive layouts.
9. No module or configuration burden for businesses that do not use that module.
10. AI assists within authorized workflows; it never invents ledger figures or makes unapproved critical changes.

## 3. Users and merchant modes

Merchant modes: **online**, **physical**, **hybrid**, **services**, optionally **wholesale**. A merchant can switch modes as the business grows; this toggles modules and onboarding, not a separate database or codebase.

Roles:
- **Owner:** executive command center, cash position, decisions, alerts, branches and permissions.
- **Manager:** assigned orders, inventory, staff tasks, approvals and branch operations.
- **Cashier:** sales, scans, returns and shift status with very few distractions.
- **Accountant:** invoices, receipts, journal, payable/receivable, periods and reconciled reports with no POS dependency.
- **Warehouse/order staff:** picking, barcode verification, transfers and receiving.
- **External accountant / support:** bounded grants, visible audit and limited tenant access.

Show only relevant, implemented and permitted modules. The server must refuse unauthorized API requests even when a navigation item is hidden.

## 4. UI/UX — adapt surfaces instead of crowding one dashboard

### Onboarding
A short organization wizard asks for activity mode, selected modules, first branch, import/connect source and initial owner dashboard. Do not require a terminal, warehouse, external integration or fiscal connector when not applicable. Provide progressive disclosure and resumable setup.

### Owner command center ("نبض النشاط")
- Verified daily sales split by channel, branch and source; separate order counts from paid/settled amounts.
- Orders and exceptions: new, assigned, delayed, returned, awaiting settlement.
- Action queue: stock shortage, failed sync, overdue orders, pending discounts, overdue receivables.
- Permission-scoped activity feed: who/what/when/source/branch/status.
- Cost and profitability **only when source data covers required costs and rules**. Show "insufficient data" rather than a fictional profit.
- Refresh timestamp, last sync, source quality, stale/partial-data labels and click-through to authoritative records.
- Activity cards open the relevant real workflow; alerts can assign a task, resolve, or explicitly escalate.

### Role-specific shell
Navigation should start simple: owner [home, operations, products, more], manager [operations, stock, team, more], cashier [new sale, orders, returns, till], accountant [finance, documents, reports, more]. These are UX hypotheses to test with actual users, not permission boundaries.

Require RTL, readable Arabic typography, responsive mobile/tablet/desktop, light/dark, accessibility, keyboard focus, empty/loading/error states, safe confirmation patterns and clear offline/sync labels.

## 5. Shared business core and module contracts

### Accounting (nonoptional common domain)
Chart of accounts, immutable balanced journals, explicit reversal, opening balances, accounting periods, customers/suppliers, service/product invoices, AR/AP, expenses, cash/receipts/payments, purchase documents, ledger-reconciled reports and per-merchant eligible tax/fiscal scope. Exact-decimal money, transaction-atomic posting, permanent request identity, no unapproved alteration of posted records. Preserve ADR 0010 and ADR 0012.

### Catalog
Products, services, non-stocked items, variants, modifiers, SKU, internal barcode, source aliases, units and conversions, images, tax category, price lists, bundles, Excel/CSV import with preview. Source IDs are tenant-scoped. A merchant may maintain internal and external catalog views, but editing rights and ownership must be explicit.

### Inventory (optional)
Warehouses/branches, stock movement ledger, available/reserved/on-hand/incoming, stock transfer, counting, receiving, returns and adjustments. Optional batches/expiry/weighted goods as sector extensions. Never directly overwrite on-hand quantity on a concurrent external event. Decide and test inventory cost policy before financial posting.

### Orders (optional operational module)
Canonical order identity with separate per-channel external mapping; line items, source, fulfillment, payment/settlement, cancellation, return, pick-up, delivery and refund status. Source order import must not duplicate the customer, the sale, stock effects or accounting entries. Preserve original identifiers and provenance.

### Native POS (optional, not replacement for external POS)
Android/Flutter native flow, fast cart, barcode scan, products, discounts with grants, shifts, cash ledger, returns, receipt printer, cash transaction proof, accounting/stock link, safe offline commands where explicitly qualified. Existing POS-001–150 remain authoritative and POS-148 must pass before claiming POS readiness. Card/SoftPOS require verified provider support and payment reconciliation; a mobile app alone is not a certified card terminal.

### Merchandising tools (individually activatable)
Batch label/barcode/QR printing, scan-to-pick fulfillment, quotation-to-order, catalog/menu QR, bulk product preparation and AI descriptions. Internal barcodes are not substitutes for officially licensed GTIN when required. QR or PDF creation alone does not constitute ZATCA compliance.

### Tasks, alerts and workflows
Typed business events -> configurable rules -> bounded notifications/tasks/approval actions. Actor/organization/branch identity and final result are auditable. Alerts with missing evidence must say so; all mutations recheck server authority. Delivery retries are idempotent.

### AI assistant
Explain verified business signals, summarize activity, assist with product descriptions and quotations, propose authorized actions. Calculations always originate from deterministic business engines. No raw unrestricted SQL, cross-tenant retrieval, silent stock/price/financial writes or AI dependence for checkout; enforce quotas and cost caps.

## 6. Integration Hub and data ownership

Target **first** a read-only, formally authorized connector for a selected online platform after core dependencies. Expand to Salla, Zid, supported external POS and other ERPs/marketplaces by tested adapter. Support Excel/CSV/manual entry when no API exists.

Each adapter must define:
- Official auth/OAuth and token handling, webhook verification, least-privilege scopes.
- Capabilities table: what can be read, written, subscribed to and reconciled.
- Tenant/source/object identities, mapping and exact upstream provenance.
- Initial snapshot and incremental ingestion, cursor/pagination/rate limits.
- Signature/dedupe/ordering handling, outbox/inbox, queue, retry/backoff and dead-letter.
- Per-entity or per-field system of record, permitted write direction and conflict policy.
- Reconnect/deauthorize, retries and actionable failed-sync status.
- Observable event → canonical domain command → durable effect → resulting projection.
- Import preview and discrepancy review before risky or destructive updates.

No blind bidirectional stock mirroring; no assumed real-time guarantee. Channel reports must indicate sync freshness. Do not count a POS sale and imported order twice if they represent the same commercial transaction. External providers may restrict operations; no adapter is declared supported until its real API contracts and permissions are checked.

## 7. Critical invariants and reliability

- All business queries and commands are scoped by organization ID, active membership and explicit branch grant.
- Unique external source mapping under organization/provider/entity identity.
- User/client UUID possession is not authorization; repeat commands require immutable normalized request identity.
- Financial, payment, stock and order commands are atomic within their authoritative boundary; external payment capture is separately reconciled.
- Never coerce money to binary floating point.
- State transitions, event outbox and audit append occur atomically whenever they must agree.
- Do not auto-resend a financial command of unknown result under a new request ID.
- No implicit offline accounting journal posting; qualify offline POS separately with durable local queue and testable conflict recovery.
- Failure of printer, email, analytics, notification or AI does not rollback an authoritative completed sale.
- Approval, user and source scopes must be enforced server-side and logged with secrets redacted.
- No unverified release claims for ZATCA, PDPL, PSP, physical devices, printers, migrations or pilots.

## 8. Technical architecture (preserve, do not replace)

Modular monolith: FastAPI, PostgreSQL transactional authority, Redis ephemeral/queue, Alembic migrations, Next.js server/BFF web, Flutter owner/POS shells. Consider local SQLite/Drift for qualified offline POS workflows only. APIs and adapters are versioned contracts; use S3-compatible attachments when qualified; no microservice rewrite.

Suggested bounded domains: identity/organizations/branches/RBAC, accounting, billing, payments, catalog, inventory, orders, POS/shifts, integrations/mappings/sync, customers/suppliers, purchasing, tasks/workflows, reporting/projections, notifications, files, AI, subscription/support, audit.

Production setup should prioritize logical isolation and resource limits on the existing VPS if capacity tests support it, with separate database credentials, backup/restore drills, isolated deployment and monitoring. Additional hosts are not a default requirement.

## 9. Phased delivery and release gates

**P0 — Current-source diagnosis and scope governance:** verify HEAD, open PRs, architecture, ADRs, AGENTS.md, roadmap, tests; record delta and gap matrix. Attach V6 as product scope, preserving the single roadmap. No claimed implementation from this documentation.

**P1 — General business/financial core:** account hierarchy, period policies/opening balances, customer/supplier subledgers; service invoice -> partial/full payment -> receivable -> exact journal -> reconciled report; import/export, onboarding and first data-backed owner summary.

**P2 — Physical commerce:** optional catalog, stock movements, native POS sale/shift/refund/receipt, test on real device/selected printer and recover offline commands, with exact ledgers and no regression to accounting-only businesses.

**P3 — Hybrid commerce:** first online read-only source → mapped catalog/orders → consistent reporting; tenant-scoped sync health, duplicate defense, conflict queue, bounded next-step write support where authorized; expand to another channel/external POS after acceptance.

**P4 — Merchant operations:** workflows/approvals, suppliers/purchases, multi-branch availability, barcode picking and labels, quotations, AI advice within limits.

**P5 — Commercial release:** full security/privacy/fiscal qualifications, trial merchants with different activity modes, hardware/provider tests, restore, performance, metering/subscriptions and rollout. No unqualified public-paid launch.

These are product phases; the precise implementation tasks and dependencies belong only in ENGINEERING/MASTER_ROADMAP.md. Historical finance/UX work remains prior to dependent hybrid connectors.

## 10. Acceptance evidence

Required evidence includes:
- Cross-tenant and cross-branch negative access; least-privilege API tests.
- Accounting-only service invoice, partial/full payment and ledger-reconciled balances without terminal/shift/stock.
- Immutable journals and correct reversal; same request identity returns same effect even after uncertainty.
- Catalog/SKU mapping and import validation, nonduplication of same external event.
- Concurrent stock reservation/sale never oversells silently; discrepancy review works.
- Native POS on selected hardware: sale/return/shift/print/offline restart/sync; POS-148 full path.
- Owner dashboard values trace to source records and show last updated time; stale data clearly signaled.
- Failing or reordered integrations do not duplicate orders, sales or financial entries.
- Refund and payment reconciliation do not exceed original permitted amounts.
- AI or notifications unavailable do not break checkout or posting.
- Migration upgrade/check/rollback path, CI static and integration tests, backup restore, physical/pilot/fiscal/provider acceptance as distinct gates.

Every result is labelled **PASS / FAIL / NOT RUN**, with precise SHA, test conditions, limitations and evidence. A successful CI job does not imply fiscal compliance or merchant pilot acceptance.

## 11. Product economics (hypotheses only)

Offer optional modules and merchant-based subscriptions, possibly metered AI/large media jobs, with clear trial and per-branch/device/user allowances. No fixed pricing or MRR figures are approved by this document. Validate value with real online-only, physical-only, hybrid and service merchants before broad build. Store distribution, external provider/API fees and contractual restrictions require separate review.

## 12. Engineering execution instruction

Start from live code. Follow governance/START_HERE.md and all root/agent instructions. The roadmap is singular. Select the next narrow financial task **after confirming** the source, likely account hierarchy/period/opening balance policy rather than implementing all hybrid modules. Build a task packet, implement with tested migrations and security regressions, review exact changes, run relevant GitHub checks, report immutable evidence and only then mark the feature qualified. No hidden production deployments or source-wide refactors.

**Success definition:** online merchant may connect and monitor existing storefronts; physical merchant may use native POS; hybrid merchant may see trustworthy channel/branch operations; accountant can work independently of POS; all get a simple, actionable interface on top of secure, correct shared business data.
