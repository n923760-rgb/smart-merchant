# MASTER ENGINEERING BASELINE REPORT

Task: SM-GOV-001 — read-only adoption discovery
Observed: 2026-10-01 UTC
Repository: n923760-rgb/smart-merchant
Official/default branch: main
Verified official HEAD: 737facd48180d7920540f93032ba0a827c9d1ef2
Candidate: foundation/sprint-01 at 42c33b761204c1195b686f2519e419d8bf979f7a
Governance reference: n923760-rgb/engineering-governance at 641e4f9e45da109257ba1f38752b94604c2e4531
First-round mode: READ-ONLY. No branches, files, commits, PRs or settings were changed during discovery.
Evidence: GitHub API/source reads; no CLI or runtime execution.

## A. PROJECT IDENTITY
FACT: Smart Merchant Assistant is an early multi-tenant merchant platform foundation. Candidate source contains FastAPI, Next.js and two Flutter application skeletons. Commercial workflows are deferred.

## B. LIVE REPOSITORY STATE
FACT: Repository is public; default main is unprotected. Open PR #1 targets main from foundation/sprint-01 and is not draft. No merged PR was returned. Rulesets API returned an empty list.

## C. CURRENT CANONICAL SOURCE
FACT: main contains README.md only. Runnable candidate code belongs to unmerged PR #1. Candidate findings and historical CI must not be represented as official-main qualification. New governance work derives from main; application implementation waits for canonicalization or an explicit alternate development-base decision.

## D. EXISTING REPOSITORY GOVERNANCE
FACT: main has no AGENTS.md or ENGINEERING roadmap. PR #1 has AGENTS.md, CONTRIBUTING.md, security documents, five ADRs and foundation CI. Candidate-native safety rules should be preserved when integrating governance.

## E. BUILD / RELEASE CONFIGURATION
FACT, candidate only: Python >=3.12; Node 22 in CI; Flutter stable; PostgreSQL 16; Redis 7; Docker Compose backend/worker/database/cache. Web dependencies have npm lockfile; Python ranges and Flutter stable are not a frozen production toolchain. Flutter runners are generated rather than committed. UNKNOWN: production app IDs, signing identity, hosting, deployment ownership and release policy.

## F. APPLICATION / SYSTEM ARCHITECTURE MAP
FACT, candidate only: modular monolith. backend/app/api contains routes/schemas; core owns persistence, security and permission context; domain directories are placeholders. apps/web uses a BFF; apps/owner manages owner sessions; apps/pos has local device/storage scaffolding. No runnable app exists on official main.

## G. AUTHORITATIVE STATE / OWNERSHIP MAP
FACT, candidate only: PostgreSQL owns users, organizations, memberships, roles, branches, terminals, refresh sessions and audit. Redis owns rate-limit counters. Web HttpOnly cookies hold session tokens and selected organization; React Query holds client cache. Flutter secure storage owns local session/device identifiers; POS SQLite owns local configuration scaffolding.

## H. FEATURE / SUBSYSTEM INVENTORY
FACT: candidate implements authentication, tenant/branch permissions, organization bootstrap, user/role/branch/device management and audit. POS is a foundation shell; owner app has login/home/account shells. Catalog, sales, inventory, payments, analytics and AI business features are outside current foundation. Telegram is explicitly deferred by owner.

## I. PLATFORM / RUNTIME CONTRACT
FACT: CI config builds Android debug APKs and iOS simulator apps for both Flutter packages, plus web production build. UNKNOWN: physical devices, browser support matrix, signed packages, production-like environments and restore behavior.

## J. TEST INVENTORY
FACT: candidate has backend unit/integration/security tests, web session-route/permission tests and Flutter foundation widget tests. INFERENCE: account-switch caching, concurrent refresh, expired-token logout and owner foreground expiry lack demonstrated end-to-end coverage.

