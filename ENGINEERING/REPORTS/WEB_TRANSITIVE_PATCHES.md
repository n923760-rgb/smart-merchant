# Web transitive security patches — SM-SEC-008

Repository: n923760-rgb/smart-merchant. Diagnosis source: main 282a0b3c26f15b198562ff98942e10828b85c71f, observed 2026-10-07. Actor: Codex, sole writer; distinct same-session review, not independent approval. Task: ENGINEERING/EVIDENCE/web-transitive-patches-task.json.

The current high-severity audit identified GHSA-wq5f-xc86-pv6w (sharp) and GHSA-68fv-2mgg-jv7q (source-map-js). This bounded lockfile update resolves sharp 0.35.4 → 0.35.5, its matching platform packages/libvips 1.3.3 → 1.3.4, and source-map-js 1.2.1 → 1.2.2. Direct ranges, Next/eslint integration 16.3.8 and the local glob adapter are unchanged. All other package records are unchanged.

Official advisory references: https://github.com/advisories/GHSA-wq5f-xc86-pv6w and https://github.com/advisories/GHSA-68fv-2mgg-jv7q. npm audit --audit-level=high: PASS, zero vulnerabilities on this lockfile. Fresh npm ci, lint, typecheck, 80 unit tests and production build: PASS on the candidate tree; exact-source Foundation/Governance/Accounting Web checks must pass before the owner-authorized merge. Previous October 3 CI is historical, not qualification of this source.

No application/schema/permission/deployment/secrets changes. Root AGENTS.md preserved. Physical devices, production and release acceptance: NOT RUN. The independent composer task remains pending until integrated security fixes and its own exact-source runtime qualification pass.
