"""Internal (nonfiscal) service-billing draft persistence."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
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
