# SM-ACC-005A2 — mobile-first service draft preparation (candidate)

Date: 2026-10-30. Repository: n923760-rgb/smart-merchant. Base main `b46d4e9940bef3de37348ef3e055ecc858e80ddd` (qualified internal draft API PR #32).

## Bounded change
- User-visible `/service-drafts` inside existing authenticated web shell, with separate read/create grants and owner dashboard navigation.
- Arabic-first responsive UI: customer name, optional email, service lines, quantity/price, add/remove, exact **before-tax** preview and saved immutable draft list.
- Permanent request ID and payload retained after unknown network outcome; same command retried rather than generating a second request.
- Explicitly marked NOT_EVALUATED / INTERNAL_SERVICE_DRAFT; no VAT or tax issuance, official invoice number, payment, receivable, journal or POS.
- Exact BigInt-based preview independent of JS binary floating rounding; amount verification from server persisted draft.
- Unit tests for arithmetic, validation and global permission-scoped menu.
- Real-backend Chromium E2E on disposable PostgreSQL verifies rendered form, committed draft, exact 34.99 SAR, no journal side effects, cashier denial and cross-organization isolation.

## Acceptance
All exact-head Foundation CI (including real browser and Android/iOS builds), Accounting Web CI and Governance CI must PASS. Tenant, financial and session boundaries must not regress. This source is a candidate until reviewed and merged; merchant pilot, customer-data/real fiscal and production deployment are NOT RUN.

## Future
Clean route integration into accounting workspace and separately qualified legal invoice issuance (ZATCA requirements apply only to the eventually supported issuing flow), followed by AR, partial/full collection and reconciled reports.
