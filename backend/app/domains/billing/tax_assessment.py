from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.exceptions import ConflictError, NotFoundError
from app.core.idempotency import request_digest
from app.core.models import Organization
from app.core.permissions import Context
from app.domains.billing.models import ServiceDraftLine, TaxAssessment
from app.domains.billing.schemas import TaxAssessmentIn
from app.domains.billing.service import get_draft
from app.domains.billing.tax_calculation import calculate_standard_vat
from app.domains.billing.tax_profile import profile_on


def assessment_dict(row: TaxAssessment) -> dict:
    return {
        "id": str(row.id), "organization_id": str(row.organization_id),
        "request_id": str(row.request_id), "draft_id": str(row.draft_id),
        "profile_id": str(row.profile_id), "assessment_date": row.assessment_date.isoformat(),
        "category": "STANDARD_15", "classification_basis": row.classification_basis,
        "net_amount": format(row.net_amount, ".2f"), "tax_amount": format(row.tax_amount, ".2f"),
        "gross_amount": format(row.gross_amount, ".2f"), "currency": "SAR",
        "tax_status": "OPERATOR_ASSESSED", "approval_status": "NOT_APPROVED",
        "can_post": False, "can_issue_tax_invoice": False, "amount_due": None,
        "created_by": str(row.created_by), "created_at": row.created_at.isoformat(),
    }


def authorize_read(ctx: Context) -> None:
    ctx.require("billing.tax.read")
    ctx.require("billing.drafts.read")


def create_assessment(db: Session, ctx: Context, payload: TaxAssessmentIn) -> TaxAssessment:
    ctx.require("billing.tax.manage")
    authorize_read(ctx)
    db.scalar(select(Organization.id).where(Organization.id == ctx.organization.id).with_for_update())
    digest = request_digest({"operation": "ASSESS_STANDARD_SERVICE_TAX", **payload.model_dump(mode="json")})
    old = db.scalar(select(TaxAssessment).where(
        TaxAssessment.organization_id == ctx.organization.id, TaxAssessment.request_id == payload.request_id,
    ))
    if old:
        if old.request_hash != digest:
            raise ConflictError()
        return old
    draft = get_draft(db, ctx, payload.draft_id)
    profile = profile_on(db, ctx, payload.assessment_date)
    if (profile is None or profile.registration_status != "REGISTERED" or draft.status != "DRAFT"
            or draft.currency != "SAR" or ctx.organization.currency != "SAR" or draft.amount_before_tax <= 0):
        raise ConflictError()
    lines = db.scalars(select(ServiceDraftLine).where(
        ServiceDraftLine.organization_id == ctx.organization.id, ServiceDraftLine.draft_id == draft.id,
    ).order_by(ServiceDraftLine.line_number)).all()
    try:
        totals = calculate_standard_vat([format(line.line_total, ".2f") for line in lines])
    except ValueError as exc:
        raise ConflictError() from exc
    row = TaxAssessment(
        organization_id=ctx.organization.id, request_id=payload.request_id, request_hash=digest,
        draft_id=draft.id, profile_id=profile.id, assessment_date=payload.assessment_date,
        classification_basis=payload.classification_basis, net_amount=totals.taxable_amount,
        tax_amount=totals.tax_amount, gross_amount=totals.gross_amount, created_by=ctx.user.id,
    )
    db.add(row)
    db.flush()
    record(db, "SERVICE_TAX_ASSESSED", "tax_assessment", row.id, ctx.organization.id, ctx.user.id,
           after={"request_id": str(row.request_id), "draft_id": str(draft.id), "profile_id": str(profile.id)})
    return row


def get_assessment(db: Session, ctx: Context, assessment_id: UUID) -> TaxAssessment:
    authorize_read(ctx)
    row = db.scalar(select(TaxAssessment).where(
        TaxAssessment.organization_id == ctx.organization.id, TaxAssessment.id == assessment_id,
    ))
    if row is None:
        raise NotFoundError()
    return row
