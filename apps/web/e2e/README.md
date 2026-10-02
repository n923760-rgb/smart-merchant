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
It forces two expired requests, a late 401 after another rotation, logout waiting for the successor, and rejection of an old account command after a new login.
No BFF interception is used in this second script. Backend PostgreSQL rotation semantics remain covered separately by backend CI.
This qualifies one Chromium context and one BFF instance with a synthetic backend; it does not claim real backend E2E, a multi-instance runtime lab, Safari/Firefox or physical devices.

Start Next.js with BACKEND_URL=http://127.0.0.1:8000, then copy/run session-renewal.mjs beside the same pinned Playwright installation after session-isolation.mjs.
The renewal script owns/cleans up port 8000. Use a disposable environment with that port free.
HTTPS (or a trustworthy localhost context) and Web Locks are required for session-changing actions.
Browsers without Web Locks receive an actionable session error; no unsafe process-local coordination fallback is used.
