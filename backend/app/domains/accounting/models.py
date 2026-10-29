from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base, IdMixin


class Account(IdMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_accounts_org_code"),
        UniqueConstraint("id", "organization_id", name="uq_accounts_id_org"),
        ForeignKeyConstraint(
            ["parent_id", "organization_id"], ["accounts.id", "accounts.organization_id"],
            name="fk_accounts_parent_org",
        ),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_accounts_not_self_parent"),
        Index("ix_accounts_org_parent", "organization_id", "parent_id"),
        CheckConstraint(
            "account_type IN ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE')",
            name="ck_accounts_type",
        ),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("organizations.id"))
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(180))
    account_type: Mapped[str] = mapped_column(String(20))
    parent_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    is_postable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )



class AccountingPeriod(IdMixin, Base):
    __tablename__ = "accounting_periods"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_period_id_org"),
        CheckConstraint("start_date <= end_date", name="ck_period_dates"),
        CheckConstraint("status IN ('OPEN', 'CLOSED')", name="ck_period_status"),
        CheckConstraint(
            "(status = 'OPEN' AND closed_at IS NULL AND closed_by IS NULL) "
            "OR (status = 'CLOSED' AND closed_at IS NOT NULL AND closed_by IS NOT NULL)",
            name="ck_period_closure_state",
        ),
        Index("ix_periods_org_start", "organization_id", "start_date", "end_date"),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("organizations.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="OPEN")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class JournalEntry(IdMixin, Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_journal_id_org"),
        UniqueConstraint("organization_id", "request_id", name="uq_journal_request"),
        UniqueConstraint("reversal_of_id", name="uq_journal_reversal"),
        ForeignKeyConstraint(
            ["branch_id", "organization_id"], ["branches.id", "branches.organization_id"]
        ),
        ForeignKeyConstraint(
            ["reversal_of_id", "organization_id"],
            ["journal_entries.id", "journal_entries.organization_id"],
        ),
        CheckConstraint("status IN ('DRAFT', 'POSTED')", name="ck_journal_status"),
        CheckConstraint(
            "reversal_of_id IS NULL OR reversal_of_id <> id", name="ck_journal_reversal"
        ),
        Index("ix_journals_org_date", "organization_id", "booking_date", "id"),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("organizations.id"))
    branch_id: Mapped[UUID | None] = mapped_column(Uuid)
    request_id: Mapped[UUID] = mapped_column(Uuid)
    request_hash: Mapped[str] = mapped_column(String(64))
    booking_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(500))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(12), default="DRAFT")
    reversal_of_id: Mapped[UUID | None] = mapped_column(Uuid)
    posted_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class JournalLine(IdMixin, Base):
    __tablename__ = "journal_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["entry_id", "organization_id"],
            ["journal_entries.id", "journal_entries.organization_id"],
        ),
        ForeignKeyConstraint(
            ["account_id", "organization_id"], ["accounts.id", "accounts.organization_id"]
        ),
        UniqueConstraint("entry_id", "line_number", name="uq_journal_line_number"),
        CheckConstraint("line_number > 0", name="ck_journal_line_number"),
        CheckConstraint(
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
            name="ck_journal_line_amount",
        ),
        Index("ix_journal_lines_org_account", "organization_id", "account_id"),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("organizations.id"))
    entry_id: Mapped[UUID] = mapped_column(Uuid)
    account_id: Mapped[UUID] = mapped_column(Uuid)
    line_number: Mapped[int] = mapped_column(Integer)
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    description: Mapped[str | None] = mapped_column(String(500))
