# Smart Merchant — Master Engineering Roadmap

The sole canonical roadmap. Observed 2026-10-02. Source integrated; product and full governance qualification incomplete. Reverify every live HEAD before each task.

## Current verified state

FACT: Foundation #1 is merged into main at cec4eba1eb07b9ab4b62ca79cb91a808eb3f373d, preserving tested tree 71d65bb3671afd968d06504d74de45e99322bbb0.
FACT: #5 repaired SQLAlchemy plugin compatibility and Next.js/brace-expansion vulnerabilities; #4 isolates account caches across web login boundaries.
FACT: Foundation CI run [36964046492](https://github.com/n923760-rgb/smart-merchant/actions/runs/36964046492) passed on ad50311a9df9b522607eea17fd4f65f6cc782078, whose tree matches the canonical integration.
FACT: Governance #2 merged at d1a148b8f30c4ceaf68f670dc8b4409e8b3ca3db; [Governance CI](https://github.com/n923760-rgb/smart-merchant/actions/runs/36965459067) and [Foundation CI](https://github.com/n923760-rgb/smart-merchant/actions/runs/36965459078) passed on 9e4487b803a06273aff7e23fd612a70e5e19adbe, with matching merge tree.
FACT: POS requirements #3 merged at 8538eb6de3a800836a007a4d23e898d94b40c2e3; [Foundation CI](https://github.com/n923760-rgb/smart-merchant/actions/runs/36966049894) and [Governance CI](https://github.com/n923760-rgb/smart-merchant/actions/runs/36966049889) passed on 7cb6a2e6cc7eb11510ccf723a5700b9868f368af. It preserves 150 rules and 25 NOT RUN acceptance groups; no POS transaction implementation is claimed.
FACT: Logout #6 merged at d273ea5ca0e7a841b3db423840d6cecb95011d8a; candidate 4eb0d980e3ad98d78716f75561d0d641c77416a2 passed Foundation/Governance 36966865089 / 36966865063. Main passed [36967403546](https://github.com/n923760-rgb/smart-merchant/actions/runs/36967403546) / [36967403567](https://github.com/n923760-rgb/smart-merchant/actions/runs/36967403567). Refresh-only logout and its regressions are integrated.
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
SOURCE FACT: Independent BFF requests attempted rotation on the same cookie snapshot. SM-AUTH-003 uses cross-tab browser locking and context binding, preserving backend one-use rotation. Exact candidate proof/review/merge is tracked in its PR.
SOURCE FACT: BFF request bodies/timeouts are unbounded; user invitation and terminal rename omit audit records. Each needs its own bounded task.
NOT RUN: Owner-app foreground expiry behavior, real backend browser E2E, physical input/printing/offline durability and complete POS-148.
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

## Exact immediate next round

Complete SM-AUTH-003 exact-source concurrency regressions, Foundation/Governance CI and reviewed owner-authorized merge. Then take BFF limits as the next bounded task; owner foreground expiry and cross-tab already-rendered cache invalidation remain separate. This round uses the browser Web Locks/session-context design in ADR 0007.
Keep each independent problem in one branch/PR and update this same roadmap with attributable results.

## Reports and evidence

[Historical baseline](REPORTS/MASTER_ENGINEERING_BASELINE_REPORT.md), [governance adoption](REPORTS/GOVERNANCE_ADOPTION.md), [account isolation](REPORTS/WEB_SESSION_CACHE_ISOLATION.md), [evidence index](EVIDENCE/README.md), [expired-access logout](REPORTS/EXPIRED_ACCESS_LOGOUT.md), [concurrent web renewal](REPORTS/WEB_SESSION_RENEWAL.md).
