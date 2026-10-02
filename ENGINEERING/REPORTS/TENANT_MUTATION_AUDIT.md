# Tenant mutation audit coverage — SM-AUDIT-006

Repository: n923760-rgb/smart-merchant. Diagnosis main: 6b6a5107ffa6867adcbcb26adb8233780d14a2c0.
Actor: Codex API session, sole source writer; controller/executor and distinct review phase by the same actor. Not independent approval.
Local Python/PostgreSQL execution: NOT RUN; unavailable. GitHub Actions supplies disposable PostgreSQL/Redis and application checks.

Existing POST /users immediately creates an active membership, for a new or existing global user; this repair does not add invitation email/token delivery.
After membership flush, USER_INVITED records entity_type=membership, entity_id=membership ID, organization=the authorized context, actor=inviter, before=null and after={user_id,status}. No branch, password/hash/token, email/phone/name or foreign organization data is copied into that event.
Duplicate, inactive-user and permission rejections retain their existing behavior and create no success event.

Existing PATCH /terminals/{id} preserves organization filtering and branch/global terminals.manage authorization.
A PostgreSQL row lock serializes accepted rename before-state capture. TERMINAL_RENAMED records terminal identity, branch, organization, actor and only before/after name.
Each accepted command, including a no-op rename, records one event. This is per-command audit, not an idempotent rename protocol.
Both events are appended before the existing commit, in the same database transaction. Audit insertion failure rolls back business mutation; no historical records are rewritten/backfilled.

Required proof: seven PostgreSQL API regressions for new/existing users, minimal snapshots/credentials preservation, duplicates, accepted/no-op rename, foreign tenant isolation, branch/global permission boundaries and forced audit foreign-key failure for invite/rename rollback.
Retain all foundation, last-owner, append-only and auth checks. Exact candidate/run/review/merge results live in the task PR result packet, avoiding self-referential source SHAs.
Real parallel-request load, production actor data, physical devices and complete POS-148 remain NOT RUN. Row locking is source-reviewed; parallel capacity/load is not claimed.
