# ADR 0012 — Explicit online journal confirmation and uncertain-result recovery

Status: implemented direction for SM-ACC-003 under the owner's 2026-10-07 continuation. Diagnosis main 282a0b3c26f15b198562ff98942e10828b85c71f. Runtime qualification is source-specific in the accompanying PR.

The web composer requires account-read and journal-post permission in its selected scope. Reads do not imply posting. Posting-only grants participate in accounting navigation but do not authorize account reads. Existing backend authentication, branch RBAC, immutable ledger, request hashing, atomic audit and organization serialization remain authoritative.

Validate dates/UUIDs/row bounds and one positive debit or credit per line. Normalize decimal strings and add integer cents using BigInt without monetary Number coercion. Preview is a separate user step and does not send a write. Explicit checked acknowledgement enables posting. The server still validates every rule independently.

Before any POST, persist the frozen normalized payload and one UUID in a browser-local pending slot namespaced by authenticated user ID, organization ID and branch. Refuse dispatch if persistence fails. No credentials are stored. The minimal financial payload remains only for pending recovery and is removed after a complete matching server result. Storage is not encrypted storage or a disaster-recovery guarantee; a shared/untrusted browser profile is not a qualified financial-device environment.

Same-origin cooperative tabs use a separate nonblocking Web Lock for save/send/clear. Contention cannot dispatch a second command while one is in flight. React also guards synchronous double clicks. A restored record is always uncertain and cannot be edited, discarded, replaced or automatically sent. Independently confirmed commands with different IDs are distinct journal operations, not content deduplication.

A first authoritative 400/403/404/413/422 rejection may clear the initial command for correction. Conflict, malformed success, timeout/transport failure or changed session retain its identity. Any failure of a restored/resend command retains it: a subsequent rejection does not prove an earlier write failed. No reset/discard UI is provided for unresolved conflicts; operators must resolve source permissions/account state or investigate the reference.

GET /api/v1/accounting/journal-requests/{request_id} requires the existing journal-read permission on the requested organization/branch scope before querying. Posting does not grant read access. Query organization, request ID and exact branch together. Missing records return 404; this never proves a still-running request cannot later commit. Users lacking read permission can only explicitly resend the same stored command under their post permission.

Validate the acknowledgement against user, organization, branch, UUID, date, text, every line/amount and totals before removing the pending slot or showing success. The browser session helper already binds requests to the original account/organization context. Unknown outcomes never generate new UUIDs; explicit resend relies on the existing permanent backend identity and returns the same journal.

No schema, accounting/fiscal policy, offline posting or permission defaults change. Existing SAR qualification remains. Physical devices, other browser engines, deletion/tampering of browser storage, independent/noncooperative clients and production qualification remain separate. Persisted-payload tampering is not treated as authorization; all backend validation remains enforced.