## K. CI / AUTOMATION INVENTORY
FACT: Foundation CI run 34741522604 succeeded at candidate SHA 42c33b761204c1195b686f2519e419d8bf979f7a. It belongs to PR #1, not main. Backend, web, secret scan, Compose, Android and iOS simulator jobs are configured. FACT: no workflow exists on main. NOT RUN: local tests/builds in this session.

## L. SECURITY / PRIVACY BOUNDARIES
FACT, candidate only: Argon2 password hashes, refresh-token digests, server-side RBAC, composite tenant foreign keys, last-owner protection and append-only audit UPDATE/DELETE trigger. Secrets are environment-fed. UNKNOWN: deployed TLS, least-privilege production DB roles, Redis isolation, recovery and monitoring.

## M. CURRENT EVIDENCE COVERAGE
FACT: attributable source and API evidence plus candidate CI run are available. NOT RUN: local commands, physical-device tests, production deployment, signing and backup restore. No canonical engineering evidence index existed.

## N. RISK / GAP LEDGER
FACT: official-source gap; no branch protection/rulesets; no canonical roadmap/lab qualification.
INFERENCE from candidate inspection: client cache survives account switch; BFF clients share backend IP limits; concurrent refresh can return 401; logout after access expiry may leave refresh session active; owner foreground token expiry lacks renewal/error state; user invite and terminal rename omit audit records.
These are separate future diagnosis/remediation rounds, not permission to combine fixes.

## O. PROPOSED REPOSITORY AUTHORITY MODEL
Current owner instruction, root repository rules, scoped contracts, pinned central governance, exact task packet. Preserve merchant safety rules. Merge/release/deployment remain protected.

## P. PROPOSED PROJECT-SOURCES MODEL
Official main and verified HEAD own adopted state. Keep PR #1 separate as candidate provenance. No silently chosen alternate official branch.

## Q. PROPOSED MASTER ENGINEERING ROADMAP STATE
One ENGINEERING/MASTER_ROADMAP.md: governance adoption -> candidate review/canonicalization -> qualified lab -> isolated session diagnoses/fixes -> foundation runtime acceptance -> bounded product features -> production qualification. Governance/product states remain unqualified until proven.

## R. ENGINEERING LAB PLAN
Use a shell-capable isolated checkout for application work, with disposable PostgreSQL/Redis, Docker, browser tests and Flutter tools. GitHub Actions provides external validation. Never use production data for tests.

## S. REQUIRED LAB TOOLCHAIN
Python 3.12, Git, Node 22/npm, Flutter/Dart compatible with current packages, Android SDK/JDK, macOS/Xcode for iOS, Docker Compose, PostgreSQL 16 and Redis 7. Capacity, paths and installed versions require executor preflight.

## T. CONTROLLER / EXECUTOR OPERATING MODEL
Controller prepares bounded exact-source tasks and reviews evidence. One authorized executor owns source mutation. Reviewer evaluates diff and attributable validation independently of the implementation claim. Agent prompts do not provision a background service or model account.

## U. EVIDENCE / REPORT STORAGE MODEL
Roadmap: ENGINEERING/MASTER_ROADMAP.md. Reports: ENGINEERING/REPORTS/. Evidence: ENGINEERING/EVIDENCE/. Retain safe metadata and exact-source links; keep tokens/private customer data out of Git.

## V. OWNER-PROTECTED DECISIONS
Merge PR #1 or governance PR, release/tag, signing, production deployment, production identity/endpoints, credentials, destructive data/infrastructure operations. None is authorized by general governance adoption.

## W. EXACT NEXT ENGINEERING ROUND
SM-GOV-002: one coherent governance adoption branch from verified main, under the owner's existing instruction to apply this governance and add a development agent. Add root authority, project profile, controller/executor/reviewer instructions, task/result protocol, roadmap and evidence/report structure. Keep application repairs and merge out of scope. Reverify main and PR #1 before mutation. A later canonicalization decision is needed before ordinary application implementation.
