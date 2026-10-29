"""Optional organization periods and durable closed-period posting barrier."""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0004_accounting_periods"
down_revision = "0003_account_hierarchy"
branch_labels = None
depends_on = None


PERMISSIONS = ("accounting.periods.read", "accounting.periods.manage")


def upgrade():
    op.create_table(
        "accounting_periods",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("id", "organization_id", name="uq_period_id_org"),
        sa.CheckConstraint("start_date <= end_date", name="ck_period_dates"),
        sa.CheckConstraint("status IN ('OPEN', 'CLOSED')", name="ck_period_status"),
        sa.CheckConstraint(
            "(status = 'OPEN' AND closed_at IS NULL AND closed_by IS NULL) "
            "OR (status = 'CLOSED' AND closed_at IS NOT NULL AND closed_by IS NOT NULL)",
            name="ck_period_closure_state",
        ),
    )
    op.create_index(
        "ix_periods_org_start", "accounting_periods",
        ["organization_id", "start_date", "end_date"],
    )
    op.execute("""
        CREATE FUNCTION guard_accounting_period() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'accounting periods cannot be deleted';
            END IF;
            -- Shared serialization point across API commands, direct SQL, close and post.
            PERFORM 1 FROM organizations WHERE id = NEW.organization_id FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'organization unavailable';
            END IF;

            IF TG_OP = 'UPDATE' THEN
                IF NEW.organization_id IS DISTINCT FROM OLD.organization_id
                    OR NEW.start_date IS DISTINCT FROM OLD.start_date
                    OR NEW.end_date IS DISTINCT FROM OLD.end_date
                    OR NEW.id IS DISTINCT FROM OLD.id
                    OR OLD.status IS DISTINCT FROM 'OPEN'
                    OR NEW.status IS DISTINCT FROM 'CLOSED'
                    OR NEW.closed_at IS NULL OR NEW.closed_by IS NULL
                THEN
                    RAISE EXCEPTION 'only one-way period closure is permitted';
                END IF;
            ELSE
                IF NEW.status IS DISTINCT FROM 'OPEN'
                    OR NEW.closed_at IS NOT NULL OR NEW.closed_by IS NOT NULL
                THEN
                    RAISE EXCEPTION 'periods must be created open';
                END IF;
                IF EXISTS (
                    SELECT 1 FROM accounting_periods p
                    WHERE p.organization_id = NEW.organization_id
                      AND p.start_date <= NEW.end_date AND p.end_date >= NEW.start_date
                ) THEN
                    RAISE EXCEPTION 'overlapping accounting period';
                END IF;
            END IF;
            RETURN NEW;
        END; $$;

        CREATE TRIGGER accounting_period_protection
        BEFORE INSERT OR UPDATE OR DELETE ON accounting_periods
        FOR EACH ROW EXECUTE FUNCTION guard_accounting_period();

        CREATE FUNCTION reject_closed_period_journal() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.status = 'POSTED'
               AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'POSTED') THEN
                PERFORM 1 FROM organizations WHERE id = NEW.organization_id FOR UPDATE;
                IF EXISTS (
                    SELECT 1 FROM accounting_periods p
                    WHERE p.organization_id = NEW.organization_id
                      AND p.status = 'CLOSED'
                      AND NEW.booking_date BETWEEN p.start_date AND p.end_date
                ) THEN
                    RAISE EXCEPTION 'posting in a closed accounting period is forbidden';
                END IF;
            END IF;
            RETURN NEW;
        END; $$;

        CREATE TRIGGER journal_closed_period_protection
        BEFORE INSERT OR UPDATE ON journal_entries
        FOR EACH ROW EXECUTE FUNCTION reject_closed_period_journal();
    """)

    connection = op.get_bind()
    for code in PERMISSIONS:
        connection.execute(
            sa.text(
                "INSERT INTO permissions (id, code) VALUES (:id, :code) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"id": uuid4(), "code": code},
        )
    connection.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r JOIN permissions p
          ON p.code IN ('accounting.periods.read', 'accounting.periods.manage')
        WHERE (
           (r.code = 'OWNER')
           OR (r.code = 'ACCOUNTANT' AND p.code = 'accounting.periods.read')
        ) ON CONFLICT DO NOTHING
    """))


def downgrade():
    op.execute("DROP TRIGGER journal_closed_period_protection ON journal_entries")
    op.execute("DROP FUNCTION reject_closed_period_journal()")
    op.execute("DROP TRIGGER accounting_period_protection ON accounting_periods")
    op.execute("DROP FUNCTION guard_accounting_period()")
    op.drop_index("ix_periods_org_start", table_name="accounting_periods")
    op.drop_table("accounting_periods")
    connection = op.get_bind()
    for code in PERMISSIONS:
        connection.execute(
            sa.text(
                "DELETE FROM role_permissions WHERE permission_id IN "
                "(SELECT id FROM permissions WHERE code = :code)"
            ),
            {"code": code},
        )
        connection.execute(
            sa.text("DELETE FROM permissions WHERE code = :code"), {"code": code}
        )
