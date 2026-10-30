"""Strictly internal service drafts: no tax issuance or ledger effects."""

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.exceptions import ConflictError, NotFoundError
from app.core.idempotency import request_digest
from app.core.models import Organization
from app.core.permissions import Context
from app.domains.billing.models import ServiceDraft, ServiceDraftLine
from app.domains.billing.schemas import ServiceDraftIn

CENT = Decimal("0.01")
MAX_MONEY = Decimal("9999999999999999.99")


def line_amount(quantity: Decimal, price: Decimal) -> Decimal:
    return (quantity * price).quantize(CENT, rounding=ROUND_HALF_UP)


def normalized_digest(payload: ServiceDraftIn) -> str:
    return request_digest(
        {
            "operation": "CREATE_INTERNAL_SERVICE_DRAFT",
            "customer_name": payload.customer_name,
            "customer_email": str(payload.customer_email) if payload.customer_email else None,
            "lines": [
                {
                    "service_name": row.service_name,
                    "quantity": format(row.quantity, ".3f"),
                    "unit_price": format(row.unit_price, ".2f"),
                }
                for row in payload.lines
            ],
        }
    )


def draft_dict(db: Session, draft: ServiceDraft) -> dict:
    lines = db.scalars(
        select(ServiceDraftLine)
        .where(
            ServiceDraftLine.organization_id == draft.organization_id,
            ServiceDraftLine.draft_id == draft.id,
        )
        .order_by(ServiceDraftLine.line_number)
    ).all()
    return {
        "id": str(draft.id),
        "organization_id": str(draft.organization_id),
        "request_id": str(draft.request_id),
        "status": draft.status,
        "document_kind": draft.document_kind,
        "tax_status": draft.tax_status,
        "currency": draft.currency,
        "customer_name": draft.customer_name,
        "customer_email": draft.customer_email,
        "amount_before_tax": format(draft.amount_before_tax, ".2f"),
        "created_by": str(draft.created_by),
        "lines": [
            {
                "service_name": row.service_name,
                "line_number": row.line_number,
                "quantity": format(row.quantity, ".3f"),
                "unit_price": format(row.unit_price, ".2f"),
                "line_total": format(row.line_total, ".2f"),
            }
            for row in lines
        ],
    }


def create_draft(db: Session, ctx: Context, payload: ServiceDraftIn) -> ServiceDraft:
    ctx.require("billing.drafts.create")
    # This first slice supports only the qualified two-decimal SAR contract.
    if ctx.organization.currency != "SAR":
        raise ConflictError()

    db.scalar(
        select(Organization.id)
        .where(Organization.id == ctx.organization.id)
        .with_for_update()
    )
    digest = normalized_digest(payload)
    old = db.scalar(
        select(ServiceDraft).where(
            ServiceDraft.organization_id == ctx.organization.id,
            ServiceDraft.request_id == payload.request_id,
        )
    )
    if old is not None:
        if old.request_hash != digest:
            raise ConflictError()
        return old

    amounts = [line_amount(line.quantity, line.unit_price) for line in payload.lines]
    total = sum(amounts, Decimal("0"))
    if total > MAX_MONEY or any(amount > MAX_MONEY for amount in amounts):
        raise ConflictError()

    draft = ServiceDraft(
        organization_id=ctx.organization.id,
        request_id=payload.request_id,
        request_hash=digest,
        customer_name=payload.customer_name,
        customer_email=str(payload.customer_email) if payload.customer_email else None,
        amount_before_tax=total,
        currency="SAR",
        status="BUILDING",
        tax_status="NOT_EVALUATED",
        document_kind="INTERNAL_SERVICE_DRAFT",
        created_by=ctx.user.id,
    )
    db.add(draft)
    db.flush()
    for index, (row, amount) in enumerate(zip(payload.lines, amounts, strict=True), start=1):
        db.add(
            ServiceDraftLine(
                draft_id=draft.id,
                organization_id=ctx.organization.id,
                line_number=index,
                service_name=row.service_name,
                quantity=row.quantity,
                unit_price=row.unit_price,
                line_total=amount,
            )
        )
    db.flush()
    draft.status = "DRAFT"
    db.flush()
    record(
        db,
        "SERVICE_DRAFT_PREPARED",
        "service_draft",
        draft.id,
        ctx.organization.id,
        ctx.user.id,
        after={"request_id": str(draft.request_id), "status": "DRAFT"},
    )
    return draft


def get_draft(db: Session, ctx: Context, draft_id: UUID) -> ServiceDraft:
    ctx.require("billing.drafts.read")
    result = db.scalar(
        select(ServiceDraft).where(
            ServiceDraft.id == draft_id, ServiceDraft.organization_id == ctx.organization.id
        )
    )
    if result is None:
        raise NotFoundError()
    return result
