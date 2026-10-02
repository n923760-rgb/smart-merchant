# Owner session renewal — SM-AUTH-005

Repository: n923760-rgb/smart-merchant. Diagnosis main: 2f5440165d7c2f2a8ef7cb07a1204b40456964b8.
Actor: Codex API session; controller/executor and separate review phase by the same actor.
Local CLI/Flutter/device execution: NOT RUN; unavailable. GitHub Actions is the external executor with disposable fixtures.

The owner session now probes on startup/foreground, recovers explicit access rejection with one serialized refresh, preserves credentials on service failure, bounds each request at ten seconds, and serializes logout after any completed rotation.
Stale account intent cannot publish session/organization results. Home caches only within an account context. Retry UI replaces indefinite loading for errors/empty memberships.

Required candidate checks: all eight Foundation jobs (including owner formatter/analyzer/tests/Android/iOS simulator), Governance task validation, full diff and byte-exact root AGENTS preservation.
Exact candidate/check/run/merge results are attached as a structured result packet in this task's PR body; this avoids a source commit that refers to its own SHA. Do not infer PASS from this source report.
Physical suspension/networks, secure-storage crash atomicity, lost rotation delivery, real backend/device E2E and production remain NOT RUN.
See [ADR 0009](../../docs/adr/0009-owner-session-renewal.md).
