from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.exceptions import ConflictError, NotFoundError
from app.core.idempotency import request_digest
from app.core.models import Organization
from app.core.permissions import Context
from app.domains.customers.models import Customer
from app.domains.customers.schemas import CustomerIn


def customer_dict(customer: Customer) -> dict:
    return {
        "id": str(customer.id),
        "organization_id": str(customer.organization_id),
        "request_id": str(customer.request_id),
        "display_name": customer.display_name,
        "email": customer.email,
        "identity_status": "OPERATOR_CREATED",
        "created_by": str(customer.created_by),
        "created_at": customer.created_at.isoformat(),
    }


def create_customer(db: Session, ctx: Context, payload: CustomerIn) -> Customer:
    ctx.require("customers.create")
    # A PostgreSQL lock serializes first submissions and replays across workers.
    db.scalar(select(Organization.id).where(
        Organization.id == ctx.organization.id
    ).with_for_update())
    digest = request_digest({
        "operation": "CREATE_CUSTOMER",
        "display_name": payload.display_name,
        "email": str(payload.email) if payload.email else None,
    })
    previous = db.scalar(select(Customer).where(
        Customer.organization_id == ctx.organization.id,
        Customer.request_id == payload.request_id,
    ))
    if previous is not None:
        if previous.request_hash != digest:
            raise ConflictError()
        return previous

    # Contacts are display details, never canonical identity or merge keys.
    customer = Customer(
        organization_id=ctx.organization.id,
        request_id=payload.request_id,
        request_hash=digest,
        display_name=payload.display_name,
        email=str(payload.email) if payload.email else None,
        created_by=ctx.user.id,
    )
    db.add(customer)
    db.flush()
    record(
        db, "CUSTOMER_CREATED", "customer", customer.id,
        ctx.organization.id, ctx.user.id,
        after={"request_id": str(customer.request_id)},
    )
    return customer


def get_customer(db: Session, ctx: Context, customer_id: UUID) -> Customer:
    ctx.require("customers.read")
    customer = db.scalar(select(Customer).where(
        Customer.organization_id == ctx.organization.id,
        Customer.id == customer_id,
    ))
    if customer is None:
        raise NotFoundError()
    return customer


def get_customer_request(db: Session, ctx: Context, request_id: UUID) -> Customer:
    ctx.require("customers.read")
    customer = db.scalar(select(Customer).where(
        Customer.organization_id == ctx.organization.id,
        Customer.request_id == request_id,
    ))
    if customer is None:
        raise NotFoundError()
    return customer
