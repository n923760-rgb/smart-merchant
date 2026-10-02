# SM-WEB-008 — Management create form lifetime

Date: 2026-10-03 (Asia/Riyadh). Repository: n923760-rgb/smart-merchant.
Official main verified: 80de2647186d999e98e2ff77eff1e1dd1c7810d0.
Task branch: fix/management-form-success.
Explicit dependency: open PR #11 / test/real-backend-foundation,
head e7a29f809df1e73857e199821c38f389d1b16100. This stacked PR targets that
exact tested branch, not an obsolete source; main/dependency drift is a stop.
One source writer; same-session review is not independent approval.

## Diagnosis and correction

FACT: Both users/devices creation handlers read React's event.currentTarget
after awaiting the API command. React's dispatch-bound currentTarget is then
null, causing reset to throw after the successful backend mutation. The catch
shows a false failure, while query invalidation can still reveal the new record.
The stale alert also remains across later attempts.

Capture the HTMLFormElement synchronously, serialize and reset through that
reference, and clear the old alert at the beginning of a new explicit attempt.
Reset still happens only after successful creation; failures keep entered data.
No backend, permissions, schema, transport retry or financial behavior changes.

Extend #11's real-backend fixture to submit actual user/device forms. Assert
successful persisted creation plus reset/no alert; then a real user duplicate
409 or device branch-validation 422 with retained inputs; then new successful
creation with stale alert cleared. The fixture inserts a deliberately invalid
branch option into the device select to reach server validation through the
actual form, not an intercepted response.
These checks fail the original implementation because its form never resets.
No synthetic route interception, arbitrary race sleep or credential dump.

## Qualification

Dependency Foundation [37013713281](https://github.com/n923760-rgb/smart-merchant/actions/runs/37013713281)
passed all nine jobs, including real PostgreSQL/Redis/Chromium, and dependency
Governance [37013712899](https://github.com/n923760-rgb/smart-merchant/actions/runs/37013712899)
passed. Foundation checked a65dd4158f1c2de03c53bf50fc9b25e01d2227cc with
the dependency tree 17ddcdfd3bff9a708240cce4d711e6cd61e0a39f.
Those runs prove only #11, not this changed candidate.

Candidate checks and exact head/tree/run IDs will be recorded in this PR's
result packet after execution. Real backend runtime remains NOT RUN locally
because Docker/PostgreSQL/Redis are unavailable; use the bounded disposable CI
executor. No merge/release is included in this task's authority.
Local PASS: web lint, strict TypeScript, all 50 Vitest tests, production build,
Node fixture syntax, task/governance validators and Git whitespace review.

## Limits and next action

This is a two-form async-lifetime correction, not a redesign or complete UI
acceptance. Duplicate prevention, all role editing paths, other browsers,
cross-tab rendered cache invalidation, physical/mobile devices and production
remain outside this round. Tenant/RBAC/audit/session regressions remain required.
Separate SOURCE FINDING: terminal creation flushes before its IntegrityError
mapping, so a duplicate device identifier can escape as an uncontrolled error.
This round does not assert a proper duplicate-terminal conflict contract; qualify
and correct tenant unique-conflict mapping separately before broad mutation UI
acceptance.
Tokens/passwords are masked in CI diagnostics; no screenshots/service logs are
uploaded. Each request/navigation/job stays bounded; unknown outcomes are not
automatically retried.

After exact-source checks and review, owner integration must preserve the tested
tree: #11 first, then this dependent PR retargeted/requalified against main.
