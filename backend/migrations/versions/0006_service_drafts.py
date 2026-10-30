"""Nonfiscal internal service draft, exact decimal and immutable snapshot."""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0006_service_drafts"
down_revision = "0005_opening_balance"
branch_labels = None
depends_on = None

PERMISSIONS = ("billing.drafts.read", "billing.drafts.create")


def upgrade():
    op.create_table(
        "service_drafts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("customer_name", sa.String(180), nullable=False),
        sa.Column("customer_email", sa.String(320), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("tax_status", sa.String(32), nullable=False),
        sa.Column("document_kind", sa.String(32), nullable=False),
        sa.Column("amount_before_tax", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "request_id", name="uq_service_drafts_request"),
        sa.UniqueConstraint("id", "organization_id", name="uq_service_drafts_id_org"),
        sa.CheckConstraint("status IN ('BUILDING', 'DRAFT')", name="ck_service_draft_status"),
        sa.CheckConstraint("amount_before_tax >= 0", name="ck_service_draft_amount"),
    )
    op.create_index("ix_service_drafts_org_created", "service_drafts",
                    ["organization_id", "created_at"])
    op.create_table(
        "service_draft_lines",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("service_name", sa.String(180), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(
            ["draft_id", "organization_id"], ["service_drafts.id", "service_drafts.organization_id"],
            name="fk_service_draft_line_org",
        ),
        sa.UniqueConstraint("draft_id", "line_number", name="uq_service_draft_line_number"),
        sa.CheckConstraint("line_number > 0 AND line_number <= 100", name="ck_draft_line_number"),
        sa.CheckConstraint("quantity > 0 AND unit_price >= 0 AND line_total >= 0",
                           name="ck_draft_line_values"),
        sa.CheckConstraint("line_total = round(quantity * unit_price, 2)",
                           name="ck_draft_line_exact_total"),
    )
    op.execute("""
        CREATE FUNCTION guard_service_draft() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'internal service draft cannot be deleted';
            ELSIF TG_OP = 'INSERT' THEN
                IF NEW.status IS DISTINCT FROM 'BUILDING'
                  OR NEW.currency IS DISTINCT FROM 'SAR'
                  OR NEW.tax_status IS DISTINCT FROM 'NOT_EVALUATED'
                  OR NEW.document_kind IS DISTINCT FROM 'INTERNAL_SERVICE_DRAFT'
                THEN
                    RAISE EXCEPTION 'unsupported service draft state or classification';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.status IS DISTINCT FROM 'BUILDING'
               OR NEW.status IS DISTINCT FROM 'DRAFT'
               OR (to_jsonb(NEW) - 'status') IS DISTINCT FROM
                  (to_jsonb(OLD) - 'status') THEN
                RAISE EXCEPTION 'only initial service draft sealing is allowed';
            END IF;
            RETURN NEW;
        END; $$;

        CREATE TRIGGER service_draft_write_guard
        BEFORE INSERT OR UPDATE OR DELETE ON service_drafts
        FOR EACH ROW EXECUTE FUNCTION guard_service_draft();

        CREATE FUNCTION guard_service_draft_line() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE parent_status text;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'internal draft lines are immutable';
            END IF;
            SELECT status INTO parent_status FROM service_drafts
            WHERE id = NEW.draft_id AND organization_id = NEW.organization_id
            FOR UPDATE;
            IF parent_status IS DISTINCT FROM 'BUILDING' THEN
                RAISE EXCEPTION 'lines can only be added during draft construction';
            END IF;
            RETURN NEW;
        END; $$;

        CREATE TRIGGER service_draft_line_write_guard
        BEFORE INSERT OR UPDATE OR DELETE ON service_draft_lines
        FOR EACH ROW EXECUTE FUNCTION guard_service_draft_line();

        CREATE FUNCTION require_complete_service_draft() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE current_state text;
                actual_total numeric;
                expected_total numeric;
                count_lines integer;
        BEGIN
            SELECT status, amount_before_tax INTO current_state, expected_total
            FROM service_drafts WHERE id = NEW.id AND organization_id = NEW.organization_id;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;
            SELECT count(*), coalesce(sum(line_total), 0)
            INTO count_lines, actual_total FROM service_draft_lines
            WHERE organization_id = NEW.organization_id AND draft_id = NEW.id;
            IF current_state IS DISTINCT FROM 'DRAFT'
               OR count_lines < 1 OR count_lines > 100
               OR expected_total IS DISTINCT FROM actual_total
            THEN
                RAISE EXCEPTION 'incomplete or inconsistent service draft';
            END IF;
            RETURN NULL;
        END; $$;

        CREATE CONSTRAINT TRIGGER service_draft_complete
        AFTER INSERT OR UPDATE ON service_drafts
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION require_complete_service_draft();
    """)
    conn = op.get_bind()
    for code in PERMISSIONS:
        conn.execute(
            sa.text("INSERT INTO permissions (id, code) VALUES (:id, :code) "
                    "ON CONFLICT (code) DO NOTHING"),
            {"id": uuid4(), "code": code},
        )
    conn.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r JOIN permissions p
          ON p.code IN ('billing.drafts.read', 'billing.drafts.create')
        WHERE r.code IN ('OWNER', 'ACCOUNTANT')
        ON CONFLICT DO NOTHING
    """))


def downgrade():
    op.execute("DROP TRIGGER service_draft_complete ON service_drafts")
    op.execute("DROP FUNCTION require_complete_service_draft()")
    op.execute("DROP TRIGGER service_draft_line_write_guard ON service_draft_lines")
    op.execute("DROP FUNCTION guard_service_draft_line()")
    op.execute("DROP TRIGGER service_draft_write_guard ON service_drafts")
    op.execute("DROP FUNCTION guard_service_draft()")
    op.drop_table("service_draft_lines")
    op.drop_index("ix_service_drafts_org_created", table_name="service_drafts")
    op.drop_table("service_drafts")
    conn = op.get_bind()
    for code in PERMISSIONS:
        conn.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_id IN "
                    "(SELECT id FROM permissions WHERE code = :code)"),
            {"code": code},
        )
        conn.execute(sa.text("DELETE FROM permissions WHERE code = :code"), {"code": code})
