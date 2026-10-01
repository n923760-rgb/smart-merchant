# Smart Merchant — Master Engineering Roadmap

Single canonical roadmap. Status: GOVERNANCE ADOPTION PROPOSED; PRODUCT NOT QUALIFIED.
Historical baseline: main 737facd48180d7920540f93032ba0a827c9d1ef2; candidate PR #1 42c33b761204c1195b686f2519e419d8bf979f7a; observed 2026-10-01. Reverify live source every session.

## Current state
FACT: main initially contained README only; PR #1 contains application foundation.
FACT: candidate CI run 34741522604 passed; main was unprotected and rulesets were empty.
UNKNOWN: production identities, endpoints, signing, backup/restore and runtime qualification.
Governance addition is a separate bounded PR; no merge or application repair is implied.

## Architecture
Candidate: FastAPI modular monolith + PostgreSQL/Redis; Next.js BFF; Flutter POS/owner skeletons.
Root safety: organization scope, server RBAC, immutable audit, last active owner and financial precision.

## Ordered gates
1. Review adoption diff and exact-source Governance CI; qualify authority and evidence rules.
2. Resolve canonical application source with owner review of PR #1; inspect any overlap before merge.
3. Qualify CLI/lab, disposable services and required toolchains.
4. Diagnose account-switch client cache, then one isolated regression-backed correction.
5. Separate session rounds: BFF limits, concurrent refresh, expired-access logout, owner foreground expiry.
6. Separate audit-coverage diagnosis/correction.
7. Foundation browser/device/runtime acceptance and enforced branch protection.
8. Owner-prioritized bounded merchant features; commercial workflows are not yet specified.
9. Exact-source production artifacts, signing when applicable, backup restore, E2E, monitoring/rollback.
10. Owner release decision.

## Findings and risks
Session issues are source-based hypotheses pending deterministic reproduction; do not combine unrelated fixes.
No permanent agent host, model account or credentials have been provisioned.
Historical CI does not qualify newer source.
No autonomous merge/deploy permission is granted.

## Exact next round
Complete governance review/checks; then owner-protected canonicalization review of foundation PR #1.
Required evidence: live main/PR heads, complete diff, attributable CI and remaining device acceptance.
Application mutation waits for a valid canonical source or explicit alternate-base authority.

## Deferred
Telegram integration (owner instruction); production deployment and release; unspecified commercial feature scope.

## Reports and evidence
- [Baseline](REPORTS/MASTER_ENGINEERING_BASELINE_REPORT.md)
- [Adoption](REPORTS/GOVERNANCE_ADOPTION.md)
- [Evidence index](EVIDENCE/README.md)
