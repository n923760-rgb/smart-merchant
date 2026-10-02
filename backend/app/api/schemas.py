from collections.abc import Callable, Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class BootstrapIn(BaseModel):
    owner_name: str = Field(min_length=1)
    owner_email: EmailStr
    owner_password: str = Field(min_length=12)
    organization_name: str = Field(min_length=1)


class BranchIn(BaseModel):
    name: str = Field(min_length=1)
    code: str = Field(pattern=r"^[A-Z0-9_-]{2,40}$")
    city: str | None = None
    region: str | None = None
    address: str | None = None


class BranchPatch(BaseModel):
    name: str | None = None
    city: str | None = None
    status: str | None = None


class UserIn(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=12)
    phone: str | None = None


class AssignRoleIn(BaseModel):
    role_id: UUID
    branch_id: UUID | None = None


class TerminalIn(BaseModel):
    name: str = Field(min_length=1)
    device_identifier: str = Field(min_length=1)
    branch_id: UUID


class TerminalPatch(BaseModel):
    name: str = Field(min_length=1)


class OrganizationPatch(BaseModel):
    name: str | None = None
    legal_name: str | None = None


class Page(BaseModel):
    items: list[dict]
    page: int
    page_size: int


def page_of(
    rows: Sequence[Any], page: int, page_size: int, projector: Callable[[Any], dict]
) -> Page:
    return Page(items=[projector(row) for row in rows], page=page, page_size=page_size)
