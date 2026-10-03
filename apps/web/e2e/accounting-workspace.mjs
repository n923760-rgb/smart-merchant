// Disposable, real FastAPI/PostgreSQL + production Next.js/BFF + Chromium.
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { chromium } from "playwright";

const baseURL = process.env.SM_TEST_BASE_URL ?? "http://127.0.0.1:3000";
const backendURL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
const bootstrapKey = process.env.BOOTSTRAP_KEY;
const password = process.env.SM_ACCOUNTING_TEST_PASSWORD;
assert.ok(
  bootstrapKey && password,
  "Explicit disposable fixture credentials are required",
);
for (const url of [baseURL, backendURL])
  assert.ok(
    new URL(url).protocol === "http:" &&
      ["127.0.0.1", "localhost"].includes(new URL(url).hostname),
    "Only an explicit loopback disposable application may receive fixture writes",
  );

async function backend(
  path,
  { token, org, method = "GET", body, bootstrap = false } = {},
) {
  const response = await fetch(`${backendURL}/api/v1/${path}`, {
    method,
    signal: AbortSignal.timeout(10_000),
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(org ? { "X-Organization-ID": org } : {}),
      ...(bootstrap ? { "X-Bootstrap-Key": bootstrapKey } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  assert.ok(
    response.ok,
    `Disposable fixture ${method} ${path} returned ${response.status}`,
  );
  return response.status === 204 ? null : response.json();
}

async function merchant(name) {
  const email = `${name.toLowerCase()}-${randomUUID()}@example.test`;
  const seed = await backend("bootstrap", {
    method: "POST",
    bootstrap: true,
    body: {
      owner_name: `${name} Owner`,
      owner_email: email,
      owner_password: password,
      organization_name: `${name} Services`,
    },
  });
  const login = await backend("auth/login", {
    method: "POST",
    body: { email, password },
  });
  const ctx = { org: seed.organization.id, token: login.access_token };
  const cash = await backend("accounting/accounts", {
    ...ctx,
    method: "POST",
    body: { code: "1000", name: `${name} Cash`, account_type: "ASSET" },
  });
  const revenue = await backend("accounting/accounts", {
    ...ctx,
    method: "POST",
    body: {
      code: "4000",
      name: `${name} Service Revenue`,
      account_type: "REVENUE",
    },
  });
  assert.equal(
    (await backend("terminals", ctx)).items.length,
    0,
    "Service accounting needs no terminals",
  );
  return { ...ctx, email, name, cash, revenue };
}

async function journal(who, description, branch = null, amount = "100.00") {
  return backend("accounting/journals", {
    ...who,
    method: "POST",
    body: {
      request_id: randomUUID(),
      branch_id: branch,
      booking_date: "2026-10-03",
      description,
      lines: [
        { account_id: who.cash.id, debit: amount },
        { account_id: who.revenue.id, credit: amount },
      ],
    },
  });
}
async function branch(who, code) {
  return (
    await backend("branches", {
      ...who,
      method: "POST",
      body: { code, name: code },
    })
  ).id;
}
async function employee(who, roleCode, branches = [null]) {
  const email = `accounting-${randomUUID()}@example.test`;
  const user = await backend("users", {
    ...who,
    method: "POST",
    body: { name: roleCode, email, password },
  });
  const roles = (await backend("roles?page_size=100", who)).items;
  const role = roles.find((candidate) => candidate.code === roleCode);
  for (const branch_id of branches)
    await backend(`users/${user.id}/roles`, {
      ...who,
      method: "POST",
      body: { role_id: role.id, branch_id },
    });
  return { email };
}

async function ready(url) {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      if ((await fetch(url, { signal: AbortSignal.timeout(2_000) })).ok) return;
    } catch {
      /* disposable startup */
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Disposable application did not become ready");
}
function gate() {
  let resolve;
  const promise = new Promise((complete) => {
    resolve = complete;
  });
  return { promise, resolve };
}
async function bounded(promise) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = setTimeout(
          () => reject(new Error("Browser fixture gate timed out")),
          15_000,
        );
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

await ready(`${backendURL}/health/ready`);
await ready(`${baseURL}/login`);
const alpha = await merchant("Alpha");
const beta = await merchant("Beta");
for (let i = 1; i <= 20; i++)
  await backend("accounting/accounts", {
    ...alpha,
    method: "POST",
    body: {
      code: `10${String(i).padStart(2, "0")}`,
      name: `Alpha Account ${i}`,
      account_type: "ASSET",
    },
  });
for (let i = 1; i <= 21; i++) await journal(alpha, `Alpha Service ${i}`);
const large = await journal(
  alpha,
  "Alpha Exact Decimal",
  null,
  "9007199254740993.01",
);
const reversal = await backend(`accounting/journals/${large.id}/reverse`, {
  ...alpha,
  method: "POST",
  body: {
    request_id: randomUUID(),
    booking_date: "2026-10-04",
    reason: "Alpha Correction",
  },
});
const b1 = await branch(alpha, "B1");
const b2 = await branch(alpha, "B2");
const b3 = await branch(alpha, "UNAUTHORIZED");
const branchOne = await journal(alpha, "Authorized branch one", b1);
await journal(alpha, "Authorized branch two", b2);
await journal(alpha, "Forbidden branch secret", b3);
await journal(beta, "Beta Service Only");
const accountant = await employee(alpha, "ACCOUNTANT");
const restricted = await employee(alpha, "ACCOUNTANT", [b1, b2]);
const cashier = await employee(alpha, "CASHIER");
const expectedAccounts = (
  await backend("accounting/accounts?page=1&page_size=20", alpha)
).items;
const expectedJournals = (
  await backend("accounting/journals?page=1&page_size=20", alpha)
).items;

const browser = await chromium.launch();
const delayed = gate();
try {
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(15_000);
  const accountingRequests = [];
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api/proxy/accounting/"))
      accountingRequests.push({ url: request.url(), method: request.method() });
  });
  async function signIn(who) {
    await page.goto(`${baseURL}/login`);
    await page.locator('input[name="email"]').fill(who.email);
    await page.locator('input[name="password"]').fill(password);
    await page
      .locator('form button[type="submit"], form button:not([type])')
      .click();
    await page.waitForURL((url) =>
      ["/overview", "/accounting"].includes(url.pathname),
    );
    await page.locator('a[href="/accounting"]').waitFor();
  }
  async function signOut() {
    await page
      .locator("header")
      .getByRole("button", { name: /Sign out|خروج/, exact: true })
      .click();
    await page.waitForURL(`${baseURL}/login`);
  }
  const accounts = () =>
    page.getByRole("region", {
      name: /Chart accounts|دليل الحسابات/,
      exact: true,
    });
  const journals = () =>
    page.getByRole("region", {
      name: /Posted journals|القيود المرحلة/,
      exact: true,
    });

  await signIn(accountant);
  await page.locator('a[href="/accounting"]').click();
  await page.getByRole("heading", { name: "المحاسبة", exact: true }).waitFor();
  await accounts().getByText("Alpha Cash", { exact: true }).waitFor();
  assert.equal(await page.locator("html").getAttribute("dir"), "rtl");
  assert.equal(
    await page.locator('a[href="/devices"]').count(),
    0,
    "Accountant needs no device permissions",
  );
  assert.equal(await page.locator('a[href="/roles"]').count(), 0);
  for (const row of expectedAccounts)
    assert.ok((await accounts().innerText()).includes(row.name));
  await journals()
    .getByText(expectedJournals[0].description, { exact: true })
    .waitFor();
  for (const row of expectedJournals)
    assert.ok((await journals().innerText()).includes(row.description));
  await accounts().getByRole("button", { name: "التالي", exact: true }).click();
  await accounts()
    .getByText("Alpha Service Revenue", { exact: true })
    .waitFor();
  assert.equal(
    await accounts()
      .getByRole("button", { name: "التالي", exact: true })
      .isDisabled(),
    true,
  );
  await accounts().getByRole("button", { name: "السابق", exact: true }).click();
  await accounts().getByText("Alpha Cash", { exact: true }).waitFor();
  await journals().getByRole("button", { name: "التالي", exact: true }).click();
  await journals().getByText("Alpha Correction", { exact: true }).waitFor();
  assert.equal(
    await journals()
      .getByRole("button", { name: "التالي", exact: true })
      .isDisabled(),
    true,
  );
  const correctionRow = journals()
    .getByRole("row")
    .filter({ hasText: "Alpha Correction" });
  await correctionRow
    .getByRole("button", { name: "عرض التفاصيل", exact: true })
    .click();
  const detail = page.getByRole("region", {
    name: "تفاصيل القيد",
    exact: true,
  });
  await detail.getByText(reversal.id, { exact: true }).waitFor();
  assert.ok(
    (await detail.innerText()).includes(large.id),
    "Historical reversal links to its original",
  );
  assert.ok(
    (await detail.innerText()).includes("9,007,199,254,740,993.01"),
    "Exact cents survive browser display",
  );
  await page.screenshot({
    path: "/tmp/smart-merchant-accounting-rtl.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    "Phone page does not overflow horizontally",
  );
  await page.screenshot({
    path: "/tmp/smart-merchant-accounting-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1280, height: 800 });

  // Controlled read failure is the only intercepted response; financial fixtures above use the real API.
  const accountRoute = "**/api/proxy/accounting/accounts?*";
  let failRead = true;
  await page.route(accountRoute, (route) =>
    failRead
      ? route.fulfill({
          status: 503,
          contentType: "application/json",
          body: '{"message":"Fixture read unavailable"}',
        })
      : route.continue(),
  );
  await page.reload();
  await accounts().getByRole("alert").waitFor();
  assert.equal(
    await accounts()
      .getByText("لا توجد سجلات في هذا النطاق.", { exact: true })
      .count(),
    0,
  );
  assert.equal(
    await accounts().getByText("Alpha Cash", { exact: true }).count(),
    0,
    "A failed refresh must hide stale rows",
  );
  failRead = false;
  await accounts()
    .getByRole("button", { name: "إعادة المحاولة", exact: true })
    .click();
  await accounts().getByText("Alpha Cash", { exact: true }).waitFor();
  await page.unroute(accountRoute);
  await signOut();

  await signIn(restricted);
  const scopeStart = accountingRequests.length;
  await page.locator('a[href="/accounting"]').click();
  await page.getByLabel("نطاق العرض", { exact: true }).selectOption(b1);
  await journals().getByText(branchOne.description, { exact: true }).waitFor();
  assert.equal(
    await page.getByRole("option", { name: "كل المنشأة", exact: true }).count(),
    0,
  );
  await journals()
    .getByRole("button", { name: "عرض التفاصيل", exact: true })
    .click();
  await page
    .getByRole("region", { name: "تفاصيل القيد", exact: true })
    .getByText(branchOne.id, { exact: true })
    .waitFor();
  await page.getByLabel("نطاق العرض", { exact: true }).selectOption(b2);
  await journals()
    .getByText("Authorized branch two", { exact: true })
    .waitFor();
  assert.equal(
    await page
      .getByRole("region", { name: "تفاصيل القيد", exact: true })
      .count(),
    0,
    "Scope changes clear journal details",
  );
  assert.doesNotMatch(
    await page.locator("main").innerText(),
    /Authorized branch one|Forbidden branch secret|Alpha Service \d/,
  );
  const scopedReads = accountingRequests
    .slice(scopeStart)
    .filter((item) =>
      /^\/api\/proxy\/accounting\/(accounts|journals)$/.test(
        new URL(item.url).pathname,
      ),
    );
  assert.ok(scopedReads.length >= 4);
  for (const request of scopedReads)
    assert.ok(
      [b1, b2].includes(new URL(request.url).searchParams.get("branch_id")),
      "No unscoped or foreign-branch list requests",
    );
  const contextCookie = (await context.cookies()).find(
    (cookie) => cookie.name === "sm_context",
  );
  assert.ok(contextCookie);
  const denied = await context.request.get(
    `${baseURL}/api/proxy/accounting/journals?branch_id=${b3}`,
    { headers: { "X-Session-Context": contextCookie.value } },
  );
  assert.equal(
    denied.status(),
    403,
    "Real backend denies a manually forged branch query",
  );
  assert.doesNotMatch(await denied.text(), /Forbidden branch secret/);
  await signOut();

  // A cashier must have neither the link nor read requests even after direct URL navigation.
  await page.goto(`${baseURL}/login`);
  await page.locator('input[name="email"]').fill(cashier.email);
  await page.locator('input[name="password"]').fill(password);
  await page
    .locator('form button[type="submit"], form button:not([type])')
    .click();
  await page.waitForURL(`${baseURL}/overview`);
  await page.locator("nav").waitFor({ state: "attached" });
  assert.equal(await page.locator('a[href="/accounting"]').count(), 0);
  const cashierStart = accountingRequests.length;
  await page.goto(`${baseURL}/accounting`);
  await page.getByRole("alert").waitFor();
  assert.equal(accountingRequests.length, cashierStart);
  await page.goto(`${baseURL}/overview`);
  await page.locator("nav").waitFor({ state: "attached" });
  await signOut();

  // Warm the accounting caches once more, then prove the next organization cannot see them.
  await signIn(accountant);
  await page.locator('a[href="/accounting"]').click();
  await accounts().getByText("Alpha Cash", { exact: true }).waitFor();
  await signOut();
  await signIn(beta);
  const waiting = gate();
  await page.route("**/api/proxy/accounting/**", async (route) => {
    waiting.resolve();
    await delayed.promise;
    await route.continue();
  });
  await page.locator('a[href="/accounting"]').click();
  await bounded(waiting.promise);
  assert.doesNotMatch(
    await page.locator("main").innerText(),
    /Alpha Cash|Alpha Service|Alpha Account|Forbidden branch/,
  );
  delayed.resolve();
  await accounts().getByText("Beta Cash", { exact: true }).waitFor();
  await journals().getByText("Beta Service Only", { exact: true }).waitFor();
  assert.doesNotMatch(
    await page.locator("main").innerText(),
    /Alpha Cash|Alpha Service|Alpha Account/,
  );
  await page.unroute("**/api/proxy/accounting/**");
  await page
    .locator("header")
    .getByRole("button", { name: "English", exact: true })
    .click();
  await page
    .getByRole("heading", { name: "Accounting", exact: true })
    .waitFor();
  assert.equal(await page.locator("html").getAttribute("dir"), "ltr");
  await page
    .getByRole("region", { name: "Chart accounts", exact: true })
    .getByText("Beta Cash", { exact: true })
    .waitFor();
  assert.ok(
    accountingRequests.every((request) => request.method === "GET"),
    "Accounting UI performs no financial writes",
  );
  assert.deepEqual(failures, [], "No browser runtime errors");
  console.log(
    "PASS: real ledger/BFF browser reads, exact money, no-terminal accountant, branch/tenant denial, pagination, explicit read error/retry, RTL/mobile/English and account cache isolation",
  );
} finally {
  delayed.resolve();
  await browser.close();
}
