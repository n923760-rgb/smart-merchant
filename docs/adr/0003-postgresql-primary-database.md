# ADR 0003 — PostgreSQL

Status: accepted. PostgreSQL is the authority for transactional state. Redis is only for short-lived rate limiting, jobs and cache. All schema changes use Alembic. Timestamps are timezone aware and stored as absolute instants.
