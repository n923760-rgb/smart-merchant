"""Read-only qualification: pre-tax allocations are not a posted receivable."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import Context
from app.domains.accounting.models import Account, AccountingPeriod, OpeningBalanceBatch
from app.domains.billing.schemas import ServiceObligationPreviewIn
from app.domains.billing.service import get_draft
from app.domains.customers.service import get_customer


def preview_obligation(
    db: Session, ctx: Context, payload: ServiceObligationPreviewIn
) -> dict:
    # All are organization-wide reads. A branch-only grant is insufficient
    # even if another required permission is granted globally.
    for permission in (
        "billing.drafts.read", "customers.read", "accounting.accounts.read",
        "accounting.periods.read", "accounting.opening.read",
    ):
        ctx.require(permission)
    draft = get_draft(db, ctx, payload.draft_id)
    customer = get_customer(db, ctx, payload.customer_id)
    accounts = db.scalars(select(Account).where(
        Account.organization_id == ctx.organization.id,
        Account.id.in_({payload.receivable_account_id, payload.revenue_account_id}),
    )).all()
    by_id = {account.id: account for account in accounts}
    for account_id in (payload.receivable_account_id, payload.revenue_account_id):
        if account_id not in by_id:
            raise NotFoundError()
    ar, revenue = by_id[payload.receivable_account_id], by_id[payload.revenue_account_id]
    if (
        ar.account_type != "ASSET" or revenue.account_type != "REVENUE"
        or any(not a.is_active or not a.is_postable for a in (ar, revenue))
        or draft.status != "DRAFT" or draft.amount_before_tax <= 0
        or draft.currency != "SAR" or ctx.organization.currency != "SAR"
    ):
        raise ConflictError()

    blockers = [
        "TAX_POLICY_UNQUALIFIED",
        "FINANCIAL_APPROVAL_REQUIRED",
        "POSTING_NOT_IMPLEMENTED",
    ]
    closed = db.scalar(select(AccountingPeriod.id).where(
        AccountingPeriod.organization_id == ctx.organization.id,
        AccountingPeriod.start_date <= payload.booking_date,
        AccountingPeriod.end_date >= payload.booking_date,
        AccountingPeriod.status == "CLOSED",
    ))
    if closed is not None:
        blockers.append("ACCOUNTING_PERIOD_CLOSED")
    cutover = db.scalar(select(OpeningBalanceBatch.booking_date).where(
        OpeningBalanceBatch.organization_id == ctx.organization.id,
    ))
    if cutover is not None and payload.booking_date <= cutover:
        blockers.append("ON_OR_BEFORE_OPENING_CUTOVER")

    amount = format(draft.amount_before_tax, ".2f")
    # No JournalIn/request_id/journal_id is returned: this is not a payload for
    # the generic posting endpoint, nor a reusable approval capability.
    return {
        "document_kind": "INTERNAL_SERVICE_OBLIGATION_PREVIEW",
        "organization_id": str(ctx.organization.id),
        "draft_id": str(draft.id),
        "selected_customer": {
            "id": str(customer.id), "display_name": customer.display_name,
            "identity_status": "OPERATOR_CREATED",
        },
        "draft_customer_snapshot": {
            "name": draft.customer_name, "email": draft.customer_email,
        },
        "booking_date": payload.booking_date.isoformat(),
        "branch_id": None,
        "currency": "SAR",
        "amount_before_tax": amount,
        "tax_status": "NOT_EVALUATED",
        "tax_total": None,
        "amount_due": None,
        "can_post": False,
        "approval_status": "NOT_APPROVED",
        "blocking_reasons": blockers,
        "pre_tax_allocation": [
            {"account_id": str(ar.id), "side": "DEBIT", "amount": amount},
            {"account_id": str(revenue.id), "side": "CREDIT", "amount": amount},
        ],
    }
