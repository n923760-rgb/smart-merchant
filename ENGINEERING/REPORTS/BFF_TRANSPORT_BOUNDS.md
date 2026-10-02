# SM-WEB-004 — Web BFF transport bounds

Repository: n923760-rgb/smart-merchant.
Actor: Codex session, sole writer and same-actor reviewer; GitHub Actions external executor.
Diagnosis source: main 9ed105206becda3c88a369f8feff46aa66cda50c.
Authority: owner continuation and explicit continued-development/reviewed-merge grant on 2026-10-02.
Scope: one transport-bounds defect across current web session/proxy routes and the browser auth lock.

SOURCE FACT: routes read req.text/req.json and full fetch bodies without byte bounds, and fetch had no deadlines.
Implementation uses one cumulative BFF deadline, actual streamed UTF-8 byte caps, cancellation, safe errors and no transport retries.
The browser bounds full session response delivery, releasing the shared lock on failure.
Login/refresh write cookies only after complete valid token responses. Bounded failed logout still clears local cookies.
See [ADR 0008](../../docs/adr/0008-bff-transport-bounds.md) and apps/web/.env.example for defaults/ranges.

## Attributable validation

Previous main Foundation/Governance PASS: [36970604523](https://github.com/n923760-rgb/smart-merchant/actions/runs/36970604523) / [36970604435](https://github.com/n923760-rgb/smart-merchant/actions/runs/36970604435), attached only to diagnosis main.
Local shell/runtime: NOT RUN; no local execution tool is exposed.
New Vitest contracts and real-BFF Chromium failure cases are required checks, not preclaimed PASS.
The authoritative exact candidate SHA, complete diff review, job/run links and reviewed merge result are attached to the task PR before integration; this source report does not claim earlier CI for a newer tree.

## Limits

Aborting transport does not prove a mutation was rolled back or a refresh session was revoked.
Lost cookie delivery after rotation, queued-lock latency, real backend browser E2E, browser engines beyond Chromium, network devices/capacity and production are not qualified here.
POS acceptance remains NOT RUN. No deployed permanent agent, Telegram integration, signing or release is claimed.
Next bounded work: owner-client foreground expiry; unrelated audit coverage remains separate.
