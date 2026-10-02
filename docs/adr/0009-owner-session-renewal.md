# ADR 0009 — Serialized owner session renewal

Status: accepted for SM-AUTH-005 under the owner's continued-development authority.
Diagnosis base: main 2f5440165d7c2f2a8ef7cb07a1204b40456964b8.

The Flutter owner shell renewed only at startup; ordinary auth/me and foreground return did not recover access expiry.
One OwnerSession instance now serializes credential reads, login, refresh, authenticated organization reads and logout within the application isolate. Startup and overlapping resume checks share their in-flight probe.
Probe existing access at startup/resume. If access is absent, retained refresh may initialize it once. With existing access, only an explicit auth/me 401 permits one rotation and one read retry; an authoritative refresh or post-renewal me 401 clears local credentials. Other failures preserve credentials and offer retry.
Validate the complete nonempty token pair before storage writes. No transport, malformed-response or unknown rotation result is automatically replayed.
Each HTTP attempt has a ten-second deadline and closes its client on completion/failure, so a stalled request cannot permanently hold the queue. This is an engineering bound, not a merchant financial policy.

A login/logout intent advances a local context version and immediately hides the prior in-memory session. A completed in-flight rotation still persists its successor, so the queued logout can revoke it, but cannot publish credentials or organization data for an obsolete intent.
The home view retains one organization future per account context, preventing repeated reads on token rebuilds and preventing old account data from resurfacing after a new login.
The app observes foreground return, exposes a localized retry banner on session service failure, and exposes organization errors/empty membership explicitly instead of permanent loading.
No raw credentials/response exceptions are logged. Existing secure-storage token keys, backend strict one-use rotation and refresh-capability logout remain unchanged.

The queue coordinates one application session/isolate, not copied credentials or multiple independent app processes.
Secure storage writes to two keys are not an atomic transaction; process termination/storage failure during rotation and lost successor delivery remain unqualified recovery gaps. A rejected old refresh requires login; no replay grace is introduced.
Transport timeout cannot prove server revocation/rotation did not commit. Local logout is bounded best effort and does not claim online revocation when unreachable.
Body-size/capacity limits, physical mobile suspension/network behavior, real backend device E2E and production secure-storage behavior remain separate qualification work.
No financial, POS, tenant/RBAC, token lifetime or backend schema changes are included.

Required proof: MockClient and secure-storage concurrency/rejection/outage/timeout fixtures, lifecycle/account-context widget regressions, retained logout/foundation tests, all Foundation/Governance CI gates and exact-source review.
The PR result packet records candidate, synthetic checkout, tree and reviewed merge. Same-session review is not independent approval.
