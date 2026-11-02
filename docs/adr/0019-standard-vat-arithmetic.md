# ADR 0019 — Bounded standard-rate VAT arithmetic

SM-ACC-005C1, 2026-11-02. Base `25abfe00bbae4c89ce43b0b6a33fc92600b32a2a`.
One pure arithmetic dependency of issue #35. No runtime activation or tax-policy decision.

## Official source verification

Reviewed the official [specification landing page](https://zatca.gov.sa/ar/E-Invoicing/SystemsDevelopers/Pages/E-Invoice-specifications.aspx)
and its linked [XML standard v1.2, dated 2023-05-19](https://zatca.gov.sa/ar/E-Invoicing/SystemsDevelopers/Documents/20230519_ZATCA_Electronic_Invoice_XML_Implementation_Standard_%20vF.pdf),
section 10 and rules BR-CO-17, BR-S-08/09. Category VAT is calculated from the
category taxable amount and rounded to two decimals; it is not the sum of rounded
line VAT. Official [VAT FAQ](https://zatca.gov.sa/en/HelpCenter/FAQs/Pages/FAQArchiveEservices.aspx?page=Tax-FAQs-9)
states the standard rate is 15%, with other treatments for some supplies.
This verifies arithmetic inputs, not a tenant's registration or a service category.

## Decision

`calculate_standard_vat` accepts 1–100 already-rounded tax-exclusive SAR line net
amounts as ASCII decimal strings (up to two fractional places), explicitly within
one standard 15% category. Add line amounts in integer halala, compute category VAT
once with nonnegative HALF_UP, then add net and VAT to obtain gross. Return an
immutable result of exact two-place strings. No floats or ambient Decimal context.
Reject ambiguous strings, numeric inputs, negatives, unbounded collections and
overflow of any final NUMERIC(18,2) amount, including gross even when net fits.

Example: two 0.10 lines have category VAT 0.03, not 0.04. A 34.99 net category has
VAT 5.25 and gross 40.24. Gross is an arithmetic total, not a final amount due.

## Boundaries

No caller in the API, preview or posting service activates this function yet.
The existing preview remains NOT_EVALUATED with null tax/due and can_post=false.
There is no tax-status claim, actor/customer identification, discount/charge,
prepayment, credit-note, tax-inclusive price, zero/exempt/mixed category or rate
selection support. The caller must independently qualify and group the lines;
this primitive cannot infer their eligibility. The strict line limit and accepted
money strings are project boundaries, not a statement of all legal invoice formats.

Next: explicit organization tax configuration, category evidence and effective dates,
document assessment, account approval and atomic source/AR/journal linkage. Then
fiscal XML/SDK/sandbox qualification and reconciled corrections/receipts. No fiscal
or merchant acceptance follows from passing these arithmetic tests.

## Validation and integration

Hand-calculated category/rounding fixtures, below/at half-halal boundaries, large
values beyond floating-point precision, invalid representations, collection bounds,
net/gross overflow and immunity to Decimal context changes. Require exact-source
Foundation, Accounting Web and Governance CI plus complete same-session review.
Owner explicitly authorized merge when qualified on 2026-11-02. No deployment.
