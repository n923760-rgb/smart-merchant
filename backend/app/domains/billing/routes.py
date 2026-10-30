"""Organization-scoped internal service draft endpoints (not tax invoices)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes import commit
from app.api.schemas import page_of
from app.core.database import db_session
from app.core.permissions import Context, context
from app.domains.billing.models import ServiceDraft
from app.domains.billing.schemas import ServiceDraftIn
from app.domains.billing.service import create_draft, draft_dict, get_draft

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


@router.post("/service-drafts", status_code=201)
def post_service_draft(
    payload: ServiceDraftIn,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    draft = create_draft(db, ctx, payload)
    commit(db)
    return draft_dict(db, draft)


@router.get("/service-drafts")
def list_service_drafts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    ctx.require("billing.drafts.read")
    rows = db.scalars(
        select(ServiceDraft)
        .where(
            ServiceDraft.organization_id == ctx.organization.id,
            ServiceDraft.status == "DRAFT",
        )
        .order_by(ServiceDraft.created_at.desc(), ServiceDraft.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return page_of(rows, page, page_size, lambda row: draft_dict(db, row))


@router.get("/service-drafts/{draft_id}")
def read_service_draft(
    draft_id: UUID,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    return draft_dict(db, get_draft(db, ctx, draft_id))
