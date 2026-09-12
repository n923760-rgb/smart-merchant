"""Initial frozen foundation schema and append-only audit enforcement."""

from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TABLE organizations (\n\tname VARCHAR(180) NOT NULL, \n\tlegal_name VARCHAR(180), \n\tcommercial_registration VARCHAR(40), \n\ttax_number VARCHAR(40), \n\tcurrency VARCHAR(3) NOT NULL, \n\tcountry_code VARCHAR(2) NOT NULL, \n\ttimezone VARCHAR(64) NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id)\n)"
    )
    op.execute("CREATE INDEX ix_organizations_status ON organizations (status)")
    op.execute(
        "CREATE TABLE outbox_events (\n\tevent_type VARCHAR(100) NOT NULL, \n\taggregate_type VARCHAR(100) NOT NULL, \n\taggregate_id UUID NOT NULL, \n\tpayload JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tprocessed_at TIMESTAMP WITH TIME ZONE, \n\tretry_count INTEGER NOT NULL, \n\tlast_error VARCHAR(500), \n\tid UUID NOT NULL, \n\tPRIMARY KEY (id)\n)"
    )
    op.execute(
        "CREATE TABLE permissions (\n\tcode VARCHAR(100) NOT NULL, \n\tid UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (code)\n)"
    )
    op.execute(
        "CREATE TABLE users (\n\tname VARCHAR(180) NOT NULL, \n\temail VARCHAR(320) NOT NULL, \n\tphone VARCHAR(32), \n\tpassword_hash VARCHAR(255) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tlast_login_at TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (phone)\n)"
    )
    op.execute("CREATE UNIQUE INDEX ix_users_email ON users (email)")
    op.execute("CREATE UNIQUE INDEX uq_users_email_normalized ON users (lower(email))")
    op.execute("CREATE INDEX ix_users_status ON users (status)")
    op.execute(
        "CREATE TABLE audit_logs (\n\torganization_id UUID, \n\tbranch_id UUID, \n\tuser_id UUID, \n\tterminal_id UUID, \n\taction VARCHAR(80) NOT NULL, \n\tentity_type VARCHAR(80) NOT NULL, \n\tentity_id UUID, \n\tbefore_data JSON, \n\tafter_data JSON, \n\tmetadata JSON, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tid UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)"
    )
    op.execute("CREATE INDEX ix_audit_logs_action ON audit_logs (action)")
    op.execute("CREATE INDEX ix_audit_logs_organization_id ON audit_logs (organization_id)")
    op.execute("CREATE INDEX ix_audit_org_created ON audit_logs (organization_id, created_at)")
    op.execute(
        "CREATE TABLE branches (\n\torganization_id UUID NOT NULL, \n\tbrand_id UUID, \n\tname VARCHAR(180) NOT NULL, \n\tcode VARCHAR(40) NOT NULL, \n\taddress VARCHAR(300), \n\tcity VARCHAR(120), \n\tregion VARCHAR(120), \n\ttimezone VARCHAR(64) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, code), \n\tUNIQUE (id, organization_id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)"
    )
    op.execute("CREATE INDEX ix_branches_org_status ON branches (organization_id, status)")
    op.execute("CREATE INDEX ix_branches_organization_id ON branches (organization_id)")
    op.execute(
        "CREATE TABLE idempotency_keys (\n\torganization_id UUID NOT NULL, \n\tkey VARCHAR(200) NOT NULL, \n\toperation VARCHAR(100) NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL, \n\tresponse_data JSON, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tid UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, key, operation), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)"
    )
    op.execute(
        "CREATE INDEX ix_idempotency_keys_organization_id ON idempotency_keys (organization_id)"
    )
    op.execute(
        "CREATE TABLE organization_memberships (\n\torganization_id UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, user_id), \n\tUNIQUE (id, organization_id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)"
    )
    op.execute(
        "CREATE INDEX ix_memberships_user_status ON organization_memberships (user_id, status)"
    )
    op.execute(
        "CREATE INDEX ix_organization_memberships_organization_id ON organization_memberships (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_organization_memberships_user_id ON organization_memberships (user_id)"
    )
    op.execute(
        "CREATE TABLE refresh_sessions (\n\tuser_id UUID NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevoked_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tid UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tUNIQUE (token_hash)\n)"
    )
    op.execute("CREATE INDEX ix_refresh_sessions_user_id ON refresh_sessions (user_id)")
    op.execute(
        "CREATE TABLE roles (\n\torganization_id UUID NOT NULL, \n\tcode VARCHAR(64) NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tis_system BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, code), \n\tUNIQUE (id, organization_id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)"
    )
    op.execute("CREATE INDEX ix_roles_organization_id ON roles (organization_id)")
    op.execute(
        "CREATE TABLE branch_settings (\n\tbranch_id UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\ttimezone VARCHAR(64) NOT NULL, \n\tbusiness_day_cutoff VARCHAR(5) NOT NULL, \n\tdefault_order_type VARCHAR(32) NOT NULL, \n\tnegative_stock_policy VARCHAR(32) NOT NULL, \n\tid UUID NOT NULL, \n\tPRIMARY KEY (branch_id, id), \n\tFOREIGN KEY(branch_id, organization_id) REFERENCES branches (id, organization_id), \n\tUNIQUE (branch_id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)"
    )
    op.execute(
        "CREATE TABLE membership_roles (\n\torganization_id UUID NOT NULL, \n\tmembership_id UUID NOT NULL, \n\trole_id UUID NOT NULL, \n\tbranch_id UUID, \n\tid UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(membership_id, organization_id) REFERENCES organization_memberships (id, organization_id), \n\tFOREIGN KEY(role_id, organization_id) REFERENCES roles (id, organization_id), \n\tFOREIGN KEY(branch_id, organization_id) REFERENCES branches (id, organization_id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)"
    )
    op.execute("CREATE INDEX ix_membership_roles_member ON membership_roles (membership_id)")
    op.execute(
        "ALTER TABLE membership_roles ADD CONSTRAINT uq_membership_role_scope UNIQUE (membership_id, role_id, branch_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_membership_roles_global ON membership_roles (membership_id, role_id) WHERE branch_id IS NULL"
    )
    op.execute(
        "CREATE TABLE role_permissions (\n\trole_id UUID NOT NULL, \n\tpermission_id UUID NOT NULL, \n\tPRIMARY KEY (role_id, permission_id), \n\tFOREIGN KEY(role_id) REFERENCES roles (id), \n\tFOREIGN KEY(permission_id) REFERENCES permissions (id)\n)"
    )
    op.execute(
        "CREATE TABLE terminals (\n\torganization_id UUID NOT NULL, \n\tbranch_id UUID NOT NULL, \n\tname VARCHAR(120) NOT NULL, \n\tdevice_identifier VARCHAR(180) NOT NULL, \n\tactivation_status VARCHAR(20) NOT NULL, \n\tapp_version VARCHAR(40), \n\tlast_seen_at TIMESTAMP WITH TIME ZONE, \n\tlast_sync_at TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(branch_id, organization_id) REFERENCES branches (id, organization_id), \n\tUNIQUE (organization_id, device_identifier), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)"
    )
    op.execute(
        "CREATE INDEX ix_terminals_org_status ON terminals (organization_id, activation_status)"
    )
    op.execute("CREATE INDEX ix_terminals_organization_id ON terminals (organization_id)")
    op.execute(
        "CREATE FUNCTION prevent_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'audit_logs is append-only'; END; $$"
    )
    op.execute(
        "CREATE TRIGGER audit_immutable BEFORE UPDATE OR DELETE ON audit_logs FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation()"
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS audit_immutable ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_mutation()")
    op.execute("DROP TABLE terminals")
    op.execute("DROP TABLE role_permissions")
    op.execute("DROP TABLE membership_roles")
    op.execute("DROP TABLE branch_settings")
    op.execute("DROP TABLE roles")
    op.execute("DROP TABLE refresh_sessions")
    op.execute("DROP TABLE organization_memberships")
    op.execute("DROP TABLE idempotency_keys")
    op.execute("DROP TABLE branches")
    op.execute("DROP TABLE audit_logs")
    op.execute("DROP TABLE users")
    op.execute("DROP TABLE permissions")
    op.execute("DROP TABLE outbox_events")
    op.execute("DROP TABLE organizations")
