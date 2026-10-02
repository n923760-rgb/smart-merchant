# Testing strategy and acceptance

Unit: password hashing, expiry, RBAC context and validation. Integration: empty PostgreSQL → Alembic upgrade → API tests with Redis → downgrade/upgrade; tenant isolation, last owner, token rotation, audit immutability. Web: login, protected route, hidden navigation, branch controls, denied mutations. Flutter: startup, device state, localization, navigation and session state. Future financial rules require decimal arithmetic, idempotency, transaction and historical immutability tests.

Sprint 01 gates: authentication, tenant isolation, RBAC, migration pipeline, CI. All must pass against the same candidate commit before catalog development. CI is included, but a green run on the actual repository has not yet occurred.
