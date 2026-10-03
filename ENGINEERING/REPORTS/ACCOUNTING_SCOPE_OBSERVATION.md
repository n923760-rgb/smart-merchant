# SM-E2E-010 — Accounting branch request observation

Repository: n923760-rgb/smart-merchant. Actor: Codex, same-session review.
Base main: f7e31d719ad0527d2a305270e944a251738ba976.
Owner expressly authorizes continued fixes and reviewed merges.

## Observed failure and cause

PR 14 passed Accounting Web 37127922401 before its reviewed merge, with the
exact same application tree 376ac0a14172b62039a7bbb2840fe4e8f7f8f90d. Main
post-merge run 37128381976 then failed at fixture line 396, scopedReads.length
>= 4. Documentation candidate run 37128773307 also failed at the same assertion.
Successful earlier CI is retained as source-specific history, not used to ignore
the new failure. Documentation PR 16 must remain unmerged until this qualifies.

signIn waits for navigation and the accounting link. The accounting-only branch
user automatically lands on the page, whose effects may dispatch initial list
reads before signIn returns. Capturing scopeStart afterward can omit those reads;
clicking the current page does not guarantee new requests when they are cached.
The count therefore depends on timing rather than the authorization invariant.

## Correction

Capture scopeStart before restricted-user signIn. Wait for account and journal
content at both selected branches. Replace the aggregate request count with
explicit accounts/journals coverage for each of the two branches. Retain the
check on every observed list request: only authorized branch IDs, no unscoped or
foreign request. The real authenticated forged B3 request must still return 403;
scope detail reset, hidden secret rows, cashier and foreign-account checks remain.

No sleep, synthetic successful response, production change, security relaxation,
auth-cookie change or financial retry. Fixture data remains disposable/loopback.
Node syntax, formatting, task/adoption and complete bounded diff are checked
locally. New exact-source Accounting Web/Foundation/Governance qualification and
merge-tree evidence belongs to this PR. Main/doc failures remain attributable.
