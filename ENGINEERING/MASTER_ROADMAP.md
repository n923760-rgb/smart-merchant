# Smart Merchant — Master Engineering Roadmap

The sole canonical roadmap. Observed 2026-10-02. Source integrated; product and full governance qualification incomplete. Reverify every live HEAD before each task.

## Current owner scope — 2026-10-03

Owner directed merging previous/current prompts and applying changes, then explicitly replaced the proposed food-truck-first scope with a general accounting application for all business categories. The [Unified Master Prompt v2](../docs/product/SMART_MERCHANT_MASTER_PROMPT_V2.md) is the consolidated product reference. Accounting/invoicing/customers/suppliers are the common core; POS, stock and recipes are optional modules. Preserve organization/branch architecture and POS-001–150; an accountant or service-business invoice must not depend on a POS terminal or shift. This latest direction overrides the older POS-first implementation order below without erasing historical evidence.

SM-ACC-001 is the bounded first implementation: chart accounts, balanced atomic posted journals, durable request IDs and explicit reversal, with organization/branch RBAC and database immutability. First monetary qualification is SAR. Invoice/AR/AP/period/reporting/fiscal/physical-device acceptance is NOT RUN. Existing open PR #11 (real-backend browser qualification) and dependent #12 (form success repair) remain separate, unmerged work observed at diagnosis.

Current task source: main 80de2647186d999e98e2ff77eff1e1dd1c7810d0, tree e8e722a7d8001204df0df88c9b2203b2bb7ffdd4; reverify before merge. Local CLI/Python/Node are available in this session; Docker/Flutter/local service runners are not verified. Historical no-shell contracts remain records of their observed sessions.

### Current delivery order

1. Finish attributable foundation web/runtime qualification and repairs; preserve outstanding physical-device gates before catalog/POS acceptance.
2. General chart/ledger/reversal core (SM-ACC-001), then accounting UI and account hierarchy/period-close policies.
3. Customer/supplier subledgers, sales/purchase/service invoices, receipts/payments, expenses and deterministic document posting; reports reconciled to the ledger.
4. Optional product/service catalog, warehouses/movement ledger/costing, then bounded POS context/shifts/calculation/cash completion under the existing POS rules.
5. Durable offline operation, reconciliation, eligible printing/fiscal paths, refunds and owner live projections; general-accounting usability without operational modules.
6. Mixed-activity pilots, full financial/tenant/security/device/restore acceptance, production identity/infrastructure and owner release decision.

Telegram, SoftPOS and advanced sector modules remain deferred. Do not claim every industry/jurisdiction is supported without separately qualifying its requirements.

## Current verified state

