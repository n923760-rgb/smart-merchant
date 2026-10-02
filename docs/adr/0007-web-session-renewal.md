# ADR 0007 — Browser-coordinated web session renewal

Status: accepted for SM-AUTH-003 under the owner's continued-development authority.
Repository: n923760-rgb/smart-merchant. Diagnosis base: d273ea5ca0e7a841b3db423840d6cecb95011d8a.

## Problem

Each ordinary BFF proxy request used its own refresh-cookie snapshot after a 401.
PostgreSQL correctly accepts one rotation and rejects reuse. Two tabs or concurrent queries could therefore receive one success and one 401, with the latter redirecting a healthy session to login.
A process-local promise cache cannot coordinate BFF replicas or browser tabs. A replay grace period would weaken the existing strict one-use backend invariant.

## Decision

Ordinary proxy requests never rotate credentials or write cookies. A dedicated POST /api/session/refresh rotates them and returns only authenticated:true.
The browser serializes refresh, login, logout and organization selection with one same-origin Web Lock.
After acquiring the lock, a rejected request probes auth/me using the current HttpOnly access cookie. A previous renewal needs no additional rotation.
Retry the original authorized-context request once, only after an explicit 401 and with a replayable string/no body. Never retry timeout, transport failure or unknown command/payment outcomes.

Login creates a non-secret random sm_context cookie, and changing organizations replaces it. Repeated selection of the same organization is idempotent.
It is intentionally readable by browser JavaScript so requests can bind themselves to a context before waiting.
It is not a credential or permission; sm_access, sm_refresh and sm_org remain HttpOnly, and backend authentication/tenant RBAC remain authoritative.
The proxy, refresh and organization endpoints reject missing/stale binding before backend actions. Logout rejects a stale binding but retains refresh-only logout for legacy sessions without sm_context.
Each page remembers the context it first observed. Only its own successful login/logout/organization action adopts a new context. A dormant tab cannot silently adopt another tab's new account when issuing a fresh command.
The API helper checks that the context is unchanged before dispatch, before retry and before exposing response data/errors.
No token, password or per-session credential cache is added to JavaScript, Redis or the BFF process.

## Consequences and limits

HTTPS or trustworthy localhost and a browser supporting Web Locks are required for session-changing actions and automatic renewal.
Unsupported clients get an actionable error rather than an unsafe coordination fallback.
Deployment requires existing web sessions without sm_context to sign in once. No backend token lifetime, schema or revocation-family change is made.
The lock covers cooperating clients in the same browser storage partition/origin. Copied credentials in another browser, direct endpoint misuse, abrupt browser/network failure during rotation and lost Set-Cookie delivery are not qualified as recoverable.
Proxy failure does not clear cookies. Only a confirmed 401 redirects to login; network, renewal-service and context-change errors offer reload.
Cross-tab cached UI invalidation before the next request is a separate qualification gap. A dormant tab's next command is rejected before dispatch until reload; already-rendered old data is not automatically erased in this round.
Generic proxy forwarding of auth/login, auth/refresh and auth/logout is disallowed so application callers use the session protocol.
BFF timeout/body limits and owner-app foreground refresh remain separate tasks.

## Validation

Vitest covers concurrent and delayed 401s, stale account/organization actions, rejected refresh, unknown command outcomes, non-replayable bodies, missing Web Locks and HttpOnly credentials.
Chromium exercises two real Next.js BFF tabs against a disposable strict one-use upstream, including logout waiting for refresh cookies and a stale command and a dormant Alpha tab's form submission after Beta login.
Existing PostgreSQL integration continues to assert that reusing a rotated refresh returns 401.
Exact candidate CI and final review are recorded in the PR result packet. Physical devices, real backend browser E2E, Safari/Firefox and multiple live BFF instances remain NOT RUN.
