# SM-ACC-005A1 — internal service draft candidate result

**Project:** n923760-rgb/smart-merchant  
**Date:** 2026-10-30  
**Base accepted main:** `160dfb9fc1624a53d7e77f58bbc05715f399d45e` (opening balance #30).  
**Origin:** issue #31 and approved accounting-first Hybrid V6.  
**Executor:** assistant through GitHub repository APIs; no customer, provider, VPS or production access used.

## Bounded content

- New `billing` module, draft-only API: `POST /api/v1/billing/service-drafts`, `GET /api/v1/billing/service-drafts`, `GET /api/v1/billing/service-drafts/{id}`.
- Organization-scoped customer-name/email snapshot and service line quantities/unit prices transmitted as decimal strings. Line totals use explicit half-up to 2 decimal SAR; pre-tax document total sums exact lines.
- Caller must have organization-global `billing.drafts.create` or `billing.drafts.read`. New and existing OWNER and ACCOUNTANT roles have the scoped permissions. No user with only branch grants can access company-wide customer information.
- Permanently unique organization/request identity and deterministic payload digest. Same request with same normalized payload returns the stored document; changed payload conflicts.
- PostgreSQL deferrable completeness check and structural write-protection: header starts BUILDING, inserts its lines, seals to DRAFT in the same transaction; no direct SQL update/delete or later line additions.
- No `journal_entries`, AR, payment, tax rate, legal invoice number, ZATCA proof, QR or POS dependency. `tax_status=NOT_EVALUATED`, `document_kind=INTERNAL_SERVICE_DRAFT`; never displayed as a tax invoice.
- New disposable PostgreSQL tests cover normalization, rounding, replay, invalid fields/line counts, cross-tenant permission denial, direct SQL tamper/incomplete documents, no ledger effect.
- Migration and metadata imported in `backend/migrations/env.py`; existing accounting domain untouched.

## Required acceptance

- Root `AGENTS.md`, one roadmap and governance packet are respected.
- Exact-head Foundation CI must pass Python lint/typecheck/migration check/upgrade/downgrade and disposable PostgreSQL tests, frontend regression, browser integration, mobile build and security.
- Exact-head Accounting Web and Governance CI must pass.
- Independent review/cross-domain audit: NOT RUN until code review is completed.
- Merchant usability test, live tax compliance, payment, provider, physical POS, production migrations: NOT RUN.

**State:** CANDIDATE, not merged, not released. `SM-ACC-005A2` should build an accessible draft editing/preparation UI over this qualified API; final legally issued tax invoice/AR/settlement remain separately gated.
