# Account-switch browser regression

session-isolation.mjs runs against the production Next.js app with explicit synthetic BFF responses.
It exercises actual client navigation and query-provider lifecycle, not a mocked QueryClient.
The first account warms identity/organization/branch/user/device caches. An in-flight request survives logout. The second account's responses are held while the test checks that old data and old organization selection never appear.

Foundation CI builds the app, installs pinned Playwright 1.55.1 in a temporary tools directory, copies the script beside that installation and runs Chromium.
The browser tool is isolated from application dependencies; no production credentials/backend/data are used.
This test does not qualify real backend login, multi-tab session synchronization, provider payments, devices or physical runtime.

To run in a shell-capable lab from apps/web:
1. Run npm ci and npm run build.
2. Install playwright@1.55.1 in a disposable tools directory with npm install --prefix <tools-dir> --no-package-lock --ignore-scripts.
3. Run node <tools-dir>/node_modules/playwright/cli.js install --with-deps chromium.
4. Copy session-isolation.mjs next to that node_modules directory.
5. Start node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000.
6. Run SM_TEST_BASE_URL=http://127.0.0.1:3000 node <tools-dir>/session-isolation.mjs.

## Concurrent renewal through the real BFF

session-renewal.mjs uses production Next.js routes and real Chromium cookies/Web Locks in two tabs.
Its disposable Node HTTP upstream binds port 8000 and implements strict one-use refresh fixtures.
It forces two expired requests, a late 401 after another rotation, logout waiting for the successor, and rejection of an old account command and a dormant tab's real form submission after a new login.
No BFF interception is used in this second script. Backend PostgreSQL rotation semantics remain covered separately by backend CI.
This qualifies one Chromium context and one BFF instance with a synthetic backend; it does not claim real backend E2E, a multi-instance runtime lab, Safari/Firefox or physical devices.

Start Next.js with BACKEND_URL=http://127.0.0.1:8000, then copy/run session-renewal.mjs beside the same pinned Playwright installation after session-isolation.mjs.
The renewal script owns/cleans up port 8000. Use a disposable environment with that port free.
HTTPS (or a trustworthy localhost context) and Web Locks are required for session-changing actions.
Browsers without Web Locks receive an actionable session error; no unsafe process-local coordination fallback is used.

## BFF failure bounds

The same real-BFF fixture also stalls a mutation response after sending upstream headers, proving a 504 leaves cookies/navigation intact and makes only one command attempt, without refresh.
It then stalls logout revocation and verifies local cookies are cleared within the server deadline.
The test uses default server limits (10 seconds), with two deliberately stalled bodies and disposable data. Browser steps retain their 15-second bound.
Vitest uses fake timers for cumulative input/upstream deadlines and the 65-second browser deadline/lock release; it does not sleep for those durations.
These fixtures do not assert that abort rolls back an authoritative command or proves logout revocation when the result is unavailable.

## General accounting with the real ledger

accounting-workspace.mjs uses real disposable FastAPI/PostgreSQL/Redis, the production Next.js BFF and Chromium. Accounting Web CI starts its own isolated services and supplies explicit fixture credentials; the script rejects non-loopback URLs before bootstrap writes. It seeds two organizations, zero terminals, accounts, balanced posted journals, a reversal, branch-scoped accountants and a cashier through the actual API.

The browser checks read-only accounting navigation/landing, exact large decimal amounts, pagination/details, explicit branch-bound requests and real server denial of a forged branch, cashier denial, scope reset, read-error retry, login/organization cache isolation and Arabic RTL/mobile/English layout. Only controlled read failure/delay responses are injected. This additional workflow does not replace or bypass Foundation's full dependency audit.

For a qualified disposable local lab, migrate/start the backend and build/start Next.js using the same BACKEND_URL. Copy the script beside the pinned temporary Playwright installation as above. Supply BOOTSTRAP_KEY and SM_ACCOUNTING_TEST_PASSWORD matching this isolated fixture backend, then run the script. Do not use merchant or production credentials/databases. Only Chromium/one BFF instance and this read-only accounting flow are qualified; journal creation UI and other browser engines remain outside this test.