FACT: Foundation #1 is merged into main at cec4eba1eb07b9ab4b62ca79cb91a808eb3f373d, preserving tested tree 71d65bb3671afd968d06504d74de45e99322bbb0.
FACT: #5 repaired SQLAlchemy plugin compatibility and Next.js/brace-expansion vulnerabilities; #4 isolates account caches across web login boundaries.
FACT: Foundation CI run [36964046492](https://github.com/n923760-rgb/smart-merchant/actions/runs/36964046492) passed on ad50311a9df9b522607eea17fd4f65f6cc782078, whose tree matches the canonical integration.
FACT: Governance #2 merged at d1a148b8f30c4ceaf68f670dc8b4409e8b3ca3db; [Governance CI](https://github.com/n923760-rgb/smart-merchant/actions/runs/36965459067) and [Foundation CI](https://github.com/n923760-rgb/smart-merchant/actions/runs/36965459078) passed on 9e4487b803a06273aff7e23fd612a70e5e19adbe, with matching merge tree.
FACT: POS requirements #3 merged at 8538eb6de3a800836a007a4d23e898d94b40c2e3; [Foundation CI](https://github.com/n923760-rgb/smart-merchant/actions/runs/36966049894) and [Governance CI](https://github.com/n923760-rgb/smart-merchant/actions/runs/36966049889) passed on 7cb6a2e6cc7eb11510ccf723a5700b9868f368af. It preserves 150 rules and 25 NOT RUN acceptance groups; no POS transaction implementation is claimed.
FACT: Logout #6 merged at d273ea5ca0e7a841b3db423840d6cecb95011d8a; candidate 4eb0d980e3ad98d78716f75561d0d641c77416a2 passed Foundation/Governance 36966865089 / 36966865063. Main passed [36967403546](https://github.com/n923760-rgb/smart-merchant/actions/runs/36967403546) / [36967403567](https://github.com/n923760-rgb/smart-merchant/actions/runs/36967403567). Refresh-only logout and its regressions are integrated.
FACT: Web renewal #7 merged at 9ed105206becda3c88a369f8feff46aa66cda50c, preserving tested tree 4f5ab2064528a0b3be3c04646b4f399dc0c249e8. Main Foundation/Governance passed [36970604523](https://github.com/n923760-rgb/smart-merchant/actions/runs/36970604523) / [36970604435](https://github.com/n923760-rgb/smart-merchant/actions/runs/36970604435); 22 web/14 backend tests plus Chromium and Android/iOS simulator gates passed.
FACT: BFF bounds #8 merged at 2f5440165d7c2f2a8ef7cb07a1204b40456964b8, preserving tested tree c980d285ed5932ed8c39400b81f38b98067d160a. Main Foundation/Governance passed [37006048107](https://github.com/n923760-rgb/smart-merchant/actions/runs/37006048107) / [37006048068](https://github.com/n923760-rgb/smart-merchant/actions/runs/37006048068); 50 web/14 backend tests and browser/Android/iOS simulator gates passed.
FACT: Owner renewal #9 merged at 6b6a5107ffa6867adcbcb26adb8233780d14a2c0, preserving tested tree a7a5cfef732bd398059693055f4c522bc15aca7c. Candidate f7cd206ed07d4c46578b206ef41e0d868a6ab576 passed Foundation/Governance [37009604344](https://github.com/n923760-rgb/smart-merchant/actions/runs/37009604344) / [37009604354](https://github.com/n923760-rgb/smart-merchant/actions/runs/37009604354), including 18 owner/50 web/14 backend tests and all Android/iOS simulator gates. Main post-merge CI is newly triggered; reverify its state.
FACT: Owner instructed continued work without repeat permission requests and granted project authority. Reviewed merges are authorized; actions need exact-source verification and relevant successful checks.
UNKNOWN: Physical device/pilot acceptance, real payment adapters, production identities/signing/infrastructure, backups and restore.
BLOCKED: Branch-protection writes are not available through this connector.

## Architecture and ownership

FastAPI modular monolith; PostgreSQL authoritative transactional state and append-only audit; Redis ephemeral operations.
Next.js server BFF owns HttpOnly session cookies; Flutter POS/owner remain shells.
All tenant resources require organization scope and server RBAC. Preserve the last active owner.
Completed financial records will be immutable; money must use decimal arithmetic; AI cannot gate checkout.
[Architecture](../docs/architecture/overview.md), [ADRs](../docs/adr/), [testing](../docs/testing/testing-strategy.md).

## Closed historical work

- Read-only baseline at 737facd48180d7920540f93032ba0a827c9d1ef2; records remain historical.
- #5 dependency gates: [36963314173](https://github.com/n923760-rgb/smart-merchant/actions/runs/36963314173), all eight jobs passed.
- #4 account switching: [36963506667](https://github.com/n923760-rgb/smart-merchant/actions/runs/36963506667), all eight jobs passed; Chromium uses synthetic BFF, not real backend/device qualification.
- #1 canonical integration: reviewed source and matching merge tree.

## Current findings and qualification gaps

SOURCE FACT at original foundation: Backend logout depended on current_user, so expired access rejected logout before revocation; web/owner also required in-memory access. SM-AUTH-002 corrected this defect and is merged in #6.
SOURCE FACT: Independent BFF requests attempted rotation on the same cookie snapshot. SM-AUTH-003 uses cross-tab browser locking and context binding, preserving backend one-use rotation. Source/CI correction is merged in #7; cross-tab rendered-cache invalidation and lost-cookie delivery remain separate qualification gaps.
SOURCE FACT: BFF transport was unbounded on diagnosis main; SM-WEB-004 adds streamed byte caps, cumulative deadlines and bounded browser auth-lock requests. Its exact checks/review/merge are recorded in the task PR.
SOURCE FACT: User invitation and terminal rename omitted audit records on diagnosis main. SM-AUDIT-006 adds minimal tenant/actor-scoped records in the mutation transaction; its exact checks/review/merge are recorded in the task PR.
SOURCE FACT: SM-AUTH-005 adds owner foreground renewal and serialized credential operations; its exact checks/review/merge are recorded in the task PR.
NOT RUN: Real backend browser/device E2E, physical input/printing/offline durability and complete POS-148.
Governance fixtures cover packet authority/evidence, not live dirty-source/capacity/protection enforcement.
No permanent autonomous agent is installed. Role review in this session is the same actor; never label it independent review.

## Ordered engineering gates

1. Canonical foundation/governance/POS requirements #1–#3 are merged.
2. Expired-access logout regression/correction is merged (#6).
3. Separate BFF refresh concurrency, limits and owner expiry rounds.
4. Separate tenant-safe audit-coverage correction.
5. Foundation browser/device/runtime acceptance; qualify enforced protection and permanent lab where available.
6. Bounded POS slices from the owner-decided requirements: terminal/cashier context and shift ledger; catalog/prices/modifiers; shared decimal calculation; cash completion/snapshots/outbox; inventory/profit/owner projections; receipts; durable offline import; refunds/shift close; card adapters.
7. Complete POS-148 and failure/security/runtime matrix on frozen source.
8. Production artifacts, signing/configuration, restore, monitoring/rollback and owner release decision.

The [POS delivery and policy plan](../docs/product/POS_DELIVERY_PLAN_V1.md) is subordinate to this roadmap. Its unresolved policies must be selected before dependent behavior, without treating numeric examples as production defaults.

## Runtime and release gates

Source/CI success is not physical or production acceptance. Required pilot surfaces/providers/hardware are not chosen.
No production release is qualified. Use disposable data; never test against real merchant finances.
Each newer source requires affected checks; old successful CI remains attached to its actual source.

## Owner decisions and deferred work

Continued engineering and reviewed merges authorized on 2026-10-02.
Telegram remains deferred by prior owner instruction.
Payment provider, pilot/fiscal/tax policy, production identity/hosting/signing, paid service and physical targets remain unspecified.
Tables/KDS/reservations/NFC/customer display/forecasting are future surfaces per POS requirements.

## Historical immediate next round — superseded by current owner scope

Complete SM-AUDIT-006 tenant/permission/snapshot/rollback regressions, Foundation/Governance CI and reviewed owner-authorized merge. Next qualify browser flow against the real disposable backend; cross-tab rendered-cache invalidation remains a separate issue. Then begin bounded POS terminal/cashier context and shift-ledger work under the decided product rules and unresolved policy gates.
Keep each independent problem in one branch/PR and update this same roadmap with attributable results.

## Reports and evidence

[Historical baseline](REPORTS/MASTER_ENGINEERING_BASELINE_REPORT.md), [governance adoption](REPORTS/GOVERNANCE_ADOPTION.md), [account isolation](REPORTS/WEB_SESSION_CACHE_ISOLATION.md), [evidence index](EVIDENCE/README.md), [expired-access logout](REPORTS/EXPIRED_ACCESS_LOGOUT.md), [concurrent web renewal](REPORTS/WEB_SESSION_RENEWAL.md), [BFF transport bounds](REPORTS/BFF_TRANSPORT_BOUNDS.md), [owner session renewal](REPORTS/OWNER_SESSION_RENEWAL.md), [tenant mutation audit](REPORTS/TENANT_MUTATION_AUDIT.md).

[General accounting foundation report](REPORTS/GENERAL_ACCOUNTING_FOUNDATION.md) and [task](EVIDENCE/general-accounting-task.json).

## General accounting web round — 2026-10-03

SM-ACC-002 adds read-only account/journal/detail views, accounting-only landing, independent organization/branch read scopes, exact decimal-string presentation and real disposable ledger/BFF browser qualification. Its branch depends explicitly on unmerged accounting PR #13 at 00c18bd36616f16fb365408d880df2e9056acc24; diagnosis main remains 80de2647186d999e98e2ff77eff1e1dd1c7810d0. Existing PRs #11/#12 are not modified.

The pre-existing web dependency audit remains BLOCKED (braces 3.0.3; no patched stable release observed). No forced downgrade, fork substitution or weakened security gate is adopted. Neither the base nor the dependent workspace may merge until current required checks pass. Source-specific outcomes live in the PR qualification, [workspace report](REPORTS/ACCOUNTING_WEB_WORKSPACE.md) and [task](EVIDENCE/accounting-web-task.json).

Read-only UI is not full accounting: journal composer/unknown-result reconciliation, hierarchies/period policy, documents/AR/AP and reconciled reports remain subsequent bounded tasks. No device, fiscal or production acceptance is implied.
