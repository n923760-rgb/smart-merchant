# Engineering Environment Contract

Observed 2026-10-01; reverify at each session.

## Current execution
Repository API/MCP reads verified; isolated Git object/branch/PR writes are available tools and must be evidenced when used.
No shell, clone/worktree, Python/Node/Flutter runtime, Docker, browser or device runner is available in this session.
Do not simulate commands. GitHub Actions is external validation, not local execution.

## Required application lab
Isolated authorized checkout; Git, Python 3.12, Node 22/npm, Flutter/Dart, Docker Compose, disposable PostgreSQL 16 and Redis 7.
Android requires suitable SDK/JDK; iOS requires macOS/Xcode.
Verify installed versions, clean source, free storage, CPU/RAM and single heavy-workload writer before builds.
Paths, quotas and provisioning are UNKNOWN; no machine is provisioned by these files.

## Data and evidence
Only disposable test databases; never run tests against production Redis or PostgreSQL.
Keep tokens, customer data, signing keys and raw dumps outside Git.
Store safe source-attributable reports/evidence under ENGINEERING/.
Retain CI source/PR/run IDs. Candidate APK retention is configured for 14 days; export approved artifacts if longer retention is needed.
Production backup/restore procedure and monitoring are UNKNOWN; restore is NOT RUN.
Use source-specific qualification; a new source change invalidates affected evidence.
