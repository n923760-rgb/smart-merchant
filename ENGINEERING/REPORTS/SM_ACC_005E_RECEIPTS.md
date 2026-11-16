# SM-ACC-005E — Internal service receipts candidate report

- Base: `f7fea13626c8cf8c3f37ebf72940abdf989aacd9`
- Issue: https://github.com/n923760-rgb/smart-merchant/issues/42
- Contract: [ADR 0023](../../docs/adr/0023-internal-service-receipts.md).
- Status: CANDIDATE — source code/CI review not yet independently qualified.
- Confirmed predecessor: #41 merged. Its 276 backend tests and CI outcomes are **historical evidence for #41**, not proof that this task passes.
- Required checks: PostgreSQL ledger/subledger transaction, concurrent overpay, replay, audit rollback, SQL immutability/reconciliation, tenant/roles, migration roundtrip, lint/typecheck, browser/web, mobile builds, dependency/secret scans, complete diff review.
- Merchant production, financial regulation, payment-provider settlement, ZATCA, physical devices and backups: NOT RUN / OUT OF SCOPE.
