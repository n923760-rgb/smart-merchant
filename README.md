# Smart Merchant Assistant — Foundation Sprint 01

Independent multi-tenant merchant platform foundation. Scope: identity, organizations, branches, RBAC, terminals, audit, web shell, POS/owner Flutter shells. Orders, payments, catalog, inventory, analytics and AI are intentionally deferred.

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

Visit `http://localhost:3000/login`. API docs are at `http://localhost:8000/docs`. The web BFF defaults to `http://localhost:8000`; configure server-only `BACKEND_URL` for another backend. Web cookies are HttpOnly, SameSite=Strict and Secure in production; always serve production over HTTPS. The owner app accepts `--dart-define=API_URL=https://your-api-host`. The POS and owner Flutter projects are package skeletons: run `flutter create . --platforms=android,ios` in each project to generate platform runners, then `flutter pub get` and `flutter run`. The web login and navigation have Arabic/English direction and labels; operational page copy is currently Arabic-first and needs completion before a full English launch.

Run `make migrate`, `make test`, `make lint` as needed. Integration tests require a migrated disposable PostgreSQL database at `smart_merchant_test` and Redis DB 1. CI provisions both. Set branch protection in GitHub repository settings to require PR, review and all checks in `.github/workflows/ci.yml` before merge. GitHub returned HTTP 403 for repository rulesets on this private repository (requires an account upgrade or a public repository), so the repository owner must enable these protections when available. CI checks still run on pull requests.

## Current acceptance status

The Foundation CI workflow passes backend lint/type checks, PostgreSQL and Redis integration tests, Alembic upgrade/check/downgrade/upgrade, Python dependency audit, web lint/type checks/tests/production build and `npm audit`, Flutter analyze/tests for both apps, and Gitleaks secret scanning. The tenant-isolation, RBAC, authentication and migration gates pass in CI. Docker Compose readiness in a developer environment and Android/iOS platform runners have not been independently verified; Flutter package skeletons require the `flutter create` step above. Sprint 01 remains in a draft PR pending review and these remaining acceptance steps. Do **not** start catalog work until the foundation is fully accepted. See [testing strategy](docs/testing/testing-strategy.md).
