# SM-ACC-005C3 — Profile-pinned internal tax assessment

Repository n923760-rgb/smart-merchant. Actor Codex /root, single writer and separate
same-session review, not independent review. Verified main/base on 2026-11-03:
d13a5576ef4ed670b262258bef7296bce9a473bc; no open conflicting PR.

Adds an explicitly classified standard-category assessment over an immutable draft,
using the dated declaration and exact calculator already delivered in #38/#39.
Assessment creation/SQL consistency/audit is atomic, requests are durable, source and
profile UUIDs are pinned and old reads/retries do not recalculate under new settings.
No assessment is financial approval or official verification. Source draft and
existing obligation preview semantics are preserved; no AR/journal or deployment.

ADR 0021 documents eligibility, reassessment, scope and future approval requirements.
Actual local/static and external PostgreSQL/migration/browser/mobile/CI evidence and
full diff review will be recorded against the live PR head. Historical 208-test
passes alone do not qualify this new source. No production, merchant, fiscal/provider
or physical-device acceptance is claimed. Merge only after all required checks pass.

Initial CI head 31c41d205f492780c7beb162451d494edf807523, Foundation run
41596175541/backend job 125783942527, found a first-response serialization defect:
new ORM monetary attributes retained string values until reload, so Decimal format
failed after commit (13 failed, 217 passed). Construction now assigns exact Decimal
values from calculator strings, never floats. Existing first-create/read/replay
integration assertions cover this defect. Require a full fresh exact-source pass;
the initial failed source is not qualified or merged.
