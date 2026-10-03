# ADR 0011 — Bounded replacement of Next lint directory globbing

Status: accepted for SM-SEC-007 under owner continuation/merge authority, 2026-10-03.
Diagnosis main: 80de2647186d999e98e2ff77eff1e1dd1c7810d0.

Next 16.3.8's ESLint plugin pulls fast-glob/micromatch/braces, blocked by
GHSA-vfj7-8cjw-p6xm. No patched braces release was observed. Keep Next, all its
lint rules and the complete high-severity npm audit gate; no exception/downgrade.

The installed exact plugin has one fast-glob importer, get-root-dirs.js, using
only globSync(string, {onlyDirectories:true}). A version-scoped npm override
replaces that dependency with our explicitly named, private directory adapter
backed by pinned tinyglobby 0.2.17. It is not a general fast-glob implementation.
Unsupported input/options fail closed. Disable expandDirectories as required by
tinyglobby's migration guide, preserving explicit-root semantics.

Regression tests verify the installed caller contract, dependency resolution,
directory patterns (literal/wildcard/brace/absolute/backslash/array),
no-root fallback, and actual Next rule enforcement with configured root discovery.
The override applies only to plugin 16.3.8. Upgrades require new caller review,
semantic tests and audit; remove the adapter once a suitable upstream fix exists.
Project .npmrc enables install-links so npm packs this local dependency rather
than creating an unresolved importer-relative symlink; clean CI install is tested.
No application runtime, tenant/auth or financial changes are included.

References: https://github.com/advisories/GHSA-vfj7-8cjw-p6xm and
https://superchupu.dev/tinyglobby/migration.
