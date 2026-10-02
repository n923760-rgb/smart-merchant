# SM-AUTH-003 — Concurrent web session renewal

Repository: n923760-rgb/smart-merchant.
Actor: Codex session, sole source writer and same-actor reviewer.
Official diagnosis source: main d273ea5ca0e7a841b3db423840d6cecb95011d8a.
Authority: owner continuation and explicit continued-development/reviewed-merge grant on 2026-10-02.
Scope: one BFF/session concurrency defect; see [ADR 0007](../../docs/adr/0007-web-session-renewal.md).

## Source facts and implementation

SOURCE FACT: proxy request snapshots independently rotated one-use tokens; auth/me errors unconditionally redirected to login.
INFERENCE: simultaneous expired requests can produce a false logout. The new deterministic regressions force those rejected requests.
Implementation removes proxy rotation, serializes browser session operations across tabs, rechecks current access under the lock, and retries a rejected authorization once.
Non-secret context binding rejects stale account/organization requests before backend forwarding and rejects late data before client consumption.
Refresh credentials remain HttpOnly, and backend strict rotation/RBAC are unchanged.
Login clears the prior organization, changes context, and requires an initial sign-in for legacy cookies after rollout.

## Attributable checks

Local shell/browser execution: NOT RUN; this environment only exposes GitHub source APIs.
Candidate Foundation/Governance CI: pending exact pushed head. Final results, source SHA, job/run links and review evidence must be attached to the PR before merge.
Added Vitest and real-BFF Chromium fixtures are committed requirements, not preclaimed PASS.
Existing synthetic account-cache regression and PostgreSQL one-use refresh regression are retained.
Previous main Foundation/Governance PASS: [36967403546](https://github.com/n923760-rgb/smart-merchant/actions/runs/36967403546) / [36967403567](https://github.com/n923760-rgb/smart-merchant/actions/runs/36967403567), attached only to d273ea5ca0e7a841b3db423840d6cecb95011d8a.

## Residual limits

Requires modern browser Web Locks over HTTPS/localhost. Same-origin browser storage partition only.
Real backend browser E2E, multi-instance runtime, Safari/Firefox, physical devices and production: NOT RUN.
Abrupt rotation/network failure with lost cookie delivery is not recovered by weakening one-use refresh.
Cross-tab already-rendered query caches before another request remain a separate qualification task.
BFF timeout/body limits, owner foreground expiry and unrelated audit coverage remain separate rounds.
No permanent background agent, payment adapter, POS transaction implementation or production readiness is claimed.
Final exact-source result is a PR attachment so adding its own tested SHA cannot invalidate the tested tree.
