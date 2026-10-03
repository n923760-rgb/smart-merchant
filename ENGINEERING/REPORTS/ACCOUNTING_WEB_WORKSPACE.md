# SM-ACC-002 — General accounting web workspace

Repository: n923760-rgb/smart-merchant. Actor: Codex, single source writer and same-session review, not independent approval.
Diagnosis official main: 80de2647186d999e98e2ff77eff1e1dd1c7810d0.
Task base: accounting PR #13, 00c18bd36616f16fb365408d880df2e9056acc24, tree 03984901b6983256a843d0a9f52942f2183ac4c1. Main and PR were rechecked before work; #11/#12 remain separate.
Authority: owner's 2026-10-03 continued-development instruction, general-accounting product direction and persistent reviewed-merge authority. [Exact task](../EVIDENCE/accounting-web-task.json).

## Bounded outcome

An Arabic/English read-only accounting web page lists paginated chart accounts and posted journals and fetches journal details/reversal linkage from the existing authoritative APIs. No POS/device/shift permission or setup is required. No financial writes, browser totals, financial report or ledger composer is implemented.

Navigation permits either account-read or journal-read. Accounting-only users land on accounting after login without gaining organization-management access. Denied pages retain authorized navigation/sign-out but never mount their protected child page. The backend remains the authority for every grant and tenant lookup.

Each resource is checked independently for the selected scope. Organization-level reads need organization grants. Branch-only users see authorized branch UUID scopes and send an explicit branch_id on all lists. This first UI labels scopes with their authorized UUID rather than requiring extra branches.read permissions; global users see the organization-wide list, not an invented complete branch picker.

Query keys include organization, branch scope, resource, page and selected entry; scope changes unmount the table/detail state. Existing login-boundary provider isolation remains intact. Errors/loading/empty results are distinct, automatic query retries are disabled, and retry actions are explicit reads only. Amounts retain backend decimal strings, including digits above JavaScript's safe integer limit. Date/actor/ledger calculations remain authoritative backend concerns.

## Qualification

Local lab: clean isolated worktree; Git, Node 24/npm and Python are available; 27 GB free observed. Dependencies installed with the unchanged committed lockfile. No local qualified PostgreSQL/Docker/Flutter lab is claimed.

Local PASS: ESLint, TypeScript, 68 Vitest cases (18 new accounting cases), production build, JavaScript syntax, whitespace and task/adoption validation. Exact candidate CI outcomes are recorded in the PR qualification. The new Accounting Web CI runs an independent disposable PostgreSQL/Redis/FastAPI + production Next.js/BFF + Chromium fixture, not a mocked ledger.

Required browser proof includes: accountant without terminal/shift grants; exact large cents and reversal linkage; independent account/journal pagination; branch-only requests and real forged-branch denial; cashier-hidden navigation/direct denial; scope reset; controlled read error/retry without stale rows; account/organization cache reset; Arabic RTL/English and mobile layout. Only the deliberate read-error and next-account read-delay injections intercept browser requests; authoritative ledger fixtures and authorization denials use the real API. Fixture bootstrap writes require explicit credentials and loopback URLs and never touch production data.

The existing Foundation and Governance gates remain unchanged. The separate accounting browser workflow is additional evidence, not an audit bypass. Exact candidate/checkout/run outcomes belong to the PR qualification, never a previous successful commit.

Initial candidate 832d89ad499ac56fbe08b97f4e06ea851c74d614 passed local checks but Accounting Web run 37121985282 failed during fixture bootstrap: the reserved example.test email domain is rejected by the unchanged backend email validator (422). Fixture addresses are corrected to example.com; no input-validation rule is weakened. Required browser assertions were not reached on that initial run and must qualify the corrected source.

Candidate a2cce3c5b1c49e7b4b0040362135d5a6a5269713 reached real reads/pagination/reversal/exact money/mobile and error-retry checks, then timed out on the branch scope selector's exact accessible label. Native option text contributed to its computed label. An explicit localized aria-label fixes the control's stable accessible name; the same real branch assertions remain required on the corrected source.

Candidate 6eab1b7021d2aa7104d9fc362e12bc44c2e4e7ea passed branch list/scope-reset assertions, then its forged-branch check used Playwright's Node APIRequestContext, which returned 401 rather than exercising the authenticated browser's Secure loopback cookie rules. The check now uses actual in-page browser fetch with the existing non-secret session-context binding and still requires backend 403 and no secret records. No cookie/auth/permission policy changes are made. Layout artifacts from a2cce3c were visually inspected: desktop RTL and 390px phone layout; wide financial tables intentionally scroll inside their containers.

## Historical merge blocker and limits

BLOCKED: base accounting PR #13 is unmerged because the unchanged web ESLint transitive braces 3.0.3 chain fails the high-severity dependency audit. Registry checks on 2026-10-03 found no patched stable braces version, and even Next ESLint canary retained fast-glob. Forced downgrade, fork/alias substitution and an audit exception were not applied. Required gates are not relaxed. This dependent PR cannot merge into its unmerged base as a substitute for main integration.

NOT RUN / not implemented: manual posting/reversal UI, account hierarchy/period policy, document/AR/AP/fiscal integration, trial balance/statements, mobile accounting screens, other browser engines, physical devices, merchant pilot and production. CI layout screenshots contain only disposable fixture records.

Next bounded product step after safe base integration: an explicitly confirmed manual journal composer with durable command identity, unknown-outcome reconciliation and backend-authoritative balance/permission validation. Financial reports/period policy remain separate roadmap items.

## Owner-authorized integration refresh — 2026-10-03

Current owner explicitly authorizes continued reviewed merges. Security PR 15
actually replaces the vulnerable directory-glob engine and is merged with all
gates passing; previous audit failures remain historical source evidence. Refresh
upstream accounting PR 13 at 12947dd6c7eb6311bb2ed1a07262b9c1ced2d78a, including
real-backend/form PRs 11/12. Preserve both roadmap/report sections and both E2E
readme sections. Workspace production code is unchanged. Require new Foundation,
Governance and real-ledger browser checks (80 web tests including the 12 upstream
lint regressions), then predecessor integration and exact tested-tree review.
The next product slice remains confirmed journal creation/reconciliation.
