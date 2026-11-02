# SM-ACC-005C2 — Dated tax-profile declarations

Repository n923760-rgb/smart-merchant; actor Codex /root, single writer and separate
same-session review, not independent review. Base main verified on 2026-11-02 at
1ac1277eeaa0ebe3ffe54a45ffb17ea2d7591352; no open conflicting PR.

Adds immutable owner-declared registration snapshots and permission-scoped as-of
reads. Replay remains durable; dates are forward-only in organization timezone;
PostgreSQL guards immutability, chronological insertion and number/status consistency.
Existing and new OWNER roles manage/read; ACCOUNTANT reads only. VAT numbers are
excluded from audit metadata. No fiscal/calculator/posting activation.

See ADR 0020 for schedule limitations, official sources and the future profile-pinning
requirement. Exact-source local/CI checks, review and eventual authorized merge are
recorded in the live PR description. Local PostgreSQL/Redis/Flutter are unavailable;
integration and migration checks use existing disposable GitHub Actions services.
Production, merchant, fiscal/provider and physical-device acceptance remain NOT RUN.
