from uuid import UUID

from pydantic import EmailStr, Field

from app.domains.accounting.schemas import Input


class CustomerIn(Input):
    request_id: UUID
    display_name: str = Field(min_length=1, max_length=180)
    email: EmailStr | None = None
