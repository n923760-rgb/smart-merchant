"""General chart and balanced, immutable posted journal foundation."""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0002_accounting"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None

PERMISSIONS = (
    "accounting.accounts.read",
    "accounting.accounts.manage",
    "accounting.journals.read",
    "accounting.journals.post",
    "accounting.journals.reverse",
)


def upgrade():
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "code", name="uq_accounts_org_code"),
        sa.UniqueConstraint("id", "organization_id", name="uq_accounts_id_org"),
        sa.CheckConstraint(
            "account_type IN ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE')",
            name="ck_accounts_type",
        ),
    )
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("branch_id", sa.Uuid()),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("reversal_of_id", sa.Uuid()),
        sa.Column("posted_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("id", "organization_id", name="uq_journal_id_org"),
        sa.UniqueConstraint("organization_id", "request_id", name="uq_journal_request"),
        sa.UniqueConstraint("reversal_of_id", name="uq_journal_reversal"),
        sa.ForeignKeyConstraint(
            ["branch_id", "organization_id"], ["branches.id", "branches.organization_id"]
        ),
        sa.ForeignKeyConstraint(
            ["reversal_of_id", "organization_id"],
            ["journal_entries.id", "journal_entries.organization_id"],
        ),
        sa.CheckConstraint("status IN ('DRAFT', 'POSTED')", name="ck_journal_status"),
        sa.CheckConstraint(
            "reversal_of_id IS NULL OR reversal_of_id <> id", name="ck_journal_reversal"
        ),
    )
    op.create_index(
        "ix_journals_org_date", "journal_entries", ["organization_id", "booking_date", "id"]
    )
    op.create_table(
        "journal_lines",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("entry_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("debit", sa.Numeric(18, 2), nullable=False),
        sa.Column("credit", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.ForeignKeyConstraint(
            ["entry_id", "organization_id"],
            ["journal_entries.id", "journal_entries.organization_id"],
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "organization_id"], ["accounts.id", "accounts.organization_id"]
        ),
        sa.UniqueConstraint("entry_id", "line_number", name="uq_journal_line_number"),
        sa.CheckConstraint("line_number > 0", name="ck_journal_line_number"),
        sa.CheckConstraint(
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
            name="ck_journal_line_amount",
        ),
    )
    op.create_index(
        "ix_journal_lines_org_account", "journal_lines", ["organization_id", "account_id"]
    )
    op.execute("""
        CREATE FUNCTION guard_posted_journal() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status = 'POSTED' THEN
                RAISE EXCEPTION 'posted journal is immutable';
            END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER journal_immutable BEFORE UPDATE OR DELETE ON journal_entries
        FOR EACH ROW EXECUTE FUNCTION guard_posted_journal();

        CREATE FUNCTION guard_journal_line() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE entry_status text;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'journal lines are immutable';
            END IF;
            SELECT status INTO entry_status FROM journal_entries
            WHERE id = NEW.entry_id AND organization_id = NEW.organization_id FOR UPDATE;
            IF entry_status IS DISTINCT FROM 'DRAFT' THEN
                RAISE EXCEPTION 'cannot add lines to posted journal';
            END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER journal_line_immutable BEFORE INSERT OR UPDATE OR DELETE ON journal_lines
        FOR EACH ROW EXECUTE FUNCTION guard_journal_line();

        CREATE FUNCTION require_balanced_posted_journal() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE journal journal_entries%ROWTYPE;
                line_count integer;
                debit_sum numeric;
                credit_sum numeric;
        BEGIN
            SELECT * INTO journal FROM journal_entries WHERE id = NEW.id;
            IF NOT FOUND THEN RETURN NULL; END IF;
            IF journal.status <> 'POSTED' OR journal.posted_at IS NULL THEN
                RAISE EXCEPTION 'journal must finish posting before commit';
            END IF;
            SELECT count(*), coalesce(sum(debit), 0), coalesce(sum(credit), 0)
            INTO line_count, debit_sum, credit_sum FROM journal_lines
            WHERE entry_id = journal.id AND organization_id = journal.organization_id;
            IF line_count < 2 OR debit_sum <= 0 OR debit_sum <> credit_sum THEN
                RAISE EXCEPTION 'journal must contain balanced positive lines';
            END IF;
            RETURN NULL;
        END; $$;
        CREATE CONSTRAINT TRIGGER journal_balanced AFTER INSERT OR UPDATE ON journal_entries
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
        EXECUTE FUNCTION require_balanced_posted_journal();
    """)
    connection = op.get_bind()
    for code in PERMISSIONS:
        connection.execute(
            sa.text(
                "INSERT INTO permissions (id, code) VALUES (:id, :code) ON CONFLICT (code) DO NOTHING"
            ),
            {"id": uuid4(), "code": code},
        )
    connection.execute(
        sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.code IN ('OWNER', 'ACCOUNTANT') AND r.is_system = true
        AND p.code LIKE 'accounting.%' ON CONFLICT DO NOTHING
    """)
    )


def downgrade():
    op.execute("DROP FUNCTION require_balanced_posted_journal() CASCADE")
    op.execute("DROP FUNCTION guard_journal_line() CASCADE")
    op.execute("DROP FUNCTION guard_posted_journal() CASCADE")
    op.drop_table("journal_lines")
    op.drop_table("journal_entries")
    op.drop_table("accounts")
    connection = op.get_bind()
    for code in PERMISSIONS:
        connection.execute(
            sa.text("""
            DELETE FROM role_permissions WHERE permission_id IN
            (SELECT id FROM permissions WHERE code = :code)
        """),
            {"code": code},
        )
        connection.execute(sa.text("DELETE FROM permissions WHERE code = :code"), {"code": code})
