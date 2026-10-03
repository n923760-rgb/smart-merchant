# General accounting — reviewed integration receipt

Repository: n923760-rgb/smart-merchant. Observed 2026-10-03.
Actor: Codex, one source writer and same-session review; not independent approval.
Authority: owner expressly says continue and merge with full project authority.
Task: [SM-DOC-009](../EVIDENCE/general-accounting-integration-task.json).

## Integrated result

Application integration was initially verified at main f7e31d719ad0527d2a305270e944a251738ba976, tree
376ac0a14172b62039a7bbb2840fe4e8f7f8f90d. Its tree equals qualified workspace
candidate 7dffdfeeefd4d1b2950077473b9dbd9f026bf175 and CI checkout
50dc73e92c6e1a9a7c21a816e2654a5683987f21. Each merge result was reread and its
tree checked against the qualified content. PRs 11–15 are closed/merged; there
were no open PRs before this documentation round.

The merged scope is a general accounting/business platform with optional POS,
inventory and activity modules. The unified Arabic prompt and 150 existing POS
rule bodies are retained. Accounting works without terminal/shift setup.
The initial qualified currency is SAR, not a claim about every currency or law.

Delivered: tenant/branch accounting grants; chart accounts; balanced atomic
journals with decimal strings; durable request identity/content validation;
database immutability and full linked reversal; Arabic/English read-only account,
journal pagination/detail views; accounting-only landing; read error/retry and
account-cache isolation. Foundation real-backend browser and two management-form
success/rejection corrections are integrated. The vulnerable lint glob engine
was actually replaced while retaining Next rules and the full audit gate.

## Exact reviewed merges and qualification

| PR | Qualified candidate | Merge into main | CI runs |
|---|---|---|---|
| [15](https://github.com/n923760-rgb/smart-merchant/pull/15), lint dependency | f69f275cd0bb5fad53ee707dc6d270eec222ff0d | 6f037be4594f7c2b1ddadf59e0141c8ae3c07905 | Foundation 37126881609; Governance 37126881577 |
| [11](https://github.com/n923760-rgb/smart-merchant/pull/11), real backend | d0a24c720f4f0bd280505a59056b4f21d020cac0 | 5df9dbfcf578fabcd3720a0f33ff83010ce01d9d | Foundation 37127389477; Governance 37127389403 |
| [12](https://github.com/n923760-rgb/smart-merchant/pull/12), form success | f52cdd107c077a25cb21612b1e4c74b363d88bae | 139074d7be0c95cfd040821e4686c2460b959fad | Foundation 37127507360; Governance 37127507307 |
| [13](https://github.com/n923760-rgb/smart-merchant/pull/13), accounting core | 12947dd6c7eb6311bb2ed1a07262b9c1ced2d78a | 1b77314de63b19323927f04647b13d91c8de8243 | Foundation 37127669963; Governance 37127670031 |
| [14](https://github.com/n923760-rgb/smart-merchant/pull/14), accounting web | 7dffdfeeefd4d1b2950077473b9dbd9f026bf175 | f7e31d719ad0527d2a305270e944a251738ba976 | Foundation 37127922441; Governance 37127922388; Accounting Web 37127922401 |

All listed runs PASS. Successors were explicitly stacked and then retargeted to
main after predecessor integration; identical qualified upstream/candidate trees
were verified. No force push, direct main commit, security exception or failed
check merge was used. Only roadmap/report text overlaps required resolution;
both records and both E2E readme sections were preserved. Original accounting
and workspace production code remain unchanged during prerequisite refresh.

Final source evidence:

- [Foundation 37127922441](https://github.com/n923760-rgb/smart-merchant/actions/runs/37127922441): all nine jobs PASS. Backend 51 tests, lint/types, PostgreSQL migration check/roundtrip, concurrency/rollback/immutability/RBAC/tenant and dependency audit. Web 80 tests, lint/types/build, session BFF browser and full npm audit reporting zero vulnerabilities. Actual foundation browser, Compose, security and Android/iOS simulator builds PASS.
- [Accounting Web 37127922401](https://github.com/n923760-rgb/smart-merchant/actions/runs/37127922401): actual disposable PostgreSQL/FastAPI/production BFF/Chromium PASS for no-terminal accountant, large exact cents, reversal linkage, pagination, real branch/tenant denial, explicit read error/retry, RTL/mobile/English and cache isolation.
- [Governance 37127922388](https://github.com/n923760-rgb/smart-merchant/actions/runs/37127922388): contract/authority/evidence fixtures PASS.

These prove their exact application tree. The post-merge main push and this
documentation-only candidate have separately triggered checks; their latest
status belongs to their own PR/run evidence, not an invented earlier pass.

## Remaining work and next bounded outcome

1. Confirmed manual journal creation UI with exact decimal validation, durable
   command identity and tenant/actor context. Qualify unknown-result lookup and
   explicit same-command reconciliation before allowing a fresh command; never
   silently repeat an unknown financial outcome with a new UUID.
2. Chart hierarchy and closing-period policies, then customers/suppliers,
   service/sales/purchase documents, settlements/expenses and deterministic
   double-entry document posting.
3. Ledger-reconciled trial balance, general ledger, income statement and balance
   sheet. Optional catalog/POS/stock/offline modules follow their existing gates.

Financial report totals, fiscal integration, offline ledger commands, other
browser engines, physical devices, pilot review and production release remain
NOT RUN/unimplemented as applicable. Read-only accounting web is not a complete
accounting app. Keep terminal unique-conflict mapping, cross-tab cache behavior
and physical/POS acceptance as separately scoped foundation follow-ups.

## Post-merge observation correction and current source

Main Accounting Web 37128381976 and initial documentation candidate run 37128773307 subsequently failed scopedReads >= 4. Automatic accounting landing can issue lists before signIn returns, so the late fixture boundary omitted valid initial/cached requests. Both failures are retained; old passing runs were not used to ignore them. [PR 17](https://github.com/n923760-rgb/smart-merchant/pull/17) starts capture before login and proves accounts/journals for both authorized branches, retaining real forged B3 403, scope reset, cashier and tenant/cache assertions. No application, financial, auth, dependencies or CI behavior changes.

Correction candidate: 17fc050b68a0e1bbe295229d2eff84a24e860b73; tree 05add842c83cee28d0409384be78aabb9cf30176; checkout 5aec4b1d6f562a7ece7d3c131d8f8745173dafb0. Foundation 37129241430 (all nine jobs), Governance 37129241513 and Accounting Web 37129241502 PASS. It merged into main at 5831c8f3a035dfbff9374e086376447e6013c524 with the same tree. This refreshed documentation candidate includes the correction and requires its own exact-source full checks before reviewed merge. The earlier receipt records the implementation baseline, not the newest main source. Latest documentation qualification/merge evidence belongs to PR 16.
