"""Operator-declared service receipts; no verified bank or fiscal issuance."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.exceptions import ConflictError, NotFoundError
from app.core.idempotency import request_digest
from app.core.permissions import Context
from app.domains.accounting.models import Account
from app.domains.accounting.schemas import JournalIn
from app.domains.accounting.service import existing_request, lock_organization, write_entry
from app.domains.billing.charges import get_charge
from app.domains.billing.models import ServiceCharge, ServiceReceipt, TaxAssessment
from app.domains.billing.schemas import ServiceReceiptIn


def get_receipt(
    db: Session, ctx: Context, *, receipt_id: UUID | None = None, request_id: UUID | None = None
) -> ServiceReceipt:
    ctx.require("billing.receipts.read")
    ctx.require("billing.charges.read")
    criterion = (
        ServiceReceipt.id == receipt_id
        if receipt_id is not None else ServiceReceipt.request_id == request_id
    )
    row = db.scalar(
        select(ServiceReceipt).where(
            ServiceReceipt.organization_id == ctx.organization.id, criterion
        )
    )
    if row is None:
        raise NotFoundError()
    return row


def _original_amount(db: Session, charge: ServiceCharge) -> Decimal:
    amount = db.scalar(
        select(TaxAssessment.gross_amount).where(
            TaxAssessment.organization_id == charge.organization_id,
            TaxAssessment.id == charge.assessment_id,
        )
    )
    if amount is None:
        raise ConflictError()
    return amount


def _collected(db: Session, charge: ServiceCharge) -> Decimal:
    amount = db.scalar(
        select(func.sum(ServiceReceipt.amount)).where(
            ServiceReceipt.organization_id == charge.organization_id,
            ServiceReceipt.charge_id == charge.id,
        )
    )
    return amount if amount is not None else Decimal("0.00")


def charge_balance(db: Session, ctx: Context, charge_id: UUID) -> dict:
    ctx.require("billing.receipts.read")
    charge = get_charge(db, ctx, charge_id=charge_id)
    original = _original_amount(db, charge)
    received = _collected(db, charge)
    outstanding = original - received
    if outstanding < 0:
        raise ConflictError()
    status = (
        "UNPAID" if received == 0
        else "PAID" if outstanding == 0
        else "PARTIALLY_PAID"
    )
    return {
        "charge_id": str(charge.id),
        "customer_id": str(charge.customer_id),
        "organization_id": str(charge.organization_id),
        "currency": "SAR",
        "original_amount": format(original, ".2f"),
        "collected_amount": format(received, ".2f"),
        "outstanding_amount": format(outstanding, ".2f"),
        "payment_status": status,
        "collection_evidence": "OPERATOR_RECORDED",
        "external_payment_verified": False,
    }


def receipt_dict(row: ServiceReceipt) -> dict:
    return {
        "id": str(row.id), "organization_id": str(row.organization_id),
        "request_id": str(row.request_id), "charge_id": str(row.charge_id),
        "journal_id": str(row.journal_id), "settlement_account_id": str(row.settlement_account_id),
        "amount": format(row.amount, ".2f"), "currency": "SAR",
        "booking_date": row.booking_date.isoformat(),
        "payment_method": row.payment_method, "operator_reference": row.operator_reference,
        "recording_basis": row.recording_basis, "created_by": str(row.created_by),
        "created_at": row.created_at.isoformat(), "status": "OPERATOR_RECORDED",
        "external_payment_verified": False,
    }


def record_receipt(db: Session, ctx: Context, payload: ServiceReceiptIn) -> ServiceReceipt:
    for permission in (
        "billing.receipts.record", "billing.receipts.read", "billing.charges.read",
        "accounting.accounts.read", "accounting.journals.post",
    ):
        ctx.require(permission)
    lock_organization(db, ctx)
    digest = request_digest({
        "operation": "RECORD_INTERNAL_SERVICE_RECEIPT", **payload.model_dump(mode="json")
    })
    previous = db.scalar(
        select(ServiceReceipt).where(
            ServiceReceipt.organization_id == ctx.organization.id,
            ServiceReceipt.request_id == payload.request_id,
        )
    )
    if previous is not None:
        if previous.request_hash != digest:
            raise ConflictError()
        return previous
    # The journal UUID namespace also contains charges and ordinary journals.
    if existing_request(db, ctx, payload.request_id, digest) is not None:
        raise ConflictError()
    charge = get_charge(db, ctx, charge_id=payload.charge_id)
    if (
        ctx.organization.currency != "SAR"
        or payload.booking_date < charge.booking_date
        or payload.booking_date > datetime.now(ZoneInfo(ctx.organization.timezone)).date()
        or payload.settlement_account_id == charge.receivable_account_id
    ):
        raise ConflictError()
    account = db.scalar(
        select(Account).where(
            Account.organization_id == ctx.organization.id,
            Account.id == payload.settlement_account_id,
        )
    )
    if account is None:
        raise NotFoundError()
    if account.account_type != "ASSET" or not account.is_active or not account.is_postable:
        raise ConflictError()
    if _collected(db, charge) + payload.amount > _original_amount(db, charge):
        raise ConflictError()
    amount = format(payload.amount, ".2f")
    journal = write_entry(
        db, ctx,
        JournalIn.model_validate({
            "request_id": payload.request_id, "booking_date": payload.booking_date,
            "description": "Operator-declared internal service receipt",
            "lines": [
                {"account_id": payload.settlement_account_id, "debit": amount},
                {"account_id": charge.receivable_account_id, "credit": amount},
            ],
        }),
        digest,
    )
    receipt = ServiceReceipt(
        organization_id=ctx.organization.id,
        request_id=payload.request_id, request_hash=digest,
        charge_id=charge.id, journal_id=journal.id,
        settlement_account_id=payload.settlement_account_id,
        amount=payload.amount, booking_date=payload.booking_date,
        payment_method=payload.payment_method, operator_reference=payload.operator_reference,
        recording_basis=payload.recording_basis, created_by=ctx.user.id,
    )
    db.add(receipt)
    db.flush()
    record(
        db, "SERVICE_RECEIPT_RECORDED", "service_receipt", receipt.id,
        ctx.organization.id, ctx.user.id,
        after={"request_id": str(receipt.request_id),
               "charge_id": str(receipt.charge_id), "journal_id": str(receipt.journal_id)},
    )
    return receipt
