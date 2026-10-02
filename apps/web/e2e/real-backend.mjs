import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { chromium } from 'playwright';

// This destructive fixture is for a fresh disposable CI database, never a merchant lab.
const baseURL = process.env.SM_TEST_BASE_URL ?? 'http://127.0.0.1:3000';
const backendURL = process.env.SM_TEST_BACKEND_URL ?? 'http://127.0.0.1:8000';
for (const value of [baseURL, backendURL]) {
  const url = new URL(value);
  assert.ok(url.protocol === 'http:' && url.hostname === '127.0.0.1', 'Only loopback HTTP test services are allowed');
}
assert.equal(process.env.SM_DISPOSABLE_E2E, '1', 'Explicit disposable-test opt-in required');
assert.ok(process.env.BOOTSTRAP_KEY, 'Disposable bootstrap key required');
const suffix = randomUUID();
const password = randomUUID() + randomUUID();
// Playwright timeout diagnostics can include fill arguments. Mask before any UI use.
function mask(value) {
  if (process.env.GITHUB_ACTIONS === 'true') console.log(`::add-mask::${value}`);
}
mask(password);
const alphaEmail = `alpha-${suffix}@example.com`;
const betaEmail = `beta-${suffix}@example.com`;

async function backend(path, body, expected = 200, headers = {}) {
  const response = await fetch(`${backendURL}/api/v1/${path}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body), signal: AbortSignal.timeout(10_000),
  });
  assert.equal(response.status, expected, `Backend ${path} status`);
  // Do not include raw responses or credentials in failure messages/artifacts.
  return response.status === 204 ? null : response.json();
}

async function ready() {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      const results = await Promise.all([baseURL + '/login', backendURL + '/health/ready'].map(
        url => fetch(url, { signal: AbortSignal.timeout(2_000) }),
      ));
      if (results.every(response => response.ok)) return;
    } catch { /* bounded readiness polling, not mutation retry */ }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('Disposable web/backend did not become ready');
}

// Browser-origin requests use real HttpOnly cookies, context binding and Web Locks.
// These API commands are not claimed as full management-form acceptance.
async function bff(page, path, method = 'GET', body, expected = 200) {
  const result = await page.evaluate(async ({ path, method, body }) => {
    return navigator.locks.request('smart-merchant-session', async () => {
      const context = document.cookie.split('; ').find(c => c.startsWith('sm_context='))?.slice(11);
      const response = await fetch('/api/proxy/' + path, {
        method, headers: { 'Content-Type': 'application/json', 'X-Session-Context': context ?? '' },
        body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(12_000),
      });
      return { status: response.status, data: response.status === 204 ? null : await response.json() };
    });
  }, { path, method, body });
  assert.equal(result.status, expected, `BFF ${method} ${path} status`);
  return result.data;
}

async function signIn(browser, email, name, denied = false) {
  const context = await browser.newContext();
  await context.addCookies([{ name: 'sm_lang', value: 'en', url: baseURL }]);
  const page = await context.newPage();
  page.setDefaultTimeout(15_000);
  page.setDefaultNavigationTimeout(20_000);
  await page.goto(baseURL + '/login');
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.waitForURL(baseURL + '/overview');
  if (denied) await page.getByRole('alert').filter({ hasText: 'Access denied.' }).waitFor();
  else await page.locator('header').filter({ hasText: name }).waitFor();
  return { context, page };
}

function refreshCookie(cookies) {
  const value = cookies.find(c => c.name === 'sm_refresh')?.value;
  assert.ok(value, 'Refresh cookie exists');
  mask(value);
  return value;
}

async function submitCreate(page, resource, fields, button, expected = 201) {
  // Only the top-level create form has an email/device identifier input.
  const key = resource === 'users' ? 'email' : 'device_identifier';
  const form = page.locator('form').filter({ has: page.locator(`input[name="${key}"]`) });
  for (const [name, value] of Object.entries(fields)) {
    if (name === 'branch_id') await form.locator('select[name="branch_id"]').selectOption(value);
    else await form.locator(`input[name="${name}"]`).fill(value);
  }
  const response = page.waitForResponse(r => new URL(r.url()).pathname === `/api/proxy/${resource}` && r.request().method() === 'POST');
  await form.getByRole('button', { name: button, exact: true }).click();
  const result = await response;
  assert.equal(result.status(), expected, `Rendered ${resource} create status`);
  // Next.js also uses role=alert in its screen-reader route announcer shadow DOM.
  // Only this page's explicit mutation error is relevant to form outcome.
  const mutationError = page.locator('section > p[role="alert"]');
  if (expected === 201) {
    // This times out on the old post-await event.currentTarget handler, even if
    // its backend mutation committed and query invalidation refreshed the list.
    await page.waitForFunction(key => document.querySelector(`input[name="${key}"]`)?.value === '', key);
    assert.equal(await mutationError.count(), 0, 'No false/stale success error');
  } else {
    await mutationError.waitFor();
    for (const [name, value] of Object.entries(fields)) {
      const retained = await form.locator(`[name="${name}"]`).inputValue();
      // Boolean assertion avoids retaining password values on a failure.
      assert.ok(retained === value, `Rejected ${resource} retains ${name} input`);
    }
  }
  return result.json();
}

await ready();
const alpha = await backend('bootstrap', {
  owner_name: 'E2E Alpha Owner', owner_email: alphaEmail, owner_password: password,
  organization_name: 'E2E Alpha Merchant',
}, 201, { 'X-Bootstrap-Key': process.env.BOOTSTRAP_KEY });
const beta = await backend('bootstrap', {
  owner_name: 'E2E Beta Owner', owner_email: betaEmail, owner_password: password,
  organization_name: 'E2E Beta Merchant',
}, 201, { 'X-Bootstrap-Key': process.env.BOOTSTRAP_KEY });
assert.notEqual(alpha.organization.id, beta.organization.id);
const browser = await chromium.launch();
try {
  const owner = await signIn(browser, alphaEmail, 'E2E Alpha Owner');
  const me = await bff(owner.page, 'auth/me');
  assert.equal(me.id, alpha.owner.id);
  assert.deepEqual(me.organizations, [alpha.organization.id]);
  const permissions = await bff(owner.page, 'permissions');
  assert.ok(permissions.items.some(p => p.code === 'roles.manage'));

  // Real rendered branch form -> production BFF -> migrated PostgreSQL.
  await owner.page.getByRole('link', { name: 'Branches', exact: true }).click();
  await owner.page.locator('input[name="name"]').fill('E2E Abha');
  await owner.page.locator('input[name="code"]').fill('E2E_ABH');
  await owner.page.locator('input[name="city"]').fill('Abha');
  const created = owner.page.waitForResponse(r => new URL(r.url()).pathname === '/api/proxy/branches' && r.request().method() === 'POST');
  await owner.page.getByRole('button', { name: 'إضافة فرع', exact: true }).click();
  const createdResponse = await created;
  assert.equal(createdResponse.status(), 201);
  const branch = await createdResponse.json();
  await owner.page.getByRole('cell', { name: 'E2E Abha', exact: true }).waitFor();
  assert.equal(branch.organization_id, alpha.organization.id);
  const other = await bff(owner.page, 'branches', 'POST', { name: 'E2E Khamis', code: 'E2E_KHM' }, 201);
  const roles = (await bff(owner.page, 'roles')).items;
  await owner.page.getByRole('link', { name: 'Users', exact: true }).click();
  const managerFields = {
    name: 'E2E Manager', email: `manager-${suffix}@example.com`, password,
  };
  const manager = await submitCreate(owner.page, 'users', managerFields, 'إضافة');
  await owner.page.locator('article').filter({ hasText: manager.email }).waitFor();
  const assignment = await bff(owner.page, `users/${manager.id}/roles`, 'POST', {
    role_id: roles.find(r => r.code === 'MANAGER').id, branch_id: branch.id,
  }, 201);
  await submitCreate(owner.page, 'users', managerFields, 'إضافة', 409);
  const cashier = await submitCreate(owner.page, 'users', {
    name: 'E2E Cashier', email: `cashier-${suffix}@example.com`, password,
  }, 'إضافة');
  await owner.page.locator('article').filter({ hasText: cashier.email }).waitFor();
  await bff(owner.page, `users/${cashier.id}/roles`, 'POST', {
    role_id: roles.find(r => r.code === 'CASHIER').id, branch_id: branch.id,
  }, 201);
  const detail = await bff(owner.page, `users/${manager.id}`);
  assert.ok(detail.roles.some(r => r.code === 'MANAGER' && r.branch_id === branch.id));
  await owner.page.getByRole('link', { name: 'Devices', exact: true }).click();
  const terminalFields = {
    name: 'E2E Terminal', device_identifier: `e2e-${suffix}`, branch_id: branch.id,
  };
  const terminal = await submitCreate(owner.page, 'terminals', terminalFields, 'إنشاء');
  await owner.page.getByRole('cell', { name: 'E2E Terminal', exact: true }).waitFor();
  // Send an invalid branch value through the actual form/BFF for a real 422.
  // No HTTP interception; this deliberately exercises rejected input preservation.
  await owner.page.locator('select[name="branch_id"]').evaluate(select => {
    select.add(new Option('Invalid test branch', 'not-a-uuid'));
  });
  await submitCreate(owner.page, 'terminals', {
    ...terminalFields, branch_id: 'not-a-uuid',
  }, 'إنشاء', 422);
  await submitCreate(owner.page, 'terminals', {
    name: 'E2E Retry Terminal', device_identifier: `e2e-retry-${suffix}`, branch_id: branch.id,
  }, 'إنشاء');
  await owner.page.getByRole('cell', { name: 'E2E Retry Terminal', exact: true }).waitFor();
  assert.equal(terminal.activation_status, 'PENDING');
  await bff(owner.page, `terminals/${terminal.id}`, 'PATCH', { name: 'E2E Renamed Terminal' });
  // A direct fixture API rename is outside React Query's mutation callbacks.
  await owner.page.reload();
  const terminalRow = owner.page.getByRole('row').filter({ hasText: 'E2E Renamed Terminal' });
  await terminalRow.waitFor();
  const revocation = owner.page.waitForResponse(r => new URL(r.url()).pathname === `/api/proxy/terminals/${terminal.id}/revoke`);
  await terminalRow.getByRole('button', { name: 'إلغاء', exact: true }).click();
  assert.equal((await revocation).status(), 200);
  await terminalRow.getByRole('cell', { name: 'REVOKED', exact: true }).waitFor();

  const audit = (await bff(owner.page, 'audit?page_size=100')).items;
  for (const [action, id] of [
    ['BRANCH_CREATED', branch.id], ['USER_INVITED', manager.membership_id],
    ['ROLE_ASSIGNED', assignment.id], ['TERMINAL_CREATED', terminal.id],
    ['TERMINAL_RENAMED', terminal.id], ['TERMINAL_REVOKED', terminal.id],
  ]) assert.ok(audit.some(e => e.action === action && e.entity_id === id), `Audit ${action}`);
  await bff(owner.page, `users/${alpha.owner.id}/disable`, 'POST', {}, 409);

  const scoped = await signIn(browser, manager.email, 'E2E Manager');
  await scoped.page.getByRole('link', { name: 'Branches', exact: true }).click();
  await scoped.page.getByRole('cell', { name: 'E2E Abha', exact: true }).waitFor();
  assert.equal(await scoped.page.getByRole('cell', { name: 'E2E Khamis', exact: true }).count(), 0);
  assert.equal(await scoped.page.locator('input[name="code"]').count(), 0);
  assert.equal(await scoped.page.getByRole('link', { name: 'Users', exact: true }).count(), 0);
  assert.equal(await scoped.page.getByRole('link', { name: 'Roles', exact: true }).count(), 0);
  const scopedBranches = await bff(scoped.page, 'branches');
  assert.deepEqual(scopedBranches.items.map(b => b.id), [branch.id]);
  await bff(scoped.page, `branches/${branch.id}`);
  const denied = await bff(scoped.page, `branches/${other.id}`, 'GET', undefined, 403);
  assert.equal(denied.code, 'INSUFFICIENT_PERMISSION');
  assert.deepEqual(denied.details, {});
  assert.ok(denied.request_id);
  await bff(scoped.page, 'branches', 'POST', { name: 'Forbidden', code: 'DENIED' }, 403);
  await bff(scoped.page, `terminals/${terminal.id}/revoke`, 'POST', {}, 403);
  await bff(scoped.page, `users/${manager.id}/roles`, 'POST', { role_id: roles.find(r => r.code === 'OWNER').id }, 403);

  const minimal = await signIn(browser, cashier.email, 'E2E Cashier', true);
  assert.equal(await minimal.page.getByRole('link', { name: 'Branches', exact: true }).count(), 0);
  await bff(minimal.page, 'branches', 'POST', { name: 'Forbidden', code: 'DENIED' }, 403);

  const foreign = await signIn(browser, betaEmail, 'E2E Beta Owner');
  assert.deepEqual((await bff(foreign.page, 'branches')).items, []);
  assert.equal((await bff(foreign.page, `branches/${branch.id}`, 'GET', undefined, 404)).code, 'NOT_FOUND');
  await bff(foreign.page, `branches/${branch.id}`, 'PATCH', { name: 'Intrusion' }, 404);
  await bff(foreign.page, `users/${manager.id}`, 'GET', undefined, 404);
  await bff(foreign.page, `terminals/${terminal.id}/revoke`, 'POST', {}, 404);
  await bff(foreign.page, 'terminals', 'POST', { name: 'Intrusion', device_identifier: 'foreign', branch_id: branch.id }, 404);
  const foreignAudit = (await bff(foreign.page, 'audit')).items;
  assert.ok(foreignAudit.every(e => !audit.some(a => a.id === e.id)));
  assert.equal((await bff(owner.page, `branches/${branch.id}`)).name, 'E2E Abha');
  assert.equal((await bff(owner.page, 'terminals')).items[0].activation_status, 'REVOKED');

  // Real rotation and revocation; token values stay in memory and never in logs.
  const before = await owner.context.cookies();
  for (const name of ['sm_access', 'sm_refresh', 'sm_org']) {
    assert.ok(before.some(c => c.name === name && c.httpOnly && c.sameSite === 'Strict'), `${name} protected cookie`);
  }
  assert.ok(await owner.page.evaluate(() => !/sm_access=|sm_refresh=|sm_org=/.test(document.cookie)));
  const oldRefresh = refreshCookie(before);
  const status = await owner.page.evaluate(() => navigator.locks.request('smart-merchant-session', async () => {
    const context = document.cookie.split('; ').find(c => c.startsWith('sm_context='))?.slice(11);
    return (await fetch('/api/session/refresh', { method: 'POST', headers: { 'X-Session-Context': context }, signal: AbortSignal.timeout(12_000) })).status;
  }));
  assert.equal(status, 200);
  const newRefresh = refreshCookie(await owner.context.cookies());
  assert.ok(newRefresh !== oldRefresh, 'Refresh capability rotated');
  await backend('auth/refresh', { refresh_token: oldRefresh }, 401);
  assert.equal((await bff(owner.page, 'auth/me')).id, alpha.owner.id);
  await owner.page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await owner.page.waitForURL(baseURL + '/login');
  assert.ok(!(await owner.context.cookies()).some(c => ['sm_access', 'sm_refresh', 'sm_org'].includes(c.name)));
  await backend('auth/refresh', { refresh_token: newRefresh }, 401);
  console.log('PASS: real-backend Chromium foundation (rendered user/device success, rejection/retry; RBAC, tenant/audit, rotation/logout)');
} finally {
  await browser.close();
}
