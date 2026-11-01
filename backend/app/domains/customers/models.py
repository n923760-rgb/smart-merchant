from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base, IdMixin


class Customer(IdMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("organization_id", "request_id", name="uq_customers_request"),
        UniqueConstraint("id", "organization_id", name="uq_customers_id_org"),
        CheckConstraint("length(trim(display_name)) > 0", name="ck_customer_name"),
        Index("ix_customers_org_created", "organization_id", "created_at"),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("organizations.id"))
    request_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(180), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
