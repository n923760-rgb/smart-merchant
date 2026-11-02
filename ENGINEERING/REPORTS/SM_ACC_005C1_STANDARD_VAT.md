# SM-ACC-005C1 — Standard VAT arithmetic

Repository n923760-rgb/smart-merchant. Actor: Codex /root, single writer and
separate same-session review, no independent review claim. Base main verified
at 25abfe00bbae4c89ce43b0b6a33fc92600b32a2a; no open PR conflict, 2026-11-02.

Adds a pure single-standard-category arithmetic primitive and business-rule
regressions. No endpoint, migration, activation, financial posting or prior preview
behavior changes. Official source verification and exclusions are in ADR 0019.
The live PR records exact-source local/CI results, review and eventual merge;
prior 152-test passes alone are not qualification for this new source.

Next remains taxpayer/category configuration and assessment, financial approval,
atomic AR/journal identity and reconciliation. No production, fiscal/provider,
merchant or physical-device acceptance is implied. Merge is authorized only after
all required checks succeed; production deployment remains outside this task.
