# ADR 0014 — Explicit organization period-closing barrier (SM-ACC-004B1)

**Status:** Candidate policy under owner-approved Hybrid V6, 2026-10-29. Implements a bounded first period control, not a full fiscal-year close engine. Depends on ADR 0010 (ledger), 0012 (replay), and 0013 (account hierarchy).

## Business boundary
An organization can configure nonoverlapping date ranges and explicitly close a range to **block new journal postings and reversals dated inside that closed range**. No period is backfilled or automatically closed. Existing entries remain immutable and visible. Businesses without configured periods retain their current ability to post general ledger transactions; service accounting stays independent of terminals/stock/POS.

No mandatory exhaustive calendar, reopening, tax/fiscal compliance, automation or opening-balance commands are implied. A future `enforce_complete_calendar` policy would require a distinct migration and tested activation flow.

## Decisions

1. `accounting_periods` is organization-scoped and has immutable `start_date`, `end_date` (inclusive), and `organization_id`; status starts `OPEN`. `CLOSED` requires `closed_at` and `closed_by`. A period cannot be deleted, re-opened or have its dates changed in this slice.
2. Owner-only global permission `accounting.periods.manage` creates/closes periods; `accounting.periods.read` belongs to global owner/accountant. Branch-only permission cannot manage the organization calendar. New organizations inherit owner and accountant read, owner manage; existing organizations receive those grants via migration.
3. A database trigger serializes creation/closure against the `organizations` row and rejects overlapping ranges including endpoints. Non-overlapping open periods may exist, but gaps are allowed until an explicit calendar-activation policy.
4. A database trigger on `journal_entries` rejects **INSERT with POSTED status** and transition `DRAFT -> POSTED` when `booking_date` falls into a `CLOSED` period for that organization. It locks the organization row to serialize with closure, so direct SQL or concurrent posting cannot bypass the barrier. All API posts and reversal commands already acquire the same organization lock.
5. API explicitly checks a closed-period conflict to present a normal 409 response. Durable same-request replay returns the originally posted result and does not create a new transaction; replay permission is still checked. An attempted reversal with a closed date is rejected, but a reversal dated in an open/unrestricted date remains allowed under ADR 0010.
6. Closing does not amend past journal records. No period deletion or reopen path; future correction mechanisms require authorized separately audited reopening or adjustment periods with their own acceptance policy.
7. The creation/close endpoints have no direct payment/fiscal interaction. API time is UTC `closed_at`; booking dates are `date` in the organization accounting calendar, independent of frontend-local time or shifts.

## Race/authority guarantee
Both domain posting and closing lock the organization row `FOR UPDATE`. SQL trigger locks the same row `FOR UPDATE` for direct posting and period writes. If the posting commits first, close will complete afterwards (existing posted journal preserved); if close commits first, later posting for that date fails. No Redis lock defines this financial invariant.

## Restrictions and follow-up
- Do not automatically create 12 months or force a missing period to block pre-existing merchants; calendar enforcement is future independent approval.
- No opening balances in this slice. Opening balances should post as a traceable balanced journal in a separately designed opening process.
- No mutation of committed ledger entries; do not overwrite past data on a downgrade. Production migration is not authorized or tested by CI.

## Qualification
Require tenant/global RBAC checks, nonoverlap, direct SQL overlaps, closed-period journal/API/SQL denial, replay, reversal dates, race tests on disposable PostgreSQL, migration upgrade/check/downgrade/upgrade, full Foundation/Governance/Accounting Web CI. Distinguish CI success from merchant, tax, and production readiness.
