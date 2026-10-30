"""Record one immutable organization opening journal and enforce the cutover date."""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0005_opening_balance"
down_revision = "0004_accounting_periods"
branch_labels = None
depends_on = None

PERMISSIONS = ("accounting.opening.read", "accounting.opening.manage")


def upgrade():
    op.create_table(
        "opening_balance_batches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"),
                  nullable=False),
        sa.Column("journal_id", sa.Uuid(), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", name="uq_opening_batches_org"),
        sa.UniqueConstraint("journal_id", name="uq_opening_batches_journal"),
        sa.ForeignKeyConstraint(
            ["journal_id", "organization_id"],
            ["journal_entries.id", "journal_entries.organization_id"],
            name="fk_opening_batches_journal_org",
        ),
    )
    op.execute("""
        CREATE FUNCTION guard_opening_balance_batch() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE linked_date date;
                linked_status text;
                linked_branch uuid;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'opening balance batch is immutable';
            END IF;

            PERFORM 1 FROM organizations WHERE id = NEW.organization_id FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'opening balance organization does not exist';
            END IF;
            SELECT booking_date, status, branch_id
            INTO linked_date, linked_status, linked_branch
            FROM journal_entries
            WHERE id = NEW.journal_id AND organization_id = NEW.organization_id;

            IF NOT FOUND OR linked_status IS DISTINCT FROM 'POSTED'
                OR linked_date IS DISTINCT FROM NEW.booking_date
                OR linked_branch IS NOT NULL
            THEN
                RAISE EXCEPTION 'opening requires an organization-wide posted journal';
            END IF;

            IF EXISTS(
                SELECT 1 FROM journal_entries
                WHERE organization_id = NEW.organization_id AND status = 'POSTED'
                  AND booking_date <= NEW.booking_date AND id <> NEW.journal_id
            ) THEN
                RAISE EXCEPTION 'opening cannot overlap historical journal activity';
            END IF;
            RETURN NEW;
        END; $$;

        CREATE TRIGGER opening_batch_integrity
        BEFORE INSERT OR UPDATE OR DELETE ON opening_balance_batches
        FOR EACH ROW EXECUTE FUNCTION guard_opening_balance_batch();

        CREATE FUNCTION reject_before_opening_journal() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE opening_journal uuid;
                opening_date date;
        BEGIN
            IF NEW.status = 'POSTED'
               AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'POSTED') THEN
                PERFORM 1 FROM organizations WHERE id = NEW.organization_id FOR UPDATE;
                SELECT journal_id, booking_date INTO opening_journal, opening_date
                FROM opening_balance_batches
                WHERE organization_id = NEW.organization_id;

                IF FOUND AND (
                    NEW.reversal_of_id = opening_journal
                    OR (NEW.id <> opening_journal AND NEW.booking_date <= opening_date)
                ) THEN
                    RAISE EXCEPTION 'journal conflicts with immutable opening cutover';
                END IF;
            END IF;
            RETURN NEW;
        END; $$;

        CREATE TRIGGER journal_opening_cutover_protection
        BEFORE INSERT OR UPDATE ON journal_entries
        FOR EACH ROW EXECUTE FUNCTION reject_before_opening_journal();
    """)

    conn = op.get_bind()
    for code in PERMISSIONS:
        conn.execute(
            sa.text(
                "INSERT INTO permissions (id, code) VALUES (:id, :code) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"id": uuid4(), "code": code},
        )
    conn.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r JOIN permissions p
          ON p.code IN ('accounting.opening.read', 'accounting.opening.manage')
        WHERE r.code = 'OWNER'
           OR (r.code = 'ACCOUNTANT' AND p.code = 'accounting.opening.read')
        ON CONFLICT DO NOTHING
    """))


def downgrade():
    op.execute("DROP TRIGGER journal_opening_cutover_protection ON journal_entries")
    op.execute("DROP FUNCTION reject_before_opening_journal()")
    op.execute("DROP TRIGGER opening_batch_integrity ON opening_balance_batches")
    op.execute("DROP FUNCTION guard_opening_balance_batch()")
    op.drop_table("opening_balance_batches")
    conn = op.get_bind()
    for code in PERMISSIONS:
        conn.execute(
            sa.text(
                "DELETE FROM role_permissions WHERE permission_id IN "
                "(SELECT id FROM permissions WHERE code = :code)"
            ),
            {"code": code},
        )
        conn.execute(sa.text("DELETE FROM permissions WHERE code = :code"), {"code": code})
