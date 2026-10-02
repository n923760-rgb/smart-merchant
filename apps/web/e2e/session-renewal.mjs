import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { chromium } from 'playwright';

const baseURL = process.env.SM_TEST_BASE_URL ?? 'http://127.0.0.1:3000';
const org = '11111111-1111-4111-8111-111111111111';
const permissions = ['organization.read', 'branches.read', 'users.read', 'roles.read', 'terminals.read'];
function deferred() {
  let resolve;
  const promise = new Promise(complete => { resolve = complete; });
  return { promise, resolve };
}
async function bounded(promise, label) {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error('Timed out: ' + label)), 15_000);
    })]);
  } finally { clearTimeout(timer); }
}
const initialFailures = deferred();
const branchReady = deferred(), branchRelease = deferred();
const refreshReady = deferred(), refreshRelease = deferred();
let initialCount = 0, generation = 0, currentAccess = '', currentRefresh = '';
let expired = false, account = 'Alpha', refreshCalls = 0, logoutCalls = 0;
let holdBranch = false, holdRefresh = false;
const usedRefreshes = new Set();
const seenCommands = [];
function issue() {
  generation++;
  currentAccess = 'disposable-access-' + generation;
  currentRefresh = 'disposable-refresh-' + generation;
  expired = false;
  return { access_token: currentAccess, refresh_token: currentRefresh };
}
const upstream = createServer(async (req, res) => {
  const path = new URL(req.url, 'http://fixture.test').pathname.replace('/api/v1/', '');
  const send = (data, status = 200) => { res.writeHead(status, { 'Content-Type': 'application/json' }); res.end(status === 204 ? undefined : JSON.stringify(data)); };
  try {
    let text = '';
    for await (const chunk of req) text += chunk;
    const body = text ? JSON.parse(text) : {};
    if (path === 'auth/login') {
      account = body.email.startsWith('beta') ? 'Beta' : 'Alpha';
      return send(issue());
    }
    if (path === 'auth/refresh') {
      refreshCalls++;
      assert.equal(body.refresh_token, currentRefresh);
      assert.equal(usedRefreshes.has(body.refresh_token), false, 'A rotating capability must never be reused');
      usedRefreshes.add(body.refresh_token);
      if (holdRefresh) { refreshReady.resolve(); await refreshRelease.promise; }
      return send(issue());
    }
    if (path === 'auth/logout') {
      logoutCalls++;
      assert.equal(body.refresh_token, currentRefresh, 'Logout must use the rotated successor');
      return send(null, 204);
    }
    const authorized = req.headers.authorization === 'Bearer ' + currentAccess && !expired;
    if (!authorized) {
      if (path === 'auth/me' && initialCount < 2) {
        initialCount++;
        if (initialCount === 2) initialFailures.resolve();
        await initialFailures.promise;
      }
      return send({ message: 'Access expired' }, 401);
    }
    if (path === 'branches' && holdBranch) {
      holdBranch = false; branchReady.resolve(); await branchRelease.promise;
      return send({ message: 'Delayed earlier authorization failure' }, 401);
    }
    if (req.method === 'POST') seenCommands.push({ path, account });
    if (path === 'auth/me') return send({ id: org, name: account + ' Account', email: account.toLowerCase() + '@example.test', organizations: [org] });
    if (path === 'auth/context') return send({ organization: { id: org, name: account + ' Cafe' }, permissions, branch_permissions: {} });
    if (path === 'organizations') return send([{ id: org, name: account + ' Cafe' }]);
    if (path === 'branches') return send({ items: [{ id: org, name: account + ' Branch', code: 'BR01', city: null, status: 'ACTIVE' }], page: 1, page_size: 20 });
    return send({ message: 'Unexpected fixture route' }, 404);
  } catch (error) {
    console.error('Fixture assertion failed:', error.message);
    return send({ message: 'Fixture assertion failed' }, 500);
  }
});
await new Promise(resolve => upstream.listen(8000, '127.0.0.1', resolve));
const browser = await chromium.launch();
try {
  const context = await browser.newContext();
  await context.addCookies([{ name: 'sm_lang', value: 'en', url: baseURL }]);
  const first = await context.newPage(), second = await context.newPage();
  for (const page of [first, second]) page.setDefaultTimeout(15_000);
  async function identity(page, who) {
    await page.locator('header').getByText(who + ' Account', { exact: false }).waitFor();
  }
  async function signIn(page, who) {
    await page.locator('input[name="email"]').fill(who.toLowerCase() + '@example.test');
    await page.locator('input[name="password"]').fill('disposable-browser-fixture');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.waitForURL(baseURL + '/overview');
    await identity(page, who);
  }
  await first.goto(baseURL + '/login');
  await signIn(first, 'Alpha');
  await second.goto(baseURL + '/overview');
  await identity(second, 'Alpha');
  const oldContext = (await context.cookies()).find(cookie => cookie.name === 'sm_context').value;
  assert.equal(await first.evaluate(() => /sm_access=|sm_refresh=/.test(document.cookie)), false);

  // Both real BFF requests carry the same expired cookie snapshot.
  expired = true;
  await Promise.all([first.reload(), second.reload()]);
  await Promise.all([identity(first, 'Alpha'), identity(second, 'Alpha')]);
  assert.equal(refreshCalls, 1, 'Two tabs must issue exactly one refresh');
  assert.equal(initialCount, 2, 'The race must really contain two expired requests');

  // An older 401 arrives after another tab finished rotating.
  holdBranch = true;
  await first.getByRole('link', { name: 'Branches', exact: true }).click();
  await bounded(branchReady.promise, 'held branch request');
  expired = true;
  await second.reload();
  await identity(second, 'Alpha');
  assert.equal(refreshCalls, 2);
  branchRelease.resolve();
  await first.getByText('Alpha Branch', { exact: true }).waitFor();
  assert.equal(refreshCalls, 2, 'A late failure must reuse the renewed session');

  // Logout waits for rotation and revokes the successor, then Beta signs in.
  holdRefresh = true; expired = true;
  await first.reload();
  await bounded(refreshReady.promise, 'held refresh request');
  await second.getByRole('button', { name: 'Sign out', exact: true }).click();
  await second.waitForFunction(async () => (await navigator.locks.query()).pending.some(lock => lock.name === 'smart-merchant-session'));
  assert.equal(logoutCalls, 0, 'Logout must wait until refresh cookies have been applied');
  refreshRelease.resolve();
  await second.waitForURL(baseURL + '/login');
  assert.equal(logoutCalls, 1);
  await signIn(second, 'Beta');
  const denied = await second.evaluate(async previous => {
    const response = await fetch('/api/proxy/branches', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Session-Context': previous }, body: '{}' });
    return response.status;
  }, oldContext);
  assert.equal(denied, 409);
  assert.deepEqual(seenCommands, [], 'An earlier account command must not reach the backend');
  await first.reload();
  await identity(first, 'Beta');
  assert.equal(await second.evaluate(() => /sm_access=|sm_refresh=/.test(document.cookie)), false);
  console.log('PASS: real Next.js BFF, two-tab renewal, delayed 401, serialized logout, stale-command rejection and HttpOnly credentials');
} finally {
  initialFailures.resolve(); branchRelease.resolve(); refreshRelease.resolve();
  await browser.close();
  upstream.closeAllConnections();
  await new Promise(resolve => upstream.close(resolve));
}
