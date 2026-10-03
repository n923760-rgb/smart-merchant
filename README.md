# Smart Merchant Assistant — General Accounting & Business Platform

Sector-neutral multi-tenant accounting and business platform. The shared core is accounting, invoicing, customers and suppliers; POS, inventory and recipes are optional modules. The [Unified Master Prompt v2](docs/product/SMART_MERCHANT_MASTER_PROMPT_V2.md) merges earlier scope with the owner's 2026-10-03 direction: no mandatory restaurant, food-truck or other business category.

Implemented foundation: identity, organizations, branches, RBAC, terminals, audit, web shell and POS/owner Flutter shells. The first accounting slice adds chart accounts and balanced immutable journal posting/reversal with durable request replay, tenant/branch RBAC and database enforcement. It requires no POS terminal or shift; initial monetary qualification is SAR. Invoicing, AR/AP, fiscal integration, accounting periods/reports, catalog, POS sales, inventory, analytics and AI remain unimplemented. No full accounting or production-readiness claim is made.

## Start locally

Prerequisites: Docker Compose, Node.js 22, Flutter stable (for mobile projects). Copy `.env.example` to `.env`, replace all sample secrets and set `POSTGRES_PASSWORD`. If the password contains URL-reserved characters, percent-encode it in `DATABASE_URL` or choose a URL-safe password.

```sh
cp .env.example .env
docker compose up -d --build
docker compose exec backend alembic upgrade head
curl http://localhost:8000/health/ready
```

Create the first owner and organization using a strong `X-Bootstrap-Key` equal to `BOOTSTRAP_KEY` in `.env`. Never put that key in browser code. The endpoint `POST /api/v1/bootstrap` creates owner, organization, active membership, initial permission catalog and roles in one transaction. For isolated development demo data, export `DEV_SEED_PASSWORD` with a unique 12+ character value and run `make seed`. Demo email addresses are `owner-demo@example.com`, `manager-demo@example.com`, `cashier-demo@example.com`.

```sh
cd apps/web
npm install
npm run dev
```

Visit `http://localhost:3000/login`. API docs are at `http://localhost:8000/docs`. The web BFF defaults to `http://localhost:8000`; configure server-only `BACKEND_URL` for another backend. Web cookies are HttpOnly, SameSite=Strict and Secure in production; always serve production over HTTPS. The owner app accepts `--dart-define=API_URL=https://your-api-host`. The POS and owner Flutter projects are package skeletons: run `flutter create . --platforms=android,ios && rm -f test/widget_test.dart` in each project to generate platform runners and remove Flutter's unrelated default test, then `flutter pub get` and `flutter run`. The web login and navigation have Arabic/English direction and labels; operational page copy is currently Arabic-first and needs completion before a full English launch.

Run `make migrate`, `make test`, `make lint` as needed. Integration tests require a migrated disposable PostgreSQL database at `smart_merchant_test` and Redis DB 1. CI provisions both. Set branch protection in GitHub repository settings to require PR, review and all checks in `.github/workflows/ci.yml` before merge. The current connector does not provide administration writes; enforcement must be verified using a capable GitHub administration environment. CI checks still run on pull requests.

## Current acceptance status

General accounting scope, core and read-only workspace are integrated through reviewed PRs #15/#11/#12/#13/#14. Application integration at main f7e31d719ad0527d2a305270e944a251738ba976 retained the exact qualified application tree. All final Foundation (nine jobs), Governance and real-ledger browser gates passed: 80 web tests, 51 backend tests, actual PostgreSQL/BFF/Chromium, migration roundtrip, zero-vulnerability dependency audit and Android/iOS simulator builds. See the [integration receipt](ENGINEERING/REPORTS/GENERAL_ACCOUNTING_INTEGRATION.md) for exact sources/runs. Physical/pilot/production acceptance remains incomplete; each later source needs its own qualification.

The Foundation CI workflow passes backend lint/type checks, PostgreSQL and Redis integration tests, Alembic upgrade/check/downgrade/upgrade, Python dependency audit, web lint/type checks/tests/production build and `npm audit`, Flutter analyze/tests for both apps, and Gitleaks secret scanning. A separate CI job builds and starts the complete Docker Compose stack, runs migrations and the demo seed, and checks readiness, the worker and owner login. Flutter CI generates Android/iOS runners, builds debug Android APKs, and builds iOS simulator apps for POS and owner on macOS. The tenant-isolation, RBAC, authentication, migration and CI gates pass. Hands-on device testing remains outstanding; platform runners are generated in CI and with the documented local command, rather than committed. Foundation source is integrated through PR #1; physical-device acceptance remains incomplete. Do **not** start catalog work until the foundation is fully accepted. See [testing strategy](docs/testing/testing-strategy.md).

## Engineering and product requirements

Development-agent instructions: [governance/START_HERE.md](governance/START_HERE.md). Project state and next task: [ENGINEERING/MASTER_ROADMAP.md](ENGINEERING/MASTER_ROADMAP.md). These configure a coding session; no persistent agent service is installed. POS v1 [transaction rules](docs/product/POS_TRANSACTION_FLOW_V1.md), [delivery/policy plan](docs/product/POS_DELIVERY_PLAN_V1.md) and [acceptance matrix](docs/product/POS_ACCEPTANCE_V1.md) define the next merchant work; acceptance remains NOT RUN. Telegram remains deferred.

## General ledger API — first slice

With an authenticated organization context, OWNER/ACCOUNTANT may create organization-level accounts (`POST /api/v1/accounting/accounts`), list them, post balanced journals (`POST /api/v1/accounting/journals`) and read/reverse journals. Branch-scoped accountants may post/read/reverse only their allowed branch; global chart management needs a global grant. JSON monetary values are decimal strings. Every journal/reversal request carries a persistent UUID `request_id`; retain the same ID and payload after an unknown result. Completed entries have no update/delete endpoint and PostgreSQL rejects mutation or additional lines. Reversals keep the original unchanged. Mobile accounting screens, manual posting/reversal UI, invoice-to-journal rules and reports need separate implementation.

The integrated `/accounting` web workspace provides Arabic/English read-only chart accounts, journal pagination/details and original-reversal linkage without POS setup. Accounting-only users land there without extra organization/device grants. Each resource/scope is independently authorized; branch-only users cannot issue unscoped lists. Amounts retain exact backend decimal strings, not browser floats. Its separate [real ledger/BFF browser CI](.github/workflows/accounting-web.yml) uses disposable services. See the [workspace report](ENGINEERING/REPORTS/ACCOUNTING_WEB_WORKSPACE.md) for qualification limits and the historical audit failure.

Next general-accounting slice: explicitly confirmed journal creation in the web UI with durable request identity and unknown-result reconciliation; then account hierarchy/periods, customers/suppliers, documents/settlements and ledger-reconciled reports. Read-only UI does not yet provide manual posting/reversal controls.

Post-merge Accounting Web exposed a late observation boundary in the test fixture. Test-only PR #17 starts capture before automatic accounting landing and requires each authorized resource/branch pair with all real denials retained. It merged at 5831c8f3a035dfbff9374e086376447e6013c524 after all Foundation/Governance/Accounting Web gates passed (37129241430/37129241513/37129241502). This refreshed documentation source carries that correction and needs its own current checks; the initial failing main/docs runs remain in the receipt.
