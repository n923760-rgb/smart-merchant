"""Add immutable same-kind account grouping; preserve legacy postable roots."""

import sqlalchemy as sa
from alembic import op

revision = "0003_account_hierarchy"
down_revision = "0002_accounting"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accounts", sa.Column("parent_id", sa.Uuid(), nullable=True))
    op.add_column(
        "accounts",
        sa.Column(
            "is_postable", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )
    op.create_foreign_key(
        "fk_accounts_parent_org",
        "accounts",
        "accounts",
        ["parent_id", "organization_id"],
        ["id", "organization_id"],
    )
    op.create_check_constraint(
        "ck_accounts_not_self_parent",
        "accounts",
        "parent_id IS NULL OR parent_id <> id",
    )
    op.create_index("ix_accounts_org_parent", "accounts", ["organization_id", "parent_id"])
    op.execute("""
        CREATE FUNCTION guard_account_structure() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE parent_kind text;
                parent_postable boolean;
                parent_active boolean;
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF NEW.organization_id IS DISTINCT FROM OLD.organization_id
                    OR NEW.parent_id IS DISTINCT FROM OLD.parent_id
                    OR NEW.account_type IS DISTINCT FROM OLD.account_type
                    OR NEW.is_postable IS DISTINCT FROM OLD.is_postable
                THEN
                    RAISE EXCEPTION 'account classification and ancestry are immutable';
                END IF;
                RETURN NEW;
            END IF;

            IF NEW.parent_id IS NOT NULL THEN
                SELECT account_type, is_postable, is_active
                INTO parent_kind, parent_postable, parent_active
                FROM accounts
                WHERE id = NEW.parent_id AND organization_id = NEW.organization_id
                FOR SHARE;
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'account parent unavailable in organization';
                END IF;
                IF parent_kind IS DISTINCT FROM NEW.account_type
                    OR parent_postable IS DISTINCT FROM false
                    OR parent_active IS DISTINCT FROM true
                THEN
                    RAISE EXCEPTION 'account parent must be an active summary of the same type';
                END IF;
            END IF;
            RETURN NEW;
        END; $$;

        CREATE TRIGGER account_structure_guard BEFORE INSERT OR UPDATE ON accounts
        FOR EACH ROW EXECUTE FUNCTION guard_account_structure();

        CREATE FUNCTION require_postable_journal_account() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_postable boolean;
        BEGIN
            SELECT is_postable INTO target_postable
            FROM accounts
            WHERE id = NEW.account_id AND organization_id = NEW.organization_id;
            IF target_postable IS DISTINCT FROM true THEN
                RAISE EXCEPTION 'cannot post to a summary or foreign account';
            END IF;
            RETURN NEW;
        END; $$;

        CREATE TRIGGER journal_line_postable BEFORE INSERT ON journal_lines
        FOR EACH ROW EXECUTE FUNCTION require_postable_journal_account();
    """)


def downgrade():
    op.execute("DROP TRIGGER journal_line_postable ON journal_lines")
    op.execute("DROP FUNCTION require_postable_journal_account()")
    op.execute("DROP TRIGGER account_structure_guard ON accounts")
    op.execute("DROP FUNCTION guard_account_structure()")
    op.drop_index("ix_accounts_org_parent", table_name="accounts")
    op.drop_constraint("ck_accounts_not_self_parent", "accounts", type_="check")
    op.drop_constraint("fk_accounts_parent_org", "accounts", type_="foreignkey")
    op.drop_column("accounts", "is_postable")
    op.drop_column("accounts", "parent_id")
