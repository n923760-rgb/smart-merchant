"""Immutable reconciled internal customer charges, not fiscal invoices."""
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0010_service_charges"
down_revision = "0009_tax_assessments"
branch_labels = None
depends_on = None
PERMISSIONS = ("billing.charges.read", "billing.charges.approve")


def upgrade():
    op.create_table(
        "service_charges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        *(sa.Column(field, sa.Uuid(), nullable=False) for field in (
            "draft_id", "assessment_id", "customer_id", "journal_id",
            "receivable_account_id", "revenue_account_id", "tax_account_id")),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("approval_basis", sa.String(500), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "request_id", name="uq_charge_request"),
        sa.UniqueConstraint("organization_id", "draft_id", name="uq_charge_source"),
        sa.UniqueConstraint("journal_id", name="uq_charge_journal"),
        sa.CheckConstraint("length(trim(approval_basis)) > 0", name="ck_charge_basis"),
        *(sa.ForeignKeyConstraint([field, "organization_id"], [f"{table}.id", f"{table}.organization_id"], name=f"fk_charge_{field}_org") for field, table in (
            ("draft_id", "service_drafts"), ("assessment_id", "tax_assessments"),
            ("customer_id", "customers"), ("journal_id", "journal_entries"),
            ("receivable_account_id", "accounts"), ("revenue_account_id", "accounts"),
            ("tax_account_id", "accounts"),
        )),
    )
    op.execute("""
        CREATE FUNCTION guard_service_charge() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE a tax_assessments%ROWTYPE; j journal_entries%ROWTYPE;
                profile uuid; registration text; org_currency text; org_zone text;
        BEGIN
            IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'service charges are immutable'; END IF;
            SELECT currency, timezone INTO org_currency, org_zone FROM organizations
              WHERE id = NEW.organization_id FOR UPDATE;
            SELECT * INTO a FROM tax_assessments
              WHERE organization_id = NEW.organization_id AND id = NEW.assessment_id;
            SELECT id, registration_status INTO profile, registration FROM tax_profiles
              WHERE organization_id = NEW.organization_id AND effective_from <= NEW.booking_date
              ORDER BY effective_from DESC LIMIT 1;
            IF org_currency IS DISTINCT FROM 'SAR' OR a.id IS NULL
               OR a.draft_id IS DISTINCT FROM NEW.draft_id
               OR a.assessment_date IS DISTINCT FROM NEW.booking_date
               OR NEW.booking_date > (CURRENT_TIMESTAMP AT TIME ZONE org_zone)::date
               OR profile IS DISTINCT FROM a.profile_id OR registration IS DISTINCT FROM 'REGISTERED'
               OR NOT EXISTS (SELECT 1 FROM service_drafts WHERE id = NEW.draft_id
                  AND organization_id = NEW.organization_id AND status = 'DRAFT'
                  AND currency = 'SAR' AND amount_before_tax = a.net_amount AND amount_before_tax > 0)
            THEN RAISE EXCEPTION 'charge source or profile mismatch'; END IF;
            IF NOT EXISTS (SELECT 1 FROM accounts WHERE id = NEW.receivable_account_id
                  AND organization_id = NEW.organization_id AND account_type = 'ASSET' AND is_active AND is_postable)
               OR NOT EXISTS (SELECT 1 FROM accounts WHERE id = NEW.revenue_account_id
                  AND organization_id = NEW.organization_id AND account_type = 'REVENUE' AND is_active AND is_postable)
               OR NOT EXISTS (SELECT 1 FROM accounts WHERE id = NEW.tax_account_id
                  AND organization_id = NEW.organization_id AND account_type = 'LIABILITY' AND is_active AND is_postable)
            THEN RAISE EXCEPTION 'invalid charge account mapping'; END IF;
            SELECT * INTO j FROM journal_entries WHERE id = NEW.journal_id AND organization_id = NEW.organization_id;
            IF j.id IS NULL OR j.status IS DISTINCT FROM 'POSTED' OR j.branch_id IS NOT NULL
               OR j.reversal_of_id IS NOT NULL OR j.currency IS DISTINCT FROM 'SAR'
               OR j.booking_date IS DISTINCT FROM NEW.booking_date
               OR j.request_id IS DISTINCT FROM NEW.request_id OR j.request_hash IS DISTINCT FROM NEW.request_hash
               OR j.posted_by IS DISTINCT FROM NEW.created_by
               OR EXISTS (SELECT 1 FROM journal_entries WHERE organization_id = NEW.organization_id AND reversal_of_id = j.id)
               OR (SELECT count(*) FROM journal_lines WHERE entry_id = j.id AND organization_id = NEW.organization_id)
                    <> CASE WHEN a.tax_amount > 0 THEN 3 ELSE 2 END
               OR NOT EXISTS (SELECT 1 FROM journal_lines WHERE entry_id = j.id AND organization_id = NEW.organization_id
                    AND account_id = NEW.receivable_account_id AND debit = a.gross_amount AND credit = 0)
               OR NOT EXISTS (SELECT 1 FROM journal_lines WHERE entry_id = j.id AND organization_id = NEW.organization_id
                    AND account_id = NEW.revenue_account_id AND credit = a.net_amount AND debit = 0)
               OR (a.tax_amount > 0 AND NOT EXISTS (SELECT 1 FROM journal_lines WHERE entry_id = j.id AND organization_id = NEW.organization_id
                    AND account_id = NEW.tax_account_id AND credit = a.tax_amount AND debit = 0))
            THEN RAISE EXCEPTION 'charge journal does not reconcile'; END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER service_charge_integrity BEFORE INSERT OR UPDATE OR DELETE ON service_charges
          FOR EACH ROW EXECUTE FUNCTION guard_service_charge();

        CREATE FUNCTION reject_charge_reversal() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.reversal_of_id IS NOT NULL THEN
                PERFORM 1 FROM organizations WHERE id = NEW.organization_id FOR UPDATE;
                IF EXISTS (SELECT 1 FROM service_charges WHERE organization_id = NEW.organization_id
                           AND journal_id = NEW.reversal_of_id) THEN
                    RAISE EXCEPTION 'charge correction requires subledger reconciliation';
                END IF;
            END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER journal_charge_reversal BEFORE INSERT OR UPDATE ON journal_entries
          FOR EACH ROW EXECUTE FUNCTION reject_charge_reversal();
    """)
    conn = op.get_bind()
    for code in PERMISSIONS:
        conn.execute(sa.text("INSERT INTO permissions (id, code) VALUES (:id, :code) ON CONFLICT (code) DO NOTHING"), {"id": uuid4(), "code": code})
    conn.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code IN ('billing.charges.read', 'billing.charges.approve')
        WHERE r.code = 'OWNER' OR (r.code = 'ACCOUNTANT' AND p.code = 'billing.charges.read')
        ON CONFLICT DO NOTHING
    """))


def downgrade():
    op.execute("DROP TRIGGER journal_charge_reversal ON journal_entries")
    op.execute("DROP FUNCTION reject_charge_reversal()")
    op.execute("DROP TRIGGER service_charge_integrity ON service_charges")
    op.execute("DROP FUNCTION guard_service_charge()")
    op.drop_table("service_charges")
    conn = op.get_bind()
    for code in PERMISSIONS:
        conn.execute(sa.text("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = :code)"), {"code": code})
        conn.execute(sa.text("DELETE FROM permissions WHERE code = :code"), {"code": code})
