# SM-ACC-005B1A — Customer identity prerequisite

Resumed 2026-11-01 with explicit owner upload/PR authority. [PR #36](https://github.com/n923760-rgb/smart-merchant/pull/36) is open. Remote implementation source `f9d08d3a862d1e26674e338731d56e6577290944` has exactly the reviewed local tree `67ff55315a91c0c44bfe89b26e6104afe40e46be`. Backend qualification is PASS: **119 tests**, including all 26 new customer cases, Alembic upgrade/check/downgrade/upgrade and dependency audit. [Backend evidence](https://github.com/n923760-rgb/smart-merchant/actions/runs/41288866090/job/124795724833). Governance, secret scan and Compose smoke also passed. Remaining browser/mobile checks are in progress at this checkpoint. Final current-head qualification is recorded on the PR; this documentation-only successor must not inherit an old exact-head claim.

The initial upload block in the historical section below was resolved by the owner's explicit authorization. Git CLI subsequently lacked credentials, so the connected GitHub API uploaded the equivalent reviewed tree.

Repository: `n923760-rgb/smart-merchant`. Actor: Codex, single source writer and
separate same-session review phase, not independent review.
Verified base: `b866fee7edc42e9add3bb4733200ad25642cb281` on 2026-10-31.
No open PR conflict at task start. See the exact [task packet](../EVIDENCE/SM-ACC-005B1A-task.json)
and [ADR 0017](../../docs/adr/0017-customer-identity.md).

## Delivered candidate

- Canonical organization customer UUID and immutable minimal contact snapshot.
- `POST/GET /api/v1/customers`, `GET /api/v1/customers/{customer_id}` and
  `GET /api/v1/customer-requests/{request_id}`.
- Independent organization-global customer read/create permissions for existing
  and new OWNER/ACCOUNTANT roles; branch grants do not authorize these endpoints.
- Durable replay hash, organization serialization, bounded pagination, immutable
  SQL guard and PII-minimal atomic audit.
- No name/email deduplication; explicit `OPERATOR_CREATED` classification.
- PostgreSQL integration regressions covering tenant/RBAC/replay/concurrency,
  direct SQL mutation/duplicates, input restrictions and transaction rollback.

## Historical local validation (2026-10-31)

Current session has Git, Python 3.12 and an isolated checkout/venv. Historical
no-shell environment records describe earlier sessions. Local PostgreSQL/Redis,
Docker and Flutter are unavailable. A package-manager attempt to install disposable
database services failed due to the container's setuid/setgroups restrictions;
no local integration pass is claimed. Use the existing GitHub Actions disposable
PostgreSQL/Redis jobs; do not substitute SQLite or mocks.

Implementation source: `553f32fae53d0ce4dfd31dd219cfbacd4bdace5d`.
Local results on that source:

| Check | Result |
| --- | --- |
| Ruff app/tests | PASS |
| Mypy app (38 modules) | PASS |
| Existing database-free units | PASS, 15 tests |
| New customer tests | 26 collected; execution NOT RUN without PostgreSQL/Redis |
| Governance adoption/negative fixtures and task validation | PASS |
| Full diff and whitespace review | PASS, same-session review |
| PostgreSQL migrations and integration | NOT RUN locally |
| Foundation / Accounting Web / Governance CI | NOT RUN |
| Branch push / PR creation | BLOCKED |

Automatic approval review rejected `git push -u origin
feat/customer-identity-sm-acc-005b1a`: it considered the remote unverified and
the user's authority insufficiently explicit for external disclosure/mutation.
No alternate push/API workaround was used and no PR or remote CI was created.
The code is committed locally and reviewable. Request explicit owner permission
to upload this branch and open its PR before resuming remote operations.
Existing historical CI is not evidence for this candidate.

## Review and remaining scope

This is the customer-identity slice of issue #35, not completion of B1 or invoice
issuance. No ledger, draft-conversion, balance, receipts, UI or provider code is
changed. Customer contact editing/correction and retention/erasure policy are
deliberately unresolved; immutable snapshots are not production privacy acceptance.
Next: qualify the source-document/customer/account/tax contract before atomic AR
posting. Merchant pilot, production migration, fiscal/provider and physical-device
acceptance are NOT RUN.
