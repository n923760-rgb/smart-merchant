# ADR 0006 — Refresh-capability logout

Status: accepted for the bounded logout repair under the owner's continued-development authority.
Scope: POST /api/v1/auth/logout and the existing web/owner callers.

## Problem

Access tokens expire before refresh sessions. Requiring a current access token for logout rejects a legitimate logout after expiry, leaving the refresh session reusable. Web/owner callers also skipped revocation when only the refresh token was available.

## Decision

The opaque refresh capability authorizes revocation of exactly the session whose unique stored SHA-256 digest matches it.
Logout does not require or derive identity from an access token, organization header or client-supplied user ID.
Lock the matched row, set revoked_at once, and insert one USER_LOGOUT audit record in the same database transaction. The stored session determines the audit actor/entity.
Return an empty 204 for valid, unknown and already-revoked tokens so callers can retry without disclosing session existence.
Apply the existing Redis IP rate limiter. Never store/log the raw token in audit evidence.
Web and owner callers attempt revocation whenever a refresh token exists, then clear local credentials. HTTP cookies remain HttpOnly/SameSite Strict.

## Boundaries and consequences

Possession of a refresh token already authorizes access-token issuance; granting scoped revocation adds no ability to choose or mutate another session.
Other sessions, including those of the same user, remain active. This is not logout-all or refresh-family revocation.
An already-rotated token cannot revoke its successor; refresh/logout concurrency across rotation families is a separate session-design task.
Clearing local credentials during a network outage does not prove server revocation. This preserves existing local logout behavior; no online guarantee is claimed when the endpoint is unreachable.
The append-only audit model is preserved. Auth events are global and not projected into a merchant audit view in this round.
No schema, money, POS, token lifetime or password changes are included.

## Validation

Disposable PostgreSQL integration covers expired/missing access, disabled user, unknown/repeated tokens, one audit and retained other sessions.
Web regression covers refresh-only forwarding and local cookie cleanup during failure.
Owner regression uses MockClient and secure-storage fixtures to prove refresh-only revocation and local cleanup.
Exact-source Foundation/Governance CI is required before merge. Real device/network/provider behavior is not qualified by these fixtures.
