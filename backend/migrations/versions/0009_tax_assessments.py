"""Immutable operator standard-tax assessments pinned to source and profile."""

import sqlalchemy as sa
from alembic import op

revision = "0009_tax_assessments"
down_revision = "0008_tax_profiles"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tax_assessments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_date", sa.Date(), nullable=False),
        sa.Column("classification_basis", sa.String(500), nullable=False),
        sa.Column("net_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("gross_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "request_id", name="uq_tax_assessment_request"),
        sa.UniqueConstraint("id", "organization_id", name="uq_tax_assessment_id_org"),
        sa.ForeignKeyConstraint(["draft_id", "organization_id"], ["service_drafts.id", "service_drafts.organization_id"], name="fk_assessment_draft_org"),
        sa.ForeignKeyConstraint(["profile_id", "organization_id"], ["tax_profiles.id", "tax_profiles.organization_id"], name="fk_assessment_profile_org"),
        sa.CheckConstraint("net_amount > 0 AND tax_amount >= 0 AND gross_amount = net_amount + tax_amount", name="ck_assessment_totals"),
        sa.CheckConstraint("tax_amount = round(net_amount * 0.15, 2)", name="ck_assessment_standard_tax"),
        sa.CheckConstraint("length(trim(classification_basis)) > 0", name="ck_assessment_basis"),
    )
    op.execute("""
        CREATE FUNCTION guard_tax_assessment() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE source_total numeric; source_currency text; source_status text;
                selected_profile uuid; selected_status text; org_currency text;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'tax assessment snapshots are immutable';
            END IF;
            SELECT currency INTO org_currency FROM organizations
              WHERE id = NEW.organization_id FOR UPDATE;
            SELECT amount_before_tax, currency, status INTO source_total, source_currency, source_status
              FROM service_drafts WHERE id = NEW.draft_id AND organization_id = NEW.organization_id;
            SELECT id, registration_status INTO selected_profile, selected_status
              FROM tax_profiles WHERE organization_id = NEW.organization_id
              AND effective_from <= NEW.assessment_date ORDER BY effective_from DESC LIMIT 1;
            IF org_currency IS DISTINCT FROM 'SAR' OR source_currency IS DISTINCT FROM 'SAR'
               OR source_status IS DISTINCT FROM 'DRAFT' OR source_total IS DISTINCT FROM NEW.net_amount
               OR selected_profile IS DISTINCT FROM NEW.profile_id
               OR selected_status IS DISTINCT FROM 'REGISTERED' THEN
                RAISE EXCEPTION 'tax assessment source or profile mismatch';
            END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER tax_assessment_guard BEFORE INSERT OR UPDATE OR DELETE ON tax_assessments
          FOR EACH ROW EXECUTE FUNCTION guard_tax_assessment();
    """)


def downgrade():
    op.execute("DROP TRIGGER tax_assessment_guard ON tax_assessments")
    op.execute("DROP FUNCTION guard_tax_assessment()")
    op.drop_table("tax_assessments")
