# SM-E2E-007 — Real-backend browser foundation

Date: 2026-10-02. Repository: n923760-rgb/smart-merchant.
Base main: 80de2647186d999e98e2ff77eff1e1dd1c7810d0.
Branch: test/real-backend-foundation. Actor: current Codex session, one source writer.
This review is by the same session, not independent approval.

## Review and bounded outcome

FACT: #10 is merged. All eight jobs on main Foundation run 37012227678
passed; Governance run 37012227663 passed. No open PR conflicted with this task.
Existing Chromium fixtures intercepted BFF responses or used a synthetic strict
upstream. They did not connect the browser to the actual PostgreSQL-backed API.

Add one separate CI job with a fresh PostgreSQL/Redis service pair and a real
production Next.js BFF/uvicorn backend. The script bootstraps two merchants using
ephemeral credentials, performs rendered login/branch creation/device revocation,
then verifies membership/roles, tenant isolation, audit and session semantics
through browser-origin BFF requests. No application/schema/API behavior changes.

## Assertions and evidence boundaries

- Owner login/me, permissions, rendered branch creation and persisted list.
- Basic invitation and branch-scoped MANAGER/CASHIER grants through BFF APIs.
- Manager's rendered list excludes the other branch; create form and user/role
  navigation are hidden. Direct unauthorized reads/mutations remain denied.
- Cashier's protected route and branch command are denied.
- Foreign owner cannot read/patch Alpha branch/user, revoke its terminal or
  attach a new terminal to its branch. Beta lists and audit contain no Alpha data.
- Terminal creation/rename through BFF and rendered revocation persist.
- Expected branch/invitation/assignment/device audit entity IDs exist.
- Last owner's membership disable is rejected.
- Credentials stay HttpOnly/SameSite Strict; rotation changes the refresh
  capability, reuse fails, logout clears cookies and revokes its successor.

NOT RUN until attributable CI completes: the new real-backend Chromium journey.
Local runtime is unavailable (no Docker/PostgreSQL/Redis executables).
Local PASS: Node script syntax, workflow YAML parsing, task packet validator,
governance adoption validation, Git whitespace check and web lint/TypeScript/
50 Vitest tests/production build. CI is the bounded external executor, not a
permanent lab.
PR/run/head/tree evidence will be recorded in the PR after execution, not invented
or embedded as a self-referential source SHA in this commit.

## Review and risks

The test requires loopback HTTP and explicit disposable opt-in. Generated
passwords/tokens remain in memory; bootstrap/JWT configuration is masked in CI.
No screenshots, response dumps, service logs or credential-bearing artifacts are
uploaded. Service processes are cleaned up by a trap; runner containers are
disposable. Requests/readiness/navigation and the entire CI job have deadlines.
Unknown command outcomes are not retried. Production records are never used.

This is not full management-form acceptance, automatic-expiry/browser concurrency
acceptance, physical/mobile acceptance, multi-instance deployment or a production
release. Existing unit/synthetic/browser/backend gates remain required.

Separate SOURCE FINDING for the next bounded task: users/devices creation handlers
read `e.currentTarget.reset()` after awaiting the mutation. React clears the event's
currentTarget outside synchronous dispatch, so committed success can be followed
by a caught UI error. This round intentionally does not change those forms or
claim their rendered create flow passed. Capture the form before await and add
rendered real-backend regressions in a separate correction round.

Next: review exact CI/diff; then repair and qualify these form-success paths.
Physical targets, enforced branch protection, multi-tab cache invalidation and
complete POS acceptance remain open. No merge/release is authorized by this packet.
