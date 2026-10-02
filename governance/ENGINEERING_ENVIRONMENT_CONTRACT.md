# Engineering Environment Contract

Observed 2026-10-02; reverify at each session.

## Current execution
Repository API/MCP reads verified; isolated Git object/branch/PR writes and owner-authorized merges have been executed and verified.
No shell, clone/worktree, Python/Node/Flutter runtime, Docker, browser or device runner is available in this session.
Do not simulate commands. GitHub Actions is the available external executor for bounded, reproducible checks: Python 3.12, Node 22, disposable PostgreSQL 16/Redis 7, Compose, Chromium and Flutter Android/iOS simulator jobs have passed on attributable sources. It is not a local or permanently provisioned interactive lab. Do not use it for uncontrolled experiments or production data.

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
