"""Explicit internal approval and atomic customer subledger/journal effect."""
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.exceptions import ConflictError, NotFoundError
from app.core.idempotency import request_digest
from app.core.permissions import Context
from app.domains.accounting.models import Account
from app.domains.accounting.schemas import JournalIn
from app.domains.accounting.service import existing_request, lock_organization, write_entry
from app.domains.billing.models import ServiceCharge, TaxAssessment
from app.domains.billing.schemas import ServiceChargeIn
from app.domains.billing.service import get_draft
from app.domains.billing.tax_assessment import get_assessment
from app.domains.billing.tax_profile import profile_on
from app.domains.customers.service import get_customer


def authorize_read(ctx: Context) -> None:
    ctx.require("billing.charges.read")


def get_charge(db: Session, ctx: Context, *, charge_id: UUID | None = None, request_id: UUID | None = None) -> ServiceCharge:
    authorize_read(ctx)
    criterion = ServiceCharge.id == charge_id if charge_id is not None else ServiceCharge.request_id == request_id
    row = db.scalar(select(ServiceCharge).where(ServiceCharge.organization_id == ctx.organization.id, criterion))
    if row is None:
        raise NotFoundError()
    return row


def charge_dict(db: Session, row: ServiceCharge) -> dict:
    assessment = db.scalar(select(TaxAssessment).where(
        TaxAssessment.organization_id == row.organization_id, TaxAssessment.id == row.assessment_id,
    ))
    assert assessment is not None  # Composite FK; immutable assessment.
    return {
        "id": str(row.id), "organization_id": str(row.organization_id),
        "request_id": str(row.request_id), "draft_id": str(row.draft_id),
        "assessment_id": str(row.assessment_id), "customer_id": str(row.customer_id),
        "journal_id": str(row.journal_id), "booking_date": row.booking_date.isoformat(),
        "receivable_account_id": str(row.receivable_account_id),
        "revenue_account_id": str(row.revenue_account_id), "tax_account_id": str(row.tax_account_id),
        "approval_basis": row.approval_basis, "created_by": str(row.created_by),
        "created_at": row.created_at.isoformat(), "currency": "SAR",
        "net_amount": format(assessment.net_amount, ".2f"),
        "tax_amount": format(assessment.tax_amount, ".2f"),
        "original_amount": format(assessment.gross_amount, ".2f"),
        "document_kind": "INTERNAL_SERVICE_CHARGE", "status": "POSTED",
        "can_issue_tax_invoice": False,
    }


def approve_charge(db: Session, ctx: Context, payload: ServiceChargeIn) -> ServiceCharge:
    ctx.require("billing.charges.approve")
    authorize_read(ctx)
    for permission in ("billing.drafts.read", "billing.tax.read", "customers.read",
                       "accounting.accounts.read", "accounting.journals.post"):
        ctx.require(permission)
    lock_organization(db, ctx)
    digest = request_digest({"operation": "APPROVE_INTERNAL_SERVICE_CHARGE", **payload.model_dump(mode="json")})
    old = db.scalar(select(ServiceCharge).where(
        ServiceCharge.organization_id == ctx.organization.id, ServiceCharge.request_id == payload.request_id,
    ))
    if old:
        if old.request_hash != digest:
            raise ConflictError()
        return old
    # UUID namespace is shared with journals; another operation must never be adopted.
    if existing_request(db, ctx, payload.request_id, digest) is not None:
        raise ConflictError()
    assessment = get_assessment(db, ctx, payload.assessment_id)
    draft = get_draft(db, ctx, assessment.draft_id)
    get_customer(db, ctx, payload.customer_id)
    if db.scalar(select(ServiceCharge.id).where(
        ServiceCharge.organization_id == ctx.organization.id, ServiceCharge.draft_id == draft.id,
    )) is not None:
        raise ConflictError()
    profile = profile_on(db, ctx, payload.booking_date)
    if (payload.booking_date != assessment.assessment_date
            or payload.booking_date > datetime.now(ZoneInfo(ctx.organization.timezone)).date()
            or profile is None or profile.id != assessment.profile_id
            or profile.registration_status != "REGISTERED"
            or draft.status != "DRAFT" or draft.currency != "SAR" or ctx.organization.currency != "SAR"
            or draft.amount_before_tax <= 0 or draft.amount_before_tax != assessment.net_amount):
        raise ConflictError()
    mappings = ((payload.receivable_account_id, "ASSET"),
                (payload.revenue_account_id, "REVENUE"), (payload.tax_account_id, "LIABILITY"))
    for account_id, kind in mappings:
        account = db.scalar(select(Account).where(Account.organization_id == ctx.organization.id, Account.id == account_id))
        if account is None:
            raise NotFoundError()
        if account.account_type != kind or not account.is_active or not account.is_postable:
            raise ConflictError()
    lines = [
        {"account_id": payload.receivable_account_id, "debit": format(assessment.gross_amount, ".2f")},
        {"account_id": payload.revenue_account_id, "credit": format(assessment.net_amount, ".2f")},
    ]
    if assessment.tax_amount > 0:
        lines.append({"account_id": payload.tax_account_id, "credit": format(assessment.tax_amount, ".2f")})
    journal = write_entry(db, ctx, JournalIn.model_validate({
        "request_id": payload.request_id, "booking_date": payload.booking_date,
        "description": "Internal service charge", "lines": lines,
    }), digest)
    row = ServiceCharge(
        organization_id=ctx.organization.id, request_id=payload.request_id, request_hash=digest,
        draft_id=draft.id, assessment_id=assessment.id, customer_id=payload.customer_id,
        journal_id=journal.id, receivable_account_id=payload.receivable_account_id,
        revenue_account_id=payload.revenue_account_id, tax_account_id=payload.tax_account_id,
        booking_date=payload.booking_date, approval_basis=payload.approval_basis, created_by=ctx.user.id,
    )
    db.add(row)
    db.flush()
    record(db, "SERVICE_CHARGE_POSTED", "service_charge", row.id, ctx.organization.id, ctx.user.id,
           after={"request_id": str(row.request_id), "draft_id": str(row.draft_id),
                  "assessment_id": str(row.assessment_id), "customer_id": str(row.customer_id),
                  "journal_id": str(row.journal_id)})
    return row
