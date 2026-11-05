"""Validated decimal-only inputs for internal service drafts, not tax invoices."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field, field_validator, model_validator

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


class TaxProfileIn(Input):
    request_id: UUID
    effective_from: date
    registration_status: Literal["UNKNOWN", "REGISTERED", "NOT_REGISTERED"]
    vat_number: str | None = Field(default=None, pattern=r"^3[0-9]{13}3$")

    @model_validator(mode="after")
    def number_matches_status(self):
        if (self.registration_status == "REGISTERED") != (self.vat_number is not None):
            raise ValueError("Only REGISTERED declarations require a VAT number.")
        return self


class TaxAssessmentIn(Input):
    request_id: UUID
    draft_id: UUID
    assessment_date: date
    category: Literal["STANDARD_15"]
    classification_basis: str = Field(min_length=1, max_length=500)


class ServiceChargeIn(Input):
    request_id: UUID
    assessment_id: UUID
    customer_id: UUID
    receivable_account_id: UUID
    revenue_account_id: UUID
    tax_account_id: UUID
    booking_date: date
    approval_basis: str = Field(min_length=1, max_length=500)
    confirm: Literal[True]
