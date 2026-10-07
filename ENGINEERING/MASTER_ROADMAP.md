# Smart Merchant — Master Engineering Roadmap

The sole canonical roadmap. Observed 2026-10-07. Source integrated; product and full governance qualification incomplete. Reverify every live HEAD before each task.

## Current bounded task — 2026-10-07

Owner reviewed the general-platform recommendations and instructed continued work. SM-ACC-003 implements explicitly confirmed web journal posting and read-authorized request lookup, with exact monetary preview and user/organization/branch-scoped pending command recovery. Diagnosis main: 282a0b3c26f15b198562ff98942e10828b85c71f; no open PR conflict at task start. All eleven checks on that baseline passed. Current-source qualification belongs to this task's PR and result packet, not that historical baseline.

The [composer report](REPORTS/CONFIRMED_JOURNAL_COMPOSER.md), [task packet](EVIDENCE/journal-composer-task.json) and [ADR 0012](../docs/adr/0012-confirmed-journal-command.md) define this outcome. One local writer, distinct same-session review; local Git/Python 3.12/Node 24 are available. Docker/PostgreSQL/Redis/Flutter local runners are unavailable; required disposable integration/browser/mobile build checks use GitHub Actions. Historical no-shell environment records remain attributable to their earlier sessions.

Next after qualification: account hierarchy, period-close policies and opening balances; then the complete service invoice → partial/full receipt → receivable → deterministic journal → reconciled report journey. Reversal controls remain a separate bounded task. Online manual posting does not qualify offline accounting, fiscal invoices, documents, reporting or production.

The review backlog adds simple onboarding, treasury/bank reconciliation, validated migration/import/export, document attachments, tasks/approvals, external accountant access, quotes/recurring invoices and subscription/support operations. Implement each with its dependencies and acceptance evidence; unresolved fiscal/pilot/provider/pricing choices are not selected by this continuation. Core daily actions remain invoice/expense/receipt/payment; POS and inventory remain optional.

## Security prerequisite — 2026-10-07

SM-SEC-008 patches newly reported sharp/source-map-js high-severity advisories in a separate lockfile change. Diagnosis: main 282a0b3c26f15b198562ff98942e10828b85c71f. Fixed resolutions sharp 0.35.5 (matching platform/libvips packages) and source-map-js 1.2.2; no other package records or direct ranges change. Local audit: PASS, zero vulnerabilities. Exact-source required checks and reviewed merge belong to this task's PR. Confirmed composer remains a separate subsequent outcome. See [report](REPORTS/WEB_TRANSITIVE_PATCHES.md) and [task](EVIDENCE/web-transitive-patches-task.json).

## Current owner scope — 2026-10-03

Owner directed merging previous/current prompts and applying changes, then explicitly replaced the proposed food-truck-first scope with a general accounting application for all business categories. The [Unified Master Prompt v2](../docs/product/SMART_MERCHANT_MASTER_PROMPT_V2.md) is the consolidated product reference. Accounting/invoicing/customers/suppliers are the common core; POS, stock and recipes are optional modules. Preserve organization/branch architecture and POS-001–150; an accountant or service-business invoice must not depend on a POS terminal or shift. This latest direction overrides the older POS-first implementation order below without erasing historical evidence.

SM-ACC-001 is the bounded first implementation: chart accounts, balanced atomic posted journals, durable request IDs and explicit reversal, with organization/branch RBAC and database immutability. First monetary qualification is SAR. Invoice/AR/AP/period/reporting/fiscal/physical-device acceptance is NOT RUN. PR #11 (real-backend qualification) and #12 (form success) were unmerged at diagnosis and are now integrated with #13/#14 and security #15.

Historical integrated application source: main 5831c8f3a035dfbff9374e086376447e6013c524, tree 05add842c83cee28d0409384be78aabb9cf30176; reverify each later task. Original diagnosis: 80de2647186d999e98e2ff77eff1e1dd1c7810d0. Local CLI/Python/Node are available in this session; Docker/Flutter/local service runners are not verified. Historical no-shell contracts remain records of their observed sessions.

### Current delivery order

