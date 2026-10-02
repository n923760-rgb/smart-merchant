# SM-AUTH-002 — Logout after access expiry

Date: 2026-10-02. Repository: n923760-rgb/smart-merchant.
Actor: same API controller for implementation/review; GitHub Actions executes checks. Independent review and local CLI: NOT RUN.

## Diagnosis

At foundation source ad50311a9df9b522607eea17fd4f65f6cc782078, /auth/logout depends on current_user. JWT decoding rejects expired access before revoke_refresh executes, even though the supplied refresh session remains valid.
BFF DELETE and OwnerSession.logout require both access and refresh; a refresh-only session skips server revocation.

## Correction

Use the opaque refresh token as a capability for one session's revocation. Lock its unique digest match; preserve idempotency, uniform response and rate limiting. Record one token-free USER_LOGOUT audit in the same transaction.
Web and owner clients revoke whenever refresh is present, then clear local credentials.
See ADR 0006. Concurrent rotation/family revocation, BFF limits, owner foreground expiry and general audit coverage remain separate tasks.

## Required checks and evidence

Backend integration: expired/missing access, disabled user, one audit, repeated/unknown token and another session remains refreshable.
Web: refresh-only forwarding and cleanup if upstream fails.
Owner: refresh-only revocation with injected HTTP and secure storage, plus local cleanup on network error.
Keep existing lint/types/migrations/browser/audits/Flutter/Compose gates enabled.
CI source/head/run/results are retained in the PR result packet and metadata after execution. No final pass is claimed by this pre-execution report.
Physical devices, real backend browser journey, offline POS/payment/provider/hardware and production: NOT RUN.
