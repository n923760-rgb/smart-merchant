"""Stable, operator-created customer identities without financial effects."""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0007_customers"
down_revision = "0006_service_drafts"
branch_labels = None
depends_on = None

PERMISSIONS = ("customers.read", "customers.create")


def upgrade():
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(180), nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "request_id", name="uq_customers_request"),
        sa.UniqueConstraint("id", "organization_id", name="uq_customers_id_org"),
        sa.CheckConstraint("length(trim(display_name)) > 0", name="ck_customer_name"),
    )
    op.create_index("ix_customers_org_created", "customers", ["organization_id", "created_at"])
    op.execute("""
        CREATE FUNCTION guard_customer_identity() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'customer identity snapshot is immutable';
        END; $$;
        CREATE TRIGGER customer_identity_write_guard
        BEFORE UPDATE OR DELETE ON customers
        FOR EACH ROW EXECUTE FUNCTION guard_customer_identity();
    """)
    conn = op.get_bind()
    for code in PERMISSIONS:
        conn.execute(sa.text(
            "INSERT INTO permissions (id, code) VALUES (:id, :code) ON CONFLICT (code) DO NOTHING"
        ), {"id": uuid4(), "code": code})
    conn.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r JOIN permissions p
            ON p.code IN ('customers.read', 'customers.create')
        WHERE r.code IN ('OWNER', 'ACCOUNTANT')
        ON CONFLICT DO NOTHING
    """))


def downgrade():
    op.execute("DROP TRIGGER customer_identity_write_guard ON customers")
    op.execute("DROP FUNCTION guard_customer_identity()")
    op.drop_index("ix_customers_org_created", table_name="customers")
    op.drop_table("customers")
    conn = op.get_bind()
    for code in PERMISSIONS:
        conn.execute(sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = :code)"
        ), {"code": code})
        conn.execute(sa.text("DELETE FROM permissions WHERE code = :code"), {"code": code})
