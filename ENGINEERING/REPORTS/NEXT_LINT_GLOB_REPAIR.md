# SM-SEC-007 — Next lint glob dependency repair

Repository: n923760-rgb/smart-merchant. Actor: Codex, same-session implementation/review.
Diagnosis base: main 80de2647186d999e98e2ff77eff1e1dd1c7810d0.
Owner expressly authorized continuing and merging on 2026-10-03.

## Outcome

Replace only @next/eslint-plugin-next 16.3.8's directory-glob dependency with an
explicitly named local adapter using pinned tinyglobby 0.2.17. Remove the vulnerable
braces/micromatch engine and its unused dependency chain. Keep Next version,
recommended/Core Web Vitals rules and the unmodified npm audit gate.
The small CommonJS adapter permits only the inspected synchronous directory call;
it fails on unsupported options/input. Disable automatic directory expansion.
.npmrc install-links is required for a reproducible packed local dependency.

## Local qualification

PASS: clean npm ci; lint; TypeScript; 62 Vitest tests (12 new caller/discovery/rule
regressions and 50 existing tests); production build; npm audit reports zero
vulnerabilities. The new tests verify installed plugin version, single glob
importer, named replacement, absence of braces/micromatch in the lock graph,
literal/wildcard/brace/relative/absolute/backslash/array roots, files/hidden/missing
exclusion, no descendant expansion, default cwd, rejected unsupported calls, all
recommended Next rules enabled and actual no-html-link-for-pages enforcement.

PASS: task authority validator and adoption/negative fixtures. Git diff review
checks root AGENTS.md and CI security gates unchanged. Exact published candidate,
tree, full Foundation/Governance checks and final merge evidence belong to its PR;
local checks alone do not authorize integration.

## Limits

This adapter is deliberately not a generic fast-glob replacement. Version-scoped
override and installed-caller tests force reconsideration on Next upgrades. No
upstream patched release is claimed. Remove it when an appropriate upstream fix
qualifies. No application financial/auth or production behavior is changed.
