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

Create the first owner and organization using a strong `X-Bootstrap-Key` equal to `BOOTSTRAP_KEY` in `.env`. Never put that key in browser code. The endpoint `POST /api/v1/bootstrap` creates owner, organization, active membership, initial permission catalog and roles in one transaction. For isolated development demo data, export `DEV_SEED_PASSWORD` with a unique 12+ character value and run `make seed`. Demo email addresses are `owner@demo.example`, `manager@demo.example`, `cashier@demo.example`.

```sh
cd apps/web
npm install
npm run dev
```

Visit `http://localhost:3000/login`. API docs are at `http://localhost:8000/docs`. The web BFF defaults to `http://localhost:8000`; configure server-only `BACKEND_URL` for another backend. Web cookies are HttpOnly, SameSite=Strict and Secure in production; always serve production over HTTPS. The owner app accepts `--dart-define=API_URL=https://your-api-host`. The POS and owner Flutter projects are package skeletons: run `flutter create . --platforms=android,ios` in each project to generate platform runners, then `flutter pub get` and `flutter run`. The web login and navigation have Arabic/English direction and labels; operational page copy is currently Arabic-first and needs completion before a full English launch.

Run `make migrate`, `make test`, `make lint` as needed. Integration tests require a migrated disposable PostgreSQL database at `smart_merchant_test` and Redis DB 1. CI provisions both. Set branch protection in GitHub repository settings to require PR, review and all checks in `.github/workflows/ci.yml` before merge. The repository owner must configure this after creating the repository.

## Current acceptance status

Ruff, mypy, four backend unit tests, Python compilation, schema construction, web lint/type checks, web tests, production build and `npm audit` (zero reported vulnerabilities) were checked locally. PostgreSQL/Redis integration tests, Flutter analyze/tests, Docker readiness, Alembic upgrade/downgrade and live CI are pending an environment with the respective runtimes/services. Do **not** treat Sprint 01 as accepted or start catalog work until CI and the five foundation gates pass. See [testing strategy](docs/testing/testing-strategy.md).
