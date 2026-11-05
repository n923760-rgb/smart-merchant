"""Organization-scoped internal service draft endpoints (not tax invoices)."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes import commit
from app.api.schemas import page_of
from app.core.database import db_session
from app.core.permissions import Context, context
from app.domains.billing.charges import approve_charge, charge_dict, get_charge
from app.domains.billing.models import ServiceDraft
from app.domains.billing.obligation_preview import preview_obligation
from app.domains.billing.schemas import (
    ServiceChargeIn,
    ServiceDraftIn,
    ServiceObligationPreviewIn,
    TaxAssessmentIn,
    TaxProfileIn,
)
from app.domains.billing.service import create_draft, draft_dict, get_draft
from app.domains.billing.tax_assessment import assessment_dict, create_assessment, get_assessment
from app.domains.billing.tax_profile import create_profile, profile_dict, profile_on

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


@router.post("/service-tax-assessments", status_code=201)
def assess_service_tax(payload: TaxAssessmentIn, ctx: Context = Depends(context), db: Session = Depends(db_session)):
    row = create_assessment(db, ctx, payload)
    commit(db)
    return assessment_dict(row)


@router.get("/service-tax-assessments/{assessment_id}")
def read_service_tax(assessment_id: UUID, ctx: Context = Depends(context), db: Session = Depends(db_session)):
    return assessment_dict(get_assessment(db, ctx, assessment_id))


@router.post("/tax-profiles", status_code=201)
def declare_tax_profile(payload: TaxProfileIn, ctx: Context = Depends(context), db: Session = Depends(db_session)):
    profile = create_profile(db, ctx, payload)
    commit(db)
    return profile_dict(profile)


@router.get("/tax-profile")
def read_tax_profile(effective_on: date, ctx: Context = Depends(context), db: Session = Depends(db_session)):
    return {"effective_on": effective_on.isoformat(), "profile": profile_dict(profile_on(db, ctx, effective_on))}


@router.post("/service-obligation-previews")
def service_obligation_preview(
    payload: ServiceObligationPreviewIn,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    # POST carries a structured lookup, not a mutation. No commit or write audit.
    return preview_obligation(db, ctx, payload)


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


@router.post("/service-charges", status_code=201)
def post_service_charge(payload: ServiceChargeIn, ctx: Context = Depends(context), db: Session = Depends(db_session)):
    row = approve_charge(db, ctx, payload)
    commit(db)
    return charge_dict(db, row)


@router.get("/service-charges/{charge_id}")
def read_service_charge(charge_id: UUID, ctx: Context = Depends(context), db: Session = Depends(db_session)):
    return charge_dict(db, get_charge(db, ctx, charge_id=charge_id))


@router.get("/service-charge-requests/{request_id}")
def recover_service_charge(request_id: UUID, ctx: Context = Depends(context), db: Session = Depends(db_session)):
    return charge_dict(db, get_charge(db, ctx, request_id=request_id))
