# ADR 0020 — Dated operator-declared organization tax profile

SM-ACC-005C2, 2026-11-02. Base main 1ac1277eeaa0ebe3ffe54a45ffb17ea2d7591352.

## Contract

Owner-global `billing.tax.manage` may append a declaration using a permanent request
UUID, effective date, UNKNOWN/REGISTERED/NOT_REGISTERED status, and a VAT number only
for REGISTERED. Global OWNER/ACCOUNTANT receive `billing.tax.read`; branch grants
do not authorize company-wide tax data. Existing tenants are migrated with matching
grants; bootstrap gives new tenants the same defaults.

POST `/api/v1/billing/tax-profiles` serializes on the organization row and commits
snapshot plus append-only audit atomically. Same request/content replays the original
even after its effective date has passed; changed content conflicts. Effective dates
must be today or later in the organization's configured timezone and strictly later
than every prior scheduled declaration. PostgreSQL guards these rules and rejects
UPDATE/DELETE. The unique organization/date key prevents ambiguous selection.

GET `/api/v1/billing/tax-profile?effective_on=YYYY-MM-DD` returns the latest declaration
effective on/before the requested date. Before the first declaration it returns a
null profile: absence is unknown, never an implicit nonregistration or zero-tax rule.
Future scheduled declarations do not replace an earlier date's selection. Requests
are scoped to the authenticated tenant; audit metadata contains only UUID/date,
never the VAT number. Read does not imply write permission.

## Explicit limitations

This is an initial, forward-only declaration schedule, not a complete correction
workflow. Only one declaration per effective day; inserting earlier than an already
scheduled future declaration is rejected. Same-day correction, cancelling a future
declaration, historical onboarding/import, retention and verification lifecycle need
separate reviewed commands. No update/delete workaround is provided.

Verification is always OPERATOR_DECLARED and can_issue_tax_invoice is always false.
Formatting a 15-digit number beginning/ending in 3 is not registration verification.
The [official lookup](https://www.zatca.gov.sa/en/eServices/Pages/eServices-007.aspx)
is a separate service; no lookup is performed here. Format basis: official XML
standard BR-KSA-40, linked from the
[specification page](https://zatca.gov.sa/ar/E-Invoicing/SystemsDevelopers/Pages/E-Invoice-specifications.aspx).
Sources checked 2026-11-02; no taxpayer status inferred.

There is no service-category assignment, calculator activation, tax assessment,
document linkage, AR posting, invoice issuance, fiscal XML or provider integration.
Existing draft/obligation previews retain their NOT_EVALUATED/null-due blockers.
Preserving dated configuration is groundwork; future approved documents must pin
the exact immutable profile ID/snapshot instead of re-reading today's configuration.

## Validation and next work

Require API/PostgreSQL tests for as-of dates, no default status, strict fields,
owner/accountant/branch roles, tenant isolation, replay/mismatch, chronological
barriers, direct SQL mutation/backdating, concurrent retries and audit rollback.
Migration upgrade/check/downgrade/upgrade and all exact-source CI must pass before
owner-authorized merge. No production migration/deployment or fiscal acceptance.
Next: category evidence/effective dates and profile-pinned document assessment,
then explicit financial approval and atomic source/AR/journal reconciliation.
