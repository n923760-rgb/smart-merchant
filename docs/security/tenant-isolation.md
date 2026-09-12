# Tenant isolation

Resolve the user and tenant context before reading resources. Every query for branches, roles, terminals, memberships and audit filters by organization. Composite foreign keys reject mismatched organization/branch assignments. Do not use a raw UUID lookup on tenant data. Integration tests create two organizations to verify denial.
