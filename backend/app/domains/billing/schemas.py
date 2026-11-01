"""Validated decimal-only inputs for internal service drafts, not tax invoices."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.domains.accounting.schemas import Input


class ServiceDraftLineIn(Input):
    service_name: str = Field(min_length=1, max_length=180)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)

    @field_validator("quantity", "unit_price", mode="before")
    @classmethod
    def decimal_string(cls, value):
        if not isinstance(value, str):
            raise ValueError("Quantity and price must be decimal strings.")
        return value


class ServiceDraftIn(Input):
    request_id: UUID
    customer_name: str = Field(min_length=1, max_length=180)
    customer_email: EmailStr | None = None
    lines: list[ServiceDraftLineIn] = Field(min_length=1, max_length=100)


class ServiceObligationPreviewIn(Input):
    draft_id: UUID
    customer_id: UUID
    receivable_account_id: UUID
    revenue_account_id: UUID
    booking_date: date
