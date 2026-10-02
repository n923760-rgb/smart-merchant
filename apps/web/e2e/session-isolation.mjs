import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const baseURL = process.env.SM_TEST_BASE_URL ?? 'http://127.0.0.1:3000';
const permissions = [
  'organization.read', 'branches.read', 'branches.create', 'branches.update',
  'users.read', 'users.invite', 'users.manage', 'roles.read', 'roles.manage',
  'terminals.read', 'terminals.manage',
];
const alpha = {
  name: 'Alpha Account', email: 'alpha@example.test',
  org: '11111111-1111-4111-8111-111111111111', organizationName: 'Alpha Cafe',
  branch: '11111111-1111-4111-8111-111111111112', branchName: 'Alpha Branch',
  staffName: 'Alpha Staff', terminalName: 'Alpha Terminal',
};
const beta = {
  name: 'Beta Account', email: 'beta@example.test',
  org: '22222222-2222-4222-8222-222222222222', organizationName: 'Beta Cafe',
  branch: '22222222-2222-4222-8222-222222222223', branchName: 'Beta Branch',
  staffName: 'Beta Staff', terminalName: 'Beta Terminal',
};
const alphaData = /Alpha Account|Alpha Cafe|Alpha Branch|Alpha Staff|Alpha Terminal/;

function deferred() {
  let resolve;
  const promise = new Promise(complete => { resolve = complete; });
  return { promise, resolve };
}

async function bounded(promise, label) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('Timed out: ' + label)), 15_000);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

async function waitForServer() {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      if ((await fetch(baseURL + '/login', { signal: AbortSignal.timeout(2_000) })).ok) return;
    } catch { /* The production server may still be starting. */ }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('Next.js server did not become ready');
}

function fixture(who, path) {
  if (path === 'auth/me') return { id: who.org, name: who.name, email: who.email, organizations: [who.org] };
  if (path === 'auth/context') return {
    organization: { id: who.org, name: who.organizationName },
    permissions, branch_permissions: {},
  };
  if (path === 'organizations') return [{ id: who.org, name: who.organizationName }];
  const page = items => ({ items, page: 1, page_size: 20 });
  if (path === 'branches') return page([
    { id: who.branch, name: who.branchName, code: 'BR01', city: null, status: 'ACTIVE' },
  ]);
  if (path === 'users') return page([
    { id: who.branch, name: who.staffName, email: 'staff@example.test', status: 'ACTIVE', membership_id: who.branch },
  ]);
  if (path === 'roles') return page([{ id: who.branch, name: 'Owner', code: 'OWNER' }]);
  if (path === 'terminals') return page([
    { id: who.branch, name: who.terminalName, branch_id: who.branch, activation_status: 'ACTIVE', last_seen_at: null, app_version: null },
  ]);
  throw new Error('Unexpected proxy request: ' + path);
}

await waitForServer();
const browser = await chromium.launch();
const oldReady = deferred();
const oldRelease = deferred();
const oldFinished = deferred();
const gates = new Map(['auth/me', 'branches', 'users', 'terminals'].map(path => [
  path, { ready: deferred(), release: deferred() },
]));
let delayOldUsers = false;
let account = null;
let selectedOrganization = null;
const organizationSelections = [];

