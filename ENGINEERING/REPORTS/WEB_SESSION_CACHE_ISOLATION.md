# SM-WEB-001 — Account cache isolation

Observed: 2026-10-02 UTC.
Repository: n923760-rgb/smart-merchant.
Official main at discovery: 737facd48180d7920540f93032ba0a827c9d1ef2.
Authorized development base: foundation/sprint-01 at 42c33b761204c1195b686f2519e419d8bf979f7a.
Owner explicitly accepted this development base and the first bounded cache-isolation task. Merge remains protected.
Execution capability: repository API/MCP; no local shell/browser runtime.

## Diagnosis
Root layout keeps Providers mounted through SPA navigation. The original provider creates one QueryClient for its lifetime. Logout/login routes reuse that instance, including ['me'], organization/permission and resource data. Shell may choose the previous account's organization from stale ['me'] while identity refetch is pending.

## Correction
Remount SessionQueries at the login/dashboard route boundary. Every auth transition receives a fresh QueryClient and component state; ordinary dashboard navigation keeps one cache. Clear the departing client's query/mutation cache on unmount. Earlier in-flight results remain attached to the disposed client and cannot populate the next account's cache. No tokens are passed to JavaScript as cache keys.

## Regression and validation
A real Chromium session exercises two accounts with controlled synthetic BFF responses. Warm branches/users/devices, retain a pending first-account users request across logout/login, hold new-account responses and assert no old data or wrong organization selection, then verify new-account resource data.
Existing web lint/type/unit/build/audit checks remain in Foundation CI; browser regression is added after production build.
Full diff and CI source identity must be reviewed before qualification.
Local commands/browser/runtime: NOT RUN in the controller API session. External CI status is recorded in PR metadata after execution.
No real backend/provider/device or multi-tab behavior is qualified by the browser fixture.

## Scope
One client session-cache defect; no backend authentication, token rotation, financial/POS changes, unrelated UI refactoring, main writes or merge.
Governance #2 and POS requirements #3 remain separate pending adoption work.