1. Preserve qualified foundation/accounting runtime checks; scope remaining form-conflict/cache repairs separately and retain physical-device gates before catalog/POS acceptance.
2. Chart/ledger/reversal core and read-only UI (SM-ACC-001/002) are integrated. Next: confirmed journal composer/unknown-result reconciliation, then account hierarchy/period-close policies.
3. Customer/supplier subledgers, sales/purchase/service invoices, receipts/payments, expenses and deterministic document posting; reports reconciled to the ledger.
4. Optional product/service catalog, warehouses/movement ledger/costing, then bounded POS context/shifts/calculation/cash completion under the existing POS rules.
5. Durable offline operation, reconciliation, eligible printing/fiscal paths, refunds and owner live projections; general-accounting usability without operational modules.
6. Mixed-activity pilots, full financial/tenant/security/device/restore acceptance, production identity/infrastructure and owner release decision.

Telegram, SoftPOS and advanced sector modules remain deferred. Do not claim every industry/jurisdiction is supported without separately qualifying its requirements.

## Current integrated accounting result — 2026-10-03

Reviewed PRs #15/#11/#12/#13/#14 are merged into main. The [integration receipt](REPORTS/GENERAL_ACCOUNTING_INTEGRATION.md) records each exact candidate/merge/check and retained tree. Final application Foundation 37127922441 (all nine jobs), Governance 37127922388 and Accounting Web 37127922401 PASS: 80 web/51 backend tests, actual migrated PostgreSQL/BFF/Chromium, full zero-vulnerability audit, Compose/security and Android/iOS simulator builds. Original audit failures and unmerged-stack descriptions below are historical source-specific records.

General accounting works without terminal/shift setup; POS/stock/recipes remain optional modules. Delivered chart accounts, immutable balanced journals/reversal/request identity and scoped Arabic/English read-only views. Current manual web posting/reversal, documents/AR/AP/periods/reports/fiscal/offline/pilot/production acceptance remain separate. Next bounded slice is confirmed journal creation with durable same-command reconciliation after an unknown result; no automatic financial replay or new UUID on an uncertain outcome.

## Historical verified state

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
FACT: Audit #10 merged at 80de2647186d999e98e2ff77eff1e1dd1c7810d0. Main Foundation [37012227678](https://github.com/n923760-rgb/smart-merchant/actions/runs/37012227678) passed all eight jobs; Governance [37012227663](https://github.com/n923760-rgb/smart-merchant/actions/runs/37012227663) passed. SM-E2E-007 adds a separate real-backend Chromium gate; its new runtime result is pending exact-source CI, not yet PASS.
FACT: Open #11 at e7a29f809df1e73857e199821c38f389d1b16100 passed Foundation [37013713281](https://github.com/n923760-rgb/smart-merchant/actions/runs/37013713281), all nine jobs including real-backend Chromium, and Governance [37013712899](https://github.com/n923760-rgb/smart-merchant/actions/runs/37013712899). This is candidate evidence, not main integration. SM-WEB-008 is a separate dependent form-lifetime correction; its own runtime evidence is pending.
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
PASS: Real-backend web journeys are integrated via #11/#12/#14. NOT RUN: physical/mobile device E2E, input/printing/offline durability and complete POS-148.
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

