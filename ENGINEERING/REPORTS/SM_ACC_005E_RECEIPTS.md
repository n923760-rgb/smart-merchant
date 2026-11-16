# SM-ACC-005E — Internal service receipts candidate report

- Base: `f7fea13626c8cf8c3f37ebf72940abdf989aacd9`
- Issue: https://github.com/n923760-rgb/smart-merchant/issues/42
- Contract: [ADR 0023](../../docs/adr/0023-internal-service-receipts.md).
- Status: CANDIDATE — source code/CI review not yet independently qualified.
- Confirmed predecessor: #41 merged. Its 276 backend tests and CI outcomes are **historical evidence for #41**, not proof that this task passes.
- Required checks: PostgreSQL ledger/subledger transaction, concurrent overpay, replay, audit rollback, SQL immutability/reconciliation, tenant/roles, migration roundtrip, lint/typecheck, browser/web, mobile builds, dependency/secret scans, complete diff review.
- Merchant production, financial regulation, payment-provider settlement, ZATCA, physical devices and backups: NOT RUN / OUT OF SCOPE.

## First candidate CI feedback — failed source, not accepted
- At PR #43 initial head `574116ca`, Foundation backend Ruff import order/unused imports and PostgreSQL migration composite FK failed; the source was not qualified.
- PostgreSQL needed unique `(service_charges.id, organization_id)` to reference the charge from immutable receipt FK. Candidate fix adds/drops this reversible unique constraint.
- Flutter stable drifted from previously passing **3.47.9** (2026-11-05 main) to **3.50.0** (2026-11-16), adding deprecated Material imports that break analysis. Candidate CI pins 3.47.9 only; a distinct mobile migration will be required.
- Original failure evidence retained in GitHub Actions; **do not count old runs for repaired head**.
