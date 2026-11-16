"""Immutable operator-declared receipts and reconciled cash-to-AR journals."""
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0011_service_receipts"
down_revision = "0010_service_charges"
branch_labels = None
depends_on = None
PERMISSIONS = ("billing.receipts.read", "billing.receipts.record")


def upgrade():
    op.create_unique_constraint("uq_charge_id_org", "service_charges", ["id", "organization_id"])
    op.create_table(
        "service_receipts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("charge_id", sa.Uuid(), nullable=False),
        sa.Column("journal_id", sa.Uuid(), nullable=False),
        sa.Column("settlement_account_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("operator_reference", sa.String(120)),
        sa.Column("recording_basis", sa.String(500), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("id", "organization_id", name="uq_receipt_id_org"),
        sa.UniqueConstraint("organization_id", "request_id", name="uq_receipt_request"),
        sa.UniqueConstraint("journal_id", name="uq_receipt_journal"),
        sa.ForeignKeyConstraint(
            ["charge_id", "organization_id"], ["service_charges.id", "service_charges.organization_id"],
            name="fk_receipt_charge_org",
        ),
        sa.ForeignKeyConstraint(
            ["journal_id", "organization_id"], ["journal_entries.id", "journal_entries.organization_id"],
            name="fk_receipt_journal_org",
        ),
        sa.ForeignKeyConstraint(
            ["settlement_account_id", "organization_id"], ["accounts.id", "accounts.organization_id"],
            name="fk_receipt_settlement_account_org",
        ),
        sa.CheckConstraint("amount > 0", name="ck_receipt_amount"),
        sa.CheckConstraint("payment_method IN ('CASH', 'BANK_TRANSFER')", name="ck_receipt_method"),
        sa.CheckConstraint("length(trim(recording_basis)) > 0", name="ck_receipt_basis"),
    )
    op.create_index("ix_receipts_org_charge", "service_receipts", ["organization_id", "charge_id"])
    op.execute("""
        CREATE FUNCTION guard_service_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE c service_charges%ROWTYPE; j journal_entries%ROWTYPE;
                gross numeric(18,2); paid numeric(18,2); org_currency text; org_zone text;
        BEGIN
            IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'service receipts are immutable'; END IF;
            SELECT currency, timezone INTO org_currency, org_zone FROM organizations
              WHERE id = NEW.organization_id FOR UPDATE;
            SELECT * INTO c FROM service_charges
              WHERE id = NEW.charge_id AND organization_id = NEW.organization_id;
            IF c.id IS NULL OR org_currency IS DISTINCT FROM 'SAR'
               OR NEW.booking_date < c.booking_date
               OR NEW.booking_date > (CURRENT_TIMESTAMP AT TIME ZONE org_zone)::date
               OR NEW.settlement_account_id = c.receivable_account_id
            THEN RAISE EXCEPTION 'receipt source/date/currency invalid'; END IF;
            SELECT gross_amount INTO gross FROM tax_assessments
              WHERE id = c.assessment_id AND organization_id = NEW.organization_id;
            SELECT coalesce(sum(amount), 0) INTO paid FROM service_receipts
              WHERE organization_id = NEW.organization_id AND charge_id = NEW.charge_id;
            IF gross IS NULL OR paid + NEW.amount > gross
            THEN RAISE EXCEPTION 'receipt over-collects original receivable'; END IF;
            IF NOT EXISTS (
                SELECT 1 FROM accounts WHERE organization_id = NEW.organization_id
                  AND id = NEW.settlement_account_id AND account_type = 'ASSET'
                  AND is_active AND is_postable
            ) THEN RAISE EXCEPTION 'invalid settlement account'; END IF;
            SELECT * INTO j FROM journal_entries
              WHERE id = NEW.journal_id AND organization_id = NEW.organization_id;
            IF j.id IS NULL OR j.status IS DISTINCT FROM 'POSTED'
               OR j.branch_id IS NOT NULL OR j.reversal_of_id IS NOT NULL
               OR j.currency IS DISTINCT FROM 'SAR' OR j.booking_date IS DISTINCT FROM NEW.booking_date
               OR j.request_id IS DISTINCT FROM NEW.request_id
               OR j.request_hash IS DISTINCT FROM NEW.request_hash
               OR j.posted_by IS DISTINCT FROM NEW.created_by
               OR EXISTS (SELECT 1 FROM journal_entries WHERE organization_id = NEW.organization_id
                           AND reversal_of_id = j.id)
               OR (SELECT count(*) FROM journal_lines WHERE entry_id = j.id
                        AND organization_id = NEW.organization_id) <> 2
               OR NOT EXISTS (SELECT 1 FROM journal_lines WHERE entry_id = j.id
                        AND organization_id = NEW.organization_id
                        AND account_id = NEW.settlement_account_id
                        AND debit = NEW.amount AND credit = 0)
               OR NOT EXISTS (SELECT 1 FROM journal_lines WHERE entry_id = j.id
                        AND organization_id = NEW.organization_id
                        AND account_id = c.receivable_account_id
                        AND credit = NEW.amount AND debit = 0)
            THEN RAISE EXCEPTION 'receipt journal does not reconcile'; END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER service_receipt_integrity BEFORE INSERT OR UPDATE OR DELETE ON service_receipts
          FOR EACH ROW EXECUTE FUNCTION guard_service_receipt();

        CREATE FUNCTION reject_receipt_reversal() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.reversal_of_id IS NOT NULL THEN
                PERFORM 1 FROM organizations WHERE id = NEW.organization_id FOR UPDATE;
                IF EXISTS (SELECT 1 FROM service_receipts WHERE organization_id = NEW.organization_id
                           AND journal_id = NEW.reversal_of_id) THEN
                    RAISE EXCEPTION 'receipt correction requires subledger reconciliation';
                END IF;
            END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER journal_receipt_reversal BEFORE INSERT OR UPDATE ON journal_entries
          FOR EACH ROW EXECUTE FUNCTION reject_receipt_reversal();
    """)
    conn = op.get_bind()
    for code in PERMISSIONS:
        conn.execute(sa.text(
            "INSERT INTO permissions (id, code) VALUES (:id, :code) ON CONFLICT (code) DO NOTHING"
        ), {"id": uuid4(), "code": code})
    conn.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code IN (
          'billing.receipts.read', 'billing.receipts.record'
        )
        WHERE r.code = 'OWNER' OR (r.code = 'ACCOUNTANT' AND p.code = 'billing.receipts.read')
        ON CONFLICT DO NOTHING
    """))


def downgrade():
    op.execute("DROP TRIGGER journal_receipt_reversal ON journal_entries")
    op.execute("DROP FUNCTION reject_receipt_reversal()")
    op.execute("DROP TRIGGER service_receipt_integrity ON service_receipts")
    op.execute("DROP FUNCTION guard_service_receipt()")
    op.drop_index("ix_receipts_org_charge", table_name="service_receipts")
    op.drop_table("service_receipts")
    op.drop_constraint("uq_charge_id_org", "service_charges", type_="unique")
    conn = op.get_bind()
    for code in PERMISSIONS:
        conn.execute(sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = :code)"
        ), {"code": code})
        conn.execute(sa.text("DELETE FROM permissions WHERE code = :code"), {"code": code})
