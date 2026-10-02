# ADR 0008 — Bounded web BFF transport

Status: accepted for SM-WEB-004 under the owner's continued-development authority.
Diagnosis base: main 9ed105206becda3c88a369f8feff46aa66cda50c.

## Problem

BFF routes buffered unbounded request/response bodies and had no upstream deadline.
A server or partial body could stall the shared browser session lock; transport failure surfaced uncontrolled exceptions.
A timeout cannot prove whether an authoritative mutation, rotation or revocation committed.

## Decision

One common BFF scope covers request reading, upstream headers and complete upstream response reading with a single deadline.
Stream UTF-8 bodies incrementally and count actual bytes, including chunked bodies and understated/missing Content-Length.
Reject oversized input before forwarding (413), malformed JSON/UTF-8 input (400), oversized/malformed/unavailable upstream (502), invalid server limit configuration (503), and deadline expiry (504).
Use capped growing byte buffers, rather than retaining per-chunk metadata; check elapsed time during buffered reads as well as using the cancellation timer.
Cancel outstanding reads, abort the fetch, clear timers/listeners and return controlled no-store errors without raw exceptions/credentials.
Do not follow upstream redirects or automatically retry any transport failure.

Server-only settings:
- BFF_TIMEOUT_MS: default 10000; inclusive range 100–60000.
- BFF_REQUEST_MAX_BYTES: default 65536; inclusive range 1024–1048576.
- BFF_RESPONSE_MAX_BYTES: default 1048576; inclusive range 1024–8388608.
Invalid values fail closed. apps/web/.env.example documents deployment inputs.
These are engineering transport defaults, not fiscal/payment or merchant product policies. File uploads/bulk offline import need a separate contract.

All web session routes and the generic JSON/text proxy use the scope. Validate a complete successful login/refresh token pair before writing HttpOnly cookies.
Preserve context/RBAC/one-use refresh rules. Timeout/failure must not replace or erase login/refresh cookies.
Logout attempts bounded refresh-capability revocation, then clears local cookies even if that result is unavailable.
Local cleanup does not prove authoritative revocation.

Browser session requests separately bound headers and full response delivery at 65000ms (longer than the maximum server deadline) and 8388608 bytes.
The browser aborts/cancels an expired read and releases its Web Lock, without reissuing the action.
Caller cancellation is respected. The deadline starts inside a granted lock, not while waiting for another cooperating tab.
Only the existing explicit authorization-401 flow may renew/retry once; never retry 502/503/504, network errors or unknown results.

## Boundaries and qualification

Aborting transport cannot roll back a command already accepted by the backend. Operators must reconcile unknown financial/payment results using explicit identity/idempotency once those domains are implemented.
Lost rotation/cookie delivery remains an unknown outcome; no replay grace, refresh-family redesign or financial behavior is added.
Reverse-proxy connection/upload/header limits, capacity benchmarks, physical networks, other browser engines and production tuning remain unqualified.
Language toggles use the bounded server route; browser language navigation does not hold the auth lock and is outside the session-request deadline helper.
This change does not implement POS transactions, owner foreground expiry or audit-coverage fixes.

Vitest forces exact UTF-8 limits, chunked/lying lengths, stalled upload/headers/body, cumulative deadlines, bad configuration/JSON/tokens, one command attempt, cookie preservation, logout cleanup and browser lock release.
Chromium uses real Next.js BFF routes and a disposable strict upstream; two deliberately stalled bodies prove no replay/refresh/false logout.
Exact CI source and final reviewed-merge evidence live in the PR result packet.
