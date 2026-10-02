# ADR 0005 — RBAC

Status: accepted. Membership roles link a merchant user to a role, optionally scoped to one branch. Grant and removal APIs require organization-wide `roles.manage`; grants may not exceed the grantor's organization-wide permissions; only a global owner may grant OWNER. The final active owner cannot be removed through normal APIs.
