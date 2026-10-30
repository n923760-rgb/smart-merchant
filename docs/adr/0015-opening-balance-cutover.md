# ADR 0015 — One-time initial opening-balance journal (SM-ACC-004C1)

**Status:** Candidate for owner-approved accounting-first Hybrid Commerce V6, 2026-10-29. Narrow initial cutover only, not annual closing/rollover. ADR 0010/0012/0013/0014 remain binding.

## Financial decision
A merchant may post **one organization-level opening balance** with a selected effective booking date. The balance is a normal exact-decimal, balanced, immutable posted journal, not a mutable cached number. Debit total must equal credit total; the system does not invent an equity balancing item. Users choose postable leaf accounts, consistent with their accounting policy. No terminal, stock, shift or sales channel is needed.

- Only an OWNER organization-level grant `accounting.opening.manage` may initialize the one-time opening; OWNER and ACCOUNTANT may read `accounting.opening.read`. The caller must also have `accounting.journals.post`. Branch grants do not suffice.
- The opening journal is a branchless entry using the existing ledger posting rules, source auditing and permanent request identity, with a separate `OPENING_BALANCE` digest domain.
- A new immutable `opening_balance_batches` row uniquely links organization + opening date + posted journal ID. It is inserted in the same SQL transaction as the journal and audit. Existence of a batch prevents all later attempts at a second one.
- To avoid importing initial balances **over prior business activity**, creation fails if any posted journal for that organization is dated **on or before** the proposed cutover date. Earlier posted journals with dates later than the proposed cutover are allowed.
- Once an opening exists, *no subsequent ordinary or reversal journal* may be posted with booking_date on/before its date; PostgreSQL enforces this even for direct SQL. An opening journal itself cannot be reversed through ordinary reversal; subsequent corrections need an explicitly dated, approved adjustment journal.
- Current optional accounting periods apply: an opening cannot be posted in a closed period. Existing (same request ID + same payload) opening submission returns the previously committed journal/batch. Same request ID with a changed payload or reused ordinary journal command conflicts. Concurrent initializations serialize on the organization row plus a unique organization key.
- The API returns the opening batch and its exact journal; journal list and existing journal APIs remain usable. No allowance for backdating after opening is silently introduced.
- SQL triggers guard batch structural immutability, linked posted journal properties, existing earlier journal exclusion and dated-posting barriers. This is a DB integrity guard, not a substitute for API RBAC or audited operator authorization.

## Deliberate non-goals
No fiscal-year rollover, comparative-period carry-forward, automatic retained earnings balancing, editable opening numbers, chart import, ZATCA qualification, or re-opening of a closed period. Organizations that already have prior posted journals and need historical conversion require a **separate reconciled migration/cutover policy**; do not overwrite their ledger.

## Acceptance
Exactly one balanced opening per organization; tenant and owner grant protection; no duplicate effect on retries (including cross-origin generic journal key collisions); future-dated transactions remain unaffected; direct SQL insert/update/delete and pre-opening backdating are refused; closed period barrier is respected; concurrent attempts are safe; migrations upgrade/check/downgrade/upgrade in disposable PostgreSQL; all exact-head CI succeeds. Production data migration, partner/provider approvals and merchant adoption remain NOT RUN.
