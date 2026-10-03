# SM-ACC-001 — General accounting scope and journal foundation

Repository: n923760-rgb/smart-merchant.
Diagnosis source: main 80de2647186d999e98e2ff77eff1e1dd1c7810d0, tree e8e722a7d8001204df0df88c9b2203b2bb7ffdd4.
Actor: Codex session; same-session review, not independent approval.
Authority: owner 2026-10-03 requests merging prompts/applying changes and then explicitly makes the application general accounting without a required sector. Persistent reviewed-merge authority applies after successful checks.
Task: [general-accounting-task.json](../EVIDENCE/general-accounting-task.json).

## Scope reconciliation

The merged prompt preserves general POS/inventory/accounting/multi-branch/owner/AI vision and multi-device/offline invariants. The latest direction removes a food-truck-first or restaurant-only product scope. Accounting, invoicing, customers and suppliers form the core; POS/stock/recipes become optional activity modules. General accounting does not require terminals or shifts. All 150 existing POS rule bodies were compared to the diagnosis source and remain byte-for-byte unchanged; only their applicability header changes.

Earlier full-accounting expectations (double entry, AR/AP, expenses, purchasing, reports, immutable journals and deterministic costing) remain in the product reference. No source migration to another framework or competing project roadmap is introduced. Fiscal and business estimates are not promoted into production defaults.

## Implemented bounded outcome

- General Account and JournalEntry/JournalLine domain and Alembic 0002_accounting.
- Account creation/list and journal post/list/detail/full-reversal APIs, independent of POS.
- Decimal-string input, exact balance and normalized hash; initial monetary qualification SAR.
- Organization/branch accounting RBAC; OWNER/ACCOUNTANT grants on bootstrap and migrated existing system roles, without granting CASHIER ledger access.
- Durable organization-scoped request identity, hash collision rejection and organization-row serialization across workers for posting/reversal.
- Atomic header/lines/posting/audit and database-enforced balanced committed state.
- PostgreSQL guards for immutable posted headers/lines and rejection of later appended lines.
- Reversal retains original snapshot, actor/reason/date and has one-full-reversal uniqueness; historical inactive accounts can be reversed.
- Updated unified requirements, applicability docs, ADR, README and the existing canonical roadmap.

## Observed capabilities and local validation

Local isolated clone/branch, Git, Python 3.12 and Node are available. A task-specific Python environment installed dependencies. Backend lint/type checks and accounting/foundation pure unit checks PASS; governance packet/adoption validation and whitespace/rule-preservation checks PASS. Exact commands/results are recorded in the PR qualification.

Docker/Flutter are unavailable locally. PostgreSQL/Redis packages could be extracted, but the environment cannot switch to a non-root UID and PostgreSQL refuses root startup; a qualified local integration runner was not established. Do not claim local PostgreSQL/API/migration tests ran. Required runtime proof will use existing GitHub Actions with disposable PostgreSQL/Redis and attributable source.

Source review checks permission boundaries, composite keys, financial atomicity, state/append triggers, normalized replay and reversal concurrency. Review is the same actor. Existing open PR #11 and dependent #12 are not altered or claimed integrated; their browser/runtime and management-form fixes remain separate.

## Required candidate proof

Foundation CI must run PostgreSQL API, concurrency/immutability/audit/branch/tenant regressions, Alembic upgrade/check/downgrade/upgrade, backend dependency/security gates and unaffected web/Flutter/Compose gates. Governance CI must pass for the exact candidate. Candidate/checkout/tree/run details belong to final PR qualification; historical successful CI is not reused.

## Qualification limits

NOT RUN: complete accounting/service invoicing, ledger reports, AR/AP, periods/closing, reconciliation, automatic posting rules, fiscal integration, mobile/web accounting screens, physical devices and merchant pilot. The API is the first ledger foundation, not a complete accounting application. No production release/signing/deployment or production data mutation.

Next bounded work: accounting UI/account hierarchy/period policy, then general customers/suppliers/invoices/receipts/expenses and deterministic posting. Preserve the outstanding foundation browser/device work and old POS acceptance gates for the optional POS module.
