from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes import commit
from app.api.schemas import page_of
from app.core.database import db_session
from app.core.permissions import Context, context
from app.domains.customers.models import Customer
from app.domains.customers.schemas import CustomerIn
from app.domains.customers.service import (
    create_customer,
    customer_dict,
    get_customer,
    get_customer_request,
)

router = APIRouter(prefix="/api/v1", tags=["customers"])


@router.post("/customers", status_code=201)
def post_customer(
    payload: CustomerIn,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    customer = create_customer(db, ctx, payload)
    commit(db)
    return customer_dict(customer)


@router.get("/customers")
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    ctx.require("customers.read")
    rows = db.scalars(
        select(Customer).where(Customer.organization_id == ctx.organization.id)
        .order_by(Customer.created_at.desc(), Customer.id)
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return page_of(rows, page, page_size, customer_dict)


@router.get("/customers/{customer_id}")
def read_customer(
    customer_id: UUID,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    return customer_dict(get_customer(db, ctx, customer_id))


@router.get("/customer-requests/{request_id}")
def read_customer_request(
    request_id: UUID,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    # 404 is only a current observation; an in-flight write may still commit.
    return customer_dict(get_customer_request(db, ctx, request_id))
