from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AccountIn(Input):
    code: str = Field(pattern=r"^[A-Z0-9_.-]{1,40}$")
    name: str = Field(min_length=1, max_length=180)
    account_type: Literal["ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"]


class LineIn(Input):
    account_id: UUID
    debit: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    credit: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("debit", "credit", mode="before")
    @classmethod
    def decimal_string(cls, value):
        # Monetary JSON numbers can already have lost precision in a client.
        if not isinstance(value, str):
            raise ValueError("Send monetary amounts as decimal strings.")
        return value

    @model_validator(mode="after")
    def one_side(self):
        if (self.debit > 0) == (self.credit > 0):
            raise ValueError("Exactly one side of each line must be positive.")
        return self


class JournalIn(Input):
    request_id: UUID
    branch_id: UUID | None = None
    booking_date: date
    description: str = Field(min_length=1, max_length=500)
    lines: list[LineIn] = Field(min_length=2, max_length=100)

    @model_validator(mode="after")
    def balanced(self):
        if sum(line.debit for line in self.lines) != sum(line.credit for line in self.lines):
            raise ValueError("Journal debits and credits must balance exactly.")
        return self


class ReversalIn(Input):
    request_id: UUID
    booking_date: date
    reason: str = Field(min_length=1, max_length=500)