SM-AUDIT-006 is merged and main checks passed. SM-E2E-007 (#11) is qualified on its candidate and remains open. Qualify SM-WEB-008's separate dependent repair of user/device create forms and rendered rejection/success-retry tests; capture the form before await instead of reading expired React currentTarget. Integrate #11 before its dependent PR, with exact-source owner review/requalification. Next separately diagnose tenant unique-conflict mapping: terminal creation flushes before IntegrityError handling. Cross-tab rendered-cache invalidation remains separate. Then begin bounded POS terminal/cashier context and shift-ledger work under the decided product rules and unresolved policy gates.
Keep each independent problem in one branch/PR and update this same roadmap with attributable results.

## Historical dependency recovery — 2026-10-03

SM-SEC-007 diagnoses main 80de2647186d999e98e2ff77eff1e1dd1c7810d0 and open PRs #11–14.
Owner again expressly authorizes continuation and merges. A bounded, version-scoped
Next lint directory adapter removes braces/micromatch without downgrading Next,
dropping its rules or weakening the complete audit gate. Local clean installation,
lint/types/62 tests/build and zero-vulnerability audit pass; current exact-source CI
and reviewed integration remain required. See [report](REPORTS/NEXT_LINT_GLOB_REPAIR.md)
and [ADR 0011](../docs/adr/0011-next-lint-directory-glob.md).
After repair qualifies, refresh the pending foundation/form/accounting branches
against live main, resolve any overlaps and require new exact-source checks before
each merge. General-accounting scope remains the latest owner product direction.

## Reports and evidence

[Historical baseline](REPORTS/MASTER_ENGINEERING_BASELINE_REPORT.md), [governance adoption](REPORTS/GOVERNANCE_ADOPTION.md), [account isolation](REPORTS/WEB_SESSION_CACHE_ISOLATION.md), [evidence index](EVIDENCE/README.md), [expired-access logout](REPORTS/EXPIRED_ACCESS_LOGOUT.md), [concurrent web renewal](REPORTS/WEB_SESSION_RENEWAL.md), [BFF transport bounds](REPORTS/BFF_TRANSPORT_BOUNDS.md), [owner session renewal](REPORTS/OWNER_SESSION_RENEWAL.md), [tenant mutation audit](REPORTS/TENANT_MUTATION_AUDIT.md).

[General accounting foundation report](REPORTS/GENERAL_ACCOUNTING_FOUNDATION.md) and [task](EVIDENCE/general-accounting-task.json).

## General accounting web round — 2026-10-03

SM-ACC-002 adds read-only account/journal/detail views, accounting-only landing, independent organization/branch read scopes, exact decimal-string presentation and real disposable ledger/BFF browser qualification. Original source depended on #13 at 00c18bd; current integration refresh depends on #13 at 12947dd6c7eb6311bb2ed1a07262b9c1ced2d78a with #12/#11/security #15 carried as explicit prerequisites. No new accounting behavior is added during refresh.

The original accounting candidate was blocked by the braces audit. Security PR #15 removes that engine through a qualified bounded directory adapter while preserving Next lint rules and the full audit gate. The refreshed stack subsequently passed all checks and integrated; see the current receipt. Source-specific outcomes live in the PR qualification, [workspace report](REPORTS/ACCOUNTING_WEB_WORKSPACE.md) and [task](EVIDENCE/accounting-web-task.json).

Read-only UI is not full accounting: journal composer/unknown-result reconciliation, hierarchies/period policy, documents/AR/AP and reconciled reports remain subsequent bounded tasks. No device, fiscal or production acceptance is implied.
[Real-backend browser qualification](REPORTS/REAL_BACKEND_BROWSER.md).

[Management form success](REPORTS/MANAGEMENT_FORM_SUCCESS.md).

## Historical integration refresh — 2026-10-03

Security PR #15 is merged at 6f037be4594f7c2b1ddadf59e0141c8ae3c07905; tree
57fc875418ad58af513a2e307542a8ddf89fcde7 equals qualified checkout 993a705f6829fdc06a38e9bc4bb875b9e99c9234.
Foundation 37126881609 (all eight jobs) and Governance 37126881577 pass; web
audit reports zero vulnerabilities. Owner explicitly authorizes continuing and
merging. At refresh, #11 → #12 → #13 → #14 formed an explicit qualification stack,
carrying the repair and retaining each bounded outcome. Reverify exact source,
resolve report/roadmap overlaps by preserving both records, require successful
current checks, integrate predecessors, then retarget successors to main.
General accounting remains independent of business category, terminals and shifts.

FACT: Refreshed real-backend PR #11 merged at 5df9dbfcf578fabcd3720a0f33ff83010ce01d9d,
retaining qualified tree ec914dafea35487d323d00a5d2178d3a86754917. Foundation
37127389477 (all nine jobs, including actual PostgreSQL/BFF Chromium) and
Governance 37127389403 pass on d0a24c720f4f0bd280505a59056b4f21d020cac0.
Successors subsequently qualified and integrated; see the current receipt.

## Qualified post-merge observation correction — 2026-10-03

Original main Accounting Web 37128381976 and documentation candidate 37128773307 failed the late scopedReads count despite pre-merge candidate success. SM-E2E-010 captures before automatic accounting landing, waits for account/journal content and proves every authorized resource/branch pair, retaining every unscoped/foreign denial assertion. No application behavior changes. The [observation report](REPORTS/ACCOUNTING_SCOPE_OBSERVATION.md) retains the failed-source diagnosis.

PR #17 merged at 5831c8f3a035dfbff9374e086376447e6013c524, retaining qualified tree 05add842c83cee28d0409384be78aabb9cf30176. Foundation 37129241430 (all nine jobs), Governance 37129241513 and Accounting Web 37129241502 PASS on 17fc050b68a0e1bbe295229d2eff84a24e860b73. Initial documentation PR 16 was kept unmerged after its failure; this refreshed source carries the actual correction and requires its own full current checks. Historical failures are not suppressed. The next confirmed journal-composer/document/report sequence is unchanged.
