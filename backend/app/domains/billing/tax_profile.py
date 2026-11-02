from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.exceptions import ConflictError
from app.core.idempotency import request_digest
from app.core.models import Organization
from app.core.permissions import Context
from app.domains.billing.models import TaxProfile
from app.domains.billing.schemas import TaxProfileIn


def profile_dict(profile: TaxProfile | None) -> dict | None:
    if profile is None:
        return None
    return {
        "id": str(profile.id), "organization_id": str(profile.organization_id),
        "request_id": str(profile.request_id), "effective_from": profile.effective_from.isoformat(),
        "registration_status": profile.registration_status, "vat_number": profile.vat_number,
        "verification_status": "OPERATOR_DECLARED", "can_issue_tax_invoice": False,
        "created_by": str(profile.created_by), "created_at": profile.created_at.isoformat(),
    }


def create_profile(db: Session, ctx: Context, payload: TaxProfileIn) -> TaxProfile:
    ctx.require("billing.tax.manage")
    db.scalar(select(Organization.id).where(Organization.id == ctx.organization.id).with_for_update())
    digest = request_digest({"operation": "DECLARE_TAX_PROFILE", **payload.model_dump(mode="json")})
    previous = db.scalar(select(TaxProfile).where(
        TaxProfile.organization_id == ctx.organization.id, TaxProfile.request_id == payload.request_id,
    ))
    if previous:
        if previous.request_hash != digest:
            raise ConflictError()
        return previous
    try:
        today = datetime.now(ZoneInfo(ctx.organization.timezone)).date()
    except ZoneInfoNotFoundError as exc:
        raise ConflictError() from exc
    latest = db.scalar(select(func.max(TaxProfile.effective_from)).where(
        TaxProfile.organization_id == ctx.organization.id,
    ))
    if payload.effective_from < today or (latest is not None and payload.effective_from <= latest):
        raise ConflictError()
    profile = TaxProfile(organization_id=ctx.organization.id, request_hash=digest,
                         created_by=ctx.user.id, **payload.model_dump())
    db.add(profile)
    db.flush()
    record(db, "TAX_PROFILE_DECLARED", "tax_profile", profile.id, ctx.organization.id, ctx.user.id,
           after={"request_id": str(profile.request_id), "effective_from": profile.effective_from.isoformat()})
    return profile


def profile_on(db: Session, ctx: Context, effective_on: date) -> TaxProfile | None:
    ctx.require("billing.tax.read")
    return db.scalar(select(TaxProfile).where(
        TaxProfile.organization_id == ctx.organization.id, TaxProfile.effective_from <= effective_on,
    ).order_by(TaxProfile.effective_from.desc()).limit(1))
