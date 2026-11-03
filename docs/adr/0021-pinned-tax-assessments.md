# ADR 0021 — Immutable profile-pinned internal service-tax assessments

SM-ACC-005C3, 2026-11-03. Base d13a5576ef4ed670b262258bef7296bce9a473bc.
This adds a controlled caller of ADR 0019's calculator; its earlier no-caller
checkpoint is historical. No invoice/financial approval activation is implied.

## Decision and eligibility

POST `/api/v1/billing/service-tax-assessments` requires global billing.tax.manage,
billing.tax.read and billing.drafts.read. Existing owner defaults permit creation;
accountants may read with both read grants, branch-only grants cannot access it.
Input is a permanent request UUID, draft UUID, operator-chosen assessment date,
explicit `category=STANDARD_15` applying to every line, and nonempty documented
classification basis. No category inference from names, caller-supplied rates,
totals, profile IDs, organization or approval/issuance flags are accepted.

The source must be a positive sealed SAR draft in a SAR organization. Select the
latest same-tenant tax profile effective on/before the assessment date, requiring
REGISTERED. Missing/UNKNOWN/NOT_REGISTERED declarations conflict; never interpret
them as zero-tax or exemption. The profile remains OPERATOR_DECLARED, not verified.

Use source line net amounts and category-level integer-halal calculator rounding.
Persist immutable source/profile UUIDs, date, classification basis and exact net,
VAT and gross in one transaction with the audit. Source and profile rows are already
immutable, so these references pin their complete original snapshots. PostgreSQL
composite FKs protect tenant scope; an insert trigger locks the organization and
checks source net/currency/sealing and eligible as-of profile. Check constraints
enforce positive net, exact standard VAT and gross=net+VAT; UPDATE/DELETE is forbidden.

## Replay and reassessment

Serialize creation with profile scheduling on the organization row. Permanent
organization/request identity and an operation digest return the original assessment
on same-content replay before resolving current configuration. Changed content conflicts.
New request IDs deliberately create distinct assessment snapshots, allowing explicit
reassessment with new evidence/configuration. They do **not** create separate debts.
Future posting must separately enforce one approved source effect across requests.

A future profile scheduled after an assessment may change which profile would be
chosen for the assessment's future date. It must not rewrite/recalculate the stored
snapshot. A new assessment chooses the then-applicable profile; old reads/replays
retain the original profile. Future approval must recheck applicable configuration
and assessment validity inside its transaction; possession of an assessment UUID
does not authorize or reserve financial posting.

GET `/api/v1/billing/service-tax-assessments/{id}` requires both global read grants
and scopes to the authenticated organization. Audit includes only request/source/
profile IDs; no classification text, customer data or VAT number.

## Classification and financial boundary

Outputs always report OPERATOR_ASSESSED, NOT_APPROVED, can_post=false,
can_issue_tax_invoice=false and amount_due=null. Gross is an internal calculation,
not a legal debt or issued invoice. The source draft remains NOT_EVALUATED/DRAFT.
The assessment date is supplied by the operator, not certified as a legal tax point.
No customer association, journal, AR, receipt, invoice number, XML, SDK or provider
submission is created. Existing obligation-preview behavior is unchanged.

The official [VAT FAQ](https://zatca.gov.sa/en/HelpCenter/FAQs/Pages/FAQArchiveEservices.aspx?page=Tax-FAQs-9)
was checked on 2026-11-03: standard 15% does not imply that every supply has that
treatment. Zero, exempt, outside-scope, mixed categories, discounts/charges, tax-inclusive
pricing and tax-point rules are outside this first single-category implementation.
Operator evidence is not a legal classification opinion or official verification.

## Qualification and next work

Require actual PostgreSQL API/SQL tests for exact rounding, profile pinning after
scheduling changes, unknown/unregistered denials, replay/conflict, tenant/RBAC,
strict fields, overflow, immutable consistent rows, concurrency and audit rollback.
Require migration upgrade/check/downgrade/upgrade and all exact-source CI. Review
is same-session, not independent; owner authorized merge after qualification.
Next: qualified approval with source/customer/account mapping, period and profile
rechecks, durable unique charge effect and atomic AR/journal/reconciliation safeguards.
Production/fiscal/provider/merchant acceptance and UI remain NOT RUN.
