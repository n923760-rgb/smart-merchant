"""Internal (nonfiscal) service-billing draft persistence."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
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


class TaxProfile(IdMixin, Base):
    __tablename__ = "tax_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "request_id", name="uq_tax_profile_request"),
        UniqueConstraint("organization_id", "effective_from", name="uq_tax_profile_date"),
        UniqueConstraint("id", "organization_id", name="uq_tax_profile_id_org"),
        CheckConstraint("registration_status IN ('UNKNOWN', 'REGISTERED', 'NOT_REGISTERED')", name="ck_tax_profile_status"),
        CheckConstraint("(registration_status = 'REGISTERED' AND vat_number IS NOT NULL AND vat_number ~ '^3[0-9]{13}3$') OR (registration_status <> 'REGISTERED' AND vat_number IS NULL)", name="ck_tax_profile_number"),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("organizations.id"))
    request_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    registration_status: Mapped[str] = mapped_column(String(20), nullable=False)
    vat_number: Mapped[str | None] = mapped_column(String(15))
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class TaxAssessment(IdMixin, Base):
    __tablename__ = "tax_assessments"
    __table_args__ = (
        UniqueConstraint("organization_id", "request_id", name="uq_tax_assessment_request"),
        UniqueConstraint("id", "organization_id", name="uq_tax_assessment_id_org"),
        ForeignKeyConstraint(["draft_id", "organization_id"], ["service_drafts.id", "service_drafts.organization_id"], name="fk_assessment_draft_org"),
        ForeignKeyConstraint(["profile_id", "organization_id"], ["tax_profiles.id", "tax_profiles.organization_id"], name="fk_assessment_profile_org"),
        CheckConstraint("net_amount > 0 AND tax_amount >= 0 AND gross_amount = net_amount + tax_amount", name="ck_assessment_totals"),
        CheckConstraint("tax_amount = round(net_amount * 0.15, 2)", name="ck_assessment_standard_tax"),
        CheckConstraint("length(trim(classification_basis)) > 0", name="ck_assessment_basis"),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("organizations.id"))
    request_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    draft_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    profile_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False)
    classification_basis: Mapped[str] = mapped_column(String(500), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class ServiceDraft(IdMixin, Base):
    __tablename__ = "service_drafts"
    __table_args__ = (
        UniqueConstraint("organization_id", "request_id", name="uq_service_drafts_request"),
        UniqueConstraint("id", "organization_id", name="uq_service_drafts_id_org"),
        CheckConstraint("status IN ('BUILDING', 'DRAFT')", name="ck_service_draft_status"),
        CheckConstraint("amount_before_tax >= 0", name="ck_service_draft_amount"),
        Index("ix_service_drafts_org_created", "organization_id", "created_at"),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("organizations.id"))
    request_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(180), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(320))
    currency: Mapped[str] = mapped_column(String(3), default="SAR", nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="BUILDING", nullable=False)
    tax_status: Mapped[str] = mapped_column(
        String(32), default="NOT_EVALUATED", nullable=False
    )
    document_kind: Mapped[str] = mapped_column(
        String(32), default="INTERNAL_SERVICE_DRAFT", nullable=False
    )
    amount_before_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class ServiceDraftLine(IdMixin, Base):
    __tablename__ = "service_draft_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["draft_id", "organization_id"],
            ["service_drafts.id", "service_drafts.organization_id"],
            name="fk_service_draft_line_org",
        ),
        UniqueConstraint("draft_id", "line_number", name="uq_service_draft_line_number"),
        CheckConstraint("line_number > 0 AND line_number <= 100", name="ck_draft_line_number"),
        CheckConstraint("quantity > 0 AND unit_price >= 0 AND line_total >= 0", name="ck_draft_line_values"),
        CheckConstraint(
            "line_total = round(quantity * unit_price, 2)",
            name="ck_draft_line_exact_total",
        ),
    )
    draft_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    service_name: Mapped[str] = mapped_column(String(180), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class ServiceCharge(IdMixin, Base):
    __tablename__ = "service_charges"
    __table_args__ = (
        UniqueConstraint("organization_id", "request_id", name="uq_charge_request"),
        UniqueConstraint("organization_id", "draft_id", name="uq_charge_source"),
        UniqueConstraint("journal_id", name="uq_charge_journal"),
        CheckConstraint("length(trim(approval_basis)) > 0", name="ck_charge_basis"),
        *(ForeignKeyConstraint([field, "organization_id"], [f"{table}.id", f"{table}.organization_id"], name=f"fk_charge_{field}_org") for field, table in (
            ("draft_id", "service_drafts"), ("assessment_id", "tax_assessments"),
            ("customer_id", "customers"), ("journal_id", "journal_entries"),
            ("receivable_account_id", "accounts"), ("revenue_account_id", "accounts"),
            ("tax_account_id", "accounts"),
        )),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("organizations.id"))
    request_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    draft_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    assessment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    customer_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    journal_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    receivable_account_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    revenue_account_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    tax_account_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    booking_date: Mapped[date] = mapped_column(Date, nullable=False)
    approval_basis: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
