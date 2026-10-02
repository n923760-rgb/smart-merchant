# Project Instructions

- Read `docs/architecture` and ADRs before modifying code.
- Respect domain boundaries and keep tenant-scoped queries on `organization_id`.
- Enforce RBAC server-side; never trust client navigation or hidden controls.
- Do not use floats for money or mutate completed financial records.
- Do not expose secrets, raw credentials, or tokens in logs or commits.
- Add tests for all business rules and tenant isolation changes.
- Do not make unrelated refactors or silently change architectural decisions.
- Keep audit records append-only; preserve the last active owner.