try {
  const context = await browser.newContext();
  await context.addCookies([{ name: 'sm_lang', value: 'en', url: baseURL }]);
  const page = await context.newPage();
  page.setDefaultTimeout(15_000);

  await page.route('**/api/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const send = (data, status = 200) => route.fulfill({
      status, contentType: 'application/json', body: JSON.stringify(data),
    });

    if (path === '/api/session') {
      if (request.method() === 'DELETE') {
        account = null;
        selectedOrganization = null;
        return send({ authenticated: false });
      }
      const { email } = request.postDataJSON();
      account = [alpha, beta].find(candidate => candidate.email === email);
      assert.ok(account, 'Only explicit test accounts may log in');
      return send({ authenticated: true });
    }

    if (path === '/api/session/organization') {
      selectedOrganization = request.postDataJSON().id;
      organizationSelections.push({ account: account?.name, id: selectedOrganization });
      return send({ id: selectedOrganization });
    }

    assert.ok(path.startsWith('/api/proxy/'), 'Unexpected API route: ' + path);
    const endpoint = path.slice('/api/proxy/'.length);
    const who = account;
    if (!who) return send({ message: 'Unauthenticated' }, 401);
    if (endpoint !== 'auth/me' && selectedOrganization !== who.org) {
      return send({ message: 'Wrong organization' }, 404);
    }
    const data = fixture(who, endpoint);
    if (who === alpha && endpoint === 'users' && delayOldUsers) {
      oldReady.resolve();
      await oldRelease.promise;
      await send(data);
      oldFinished.resolve();
      return;
    }
    const gate = who === beta ? gates.get(endpoint) : null;
    if (gate) {
      gate.ready.resolve();
      await gate.release.promise;
    }
    return send(data);
  });

  async function signIn(who) {
    await page.locator('input[name="email"]').fill(who.email);
    // Synthetic fixture only; all session API calls are intercepted.
    await page.locator('input[name="password"]').fill('browser-fixture-only');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.waitForURL(baseURL + '/overview');
  }

  async function visit(label, text) {
    await page.getByRole('link', { name: label, exact: true }).click();
    await page.getByText(text, { exact: true }).waitFor();
  }

  await page.goto(baseURL + '/login');
  await signIn(alpha);
  await page.locator('header').getByText(alpha.name, { exact: false }).waitFor();
  await page.getByText(alpha.organizationName, { exact: true }).waitFor();
  await visit('Branches', alpha.branchName);
  await visit('Users', alpha.staffName);
  await visit('Devices', alpha.terminalName);

  // Leave an earlier account's request alive across both auth transitions.
  delayOldUsers = true;
  await page.getByRole('link', { name: 'Users', exact: true }).click();
  await bounded(oldReady.promise, 'old account request');
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.waitForURL(baseURL + '/login');
  assert.doesNotMatch(await page.locator('body').innerText(), alphaData);

  await signIn(beta);
  await bounded(gates.get('auth/me').ready.promise, 'new account identity');
  oldRelease.resolve();
  await bounded(oldFinished.promise, 'late old account response');
  // Let effects and completed response callbacks settle before checking visibility.
  await page.evaluate(() => new Promise(resolve => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  }));
  assert.doesNotMatch(await page.locator('body').innerText(), alphaData);
  assert.equal(
    organizationSelections.filter(entry => entry.account === beta.name && entry.id === alpha.org).length,
    0,
    'The next account must never select the previous organization',
  );

  gates.get('auth/me').release.resolve();
  await page.locator('header').getByText(beta.name, { exact: false }).waitFor();
  await page.getByText(beta.organizationName, { exact: true }).waitFor();
  assert.equal(selectedOrganization, beta.org);

  for (const [label, endpoint, text] of [
    ['Branches', 'branches', beta.branchName],
    ['Users', 'users', beta.staffName],
    ['Devices', 'terminals', beta.terminalName],
  ]) {
    await page.getByRole('link', { name: label, exact: true }).click();
    const gate = gates.get(endpoint);
    await bounded(gate.ready.promise, 'new account ' + endpoint);
    assert.doesNotMatch(await page.locator('body').innerText(), alphaData);
    gate.release.resolve();
    await page.getByText(text, { exact: true }).waitFor();
    assert.doesNotMatch(await page.locator('body').innerText(), alphaData);
  }

  assert.equal(organizationSelections.some(entry => entry.account === beta.name && entry.id === alpha.org), false);
  console.log('PASS: account/organization isolation, resource-cache reset and late previous-account response');
} finally {
  oldRelease.resolve();
  for (const gate of gates.values()) gate.release.resolve();
  await browser.close();
}
