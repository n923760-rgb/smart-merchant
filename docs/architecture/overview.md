# Architecture

Modular monolith: FastAPI + PostgreSQL primary data + Redis ephemeral operations; Next.js BFF and Flutter clients. Every tenant resource lookup includes `organization_id`. One active user, active organization and active membership are required before permission evaluation. Global and branch-scoped grants are additive; a branch-scoped permission never authorizes another branch. Audit is append-only in PostgreSQL. See ADRs and security docs.
