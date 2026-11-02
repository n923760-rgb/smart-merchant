"""Immutable dated operator tax declarations, never automatic fiscal activation."""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0008_tax_profiles"
down_revision = "0007_customers"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tax_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("registration_status", sa.String(20), nullable=False),
        sa.Column("vat_number", sa.String(15)),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "request_id", name="uq_tax_profile_request"),
        sa.UniqueConstraint("organization_id", "effective_from", name="uq_tax_profile_date"),
        sa.UniqueConstraint("id", "organization_id", name="uq_tax_profile_id_org"),
        sa.CheckConstraint("registration_status IN ('UNKNOWN', 'REGISTERED', 'NOT_REGISTERED')", name="ck_tax_profile_status"),
        sa.CheckConstraint("(registration_status = 'REGISTERED' AND vat_number IS NOT NULL AND vat_number ~ '^3[0-9]{13}3$') OR (registration_status <> 'REGISTERED' AND vat_number IS NULL)", name="ck_tax_profile_number"),
    )
    op.execute("""
        CREATE FUNCTION guard_tax_profile() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE zone text; latest date;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'tax profile declarations are immutable';
            END IF;
            SELECT timezone INTO zone FROM organizations
              WHERE id = NEW.organization_id FOR UPDATE;
            SELECT max(effective_from) INTO latest FROM tax_profiles
              WHERE organization_id = NEW.organization_id;
            IF NEW.effective_from < (CURRENT_TIMESTAMP AT TIME ZONE zone)::date
               OR (latest IS NOT NULL AND NEW.effective_from <= latest) THEN
                RAISE EXCEPTION 'tax profile date cannot be backdated or overlap';
            END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER tax_profile_guard BEFORE INSERT OR UPDATE OR DELETE ON tax_profiles
          FOR EACH ROW EXECUTE FUNCTION guard_tax_profile();
    """)
    conn = op.get_bind()
    for code in ("billing.tax.read", "billing.tax.manage"):
        conn.execute(sa.text("INSERT INTO permissions (id, code) VALUES (:id,:code) ON CONFLICT (code) DO NOTHING"), {"id": uuid4(), "code": code})
    conn.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r JOIN permissions p
        ON (p.code = 'billing.tax.read' AND r.code IN ('OWNER','ACCOUNTANT'))
        OR (p.code = 'billing.tax.manage' AND r.code = 'OWNER')
        ON CONFLICT DO NOTHING
    """))


def downgrade():
    op.execute("DROP TRIGGER tax_profile_guard ON tax_profiles")
    op.execute("DROP FUNCTION guard_tax_profile()")
    op.drop_table("tax_profiles")
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ('billing.tax.read','billing.tax.manage'))")
    op.execute("DELETE FROM permissions WHERE code IN ('billing.tax.read','billing.tax.manage')")
