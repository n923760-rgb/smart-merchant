from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routes import commit
from app.api.schemas import page_of
from app.core.audit import record
from app.core.database import db_session
from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import Context, context
from app.domains.accounting.models import (
    Account,
    AccountingPeriod,
    JournalEntry,
    OpeningBalanceBatch,
)
from app.domains.accounting.schemas import (
    AccountIn,
    AccountingPeriodIn,
    JournalIn,
    OpeningBalanceIn,
    ReversalIn,
)
from app.domains.accounting.service import (
    authorize,
    journal_dict,
    lock_organization,
    post_initial_opening,
    post_journal,
    reverse_journal,
    scoped_entry,
)

router = APIRouter(prefix="/api/v1/accounting", tags=["accounting"])


def account_dict(account: Account) -> dict:
    return {
        "id": str(account.id),
        "organization_id": str(account.organization_id),
        "code": account.code,
        "name": account.name,
        "account_type": account.account_type,
        "is_active": account.is_active,
        "parent_id": str(account.parent_id) if account.parent_id else None,
        "is_postable": account.is_postable,
    }


@router.post("/accounts", status_code=201)
def create_account(
    payload: AccountIn, ctx: Context = Depends(context), db: Session = Depends(db_session)
):
    ctx.require("accounting.accounts.manage")
    if payload.parent_id is not None:
        parent = db.scalar(
            select(Account)
            .where(
                Account.id == payload.parent_id,
                Account.organization_id == ctx.organization.id,
            )
            .with_for_update(read=True)
        )
        if parent is None:
            raise NotFoundError()
        if (
            parent.is_postable
            or not parent.is_active
            or parent.account_type != payload.account_type
        ):
            raise ConflictError()
    account = Account(organization_id=ctx.organization.id, **payload.model_dump())
    db.add(account)
    # Use the existing commit conflict boundary for duplicate account codes.
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError() from exc
    record(
        db,
        "ACCOUNT_CREATED",
        "account",
        account.id,
        ctx.organization.id,
        ctx.user.id,
        after={"code": account.code, "account_type": account.account_type},
    )
    commit(db)
    return account_dict(account)


@router.get("/accounts")
def accounts(
    branch_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    authorize(db, ctx, "accounting.accounts.read", branch_id)
    rows = db.scalars(
        select(Account)
        .where(Account.organization_id == ctx.organization.id)
        .order_by(Account.code)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return page_of(rows, page, page_size, account_dict)



def period_dict(period: AccountingPeriod) -> dict:
    return {
        "id": str(period.id),
        "organization_id": str(period.organization_id),
        "start_date": period.start_date.isoformat(),
        "end_date": period.end_date.isoformat(),
        "status": period.status,
        "closed_at": period.closed_at.isoformat() if period.closed_at else None,
        "closed_by": str(period.closed_by) if period.closed_by else None,
    }


@router.get("/periods")
def periods(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    ctx.require("accounting.periods.read")
    rows = db.scalars(
        select(AccountingPeriod)
        .where(AccountingPeriod.organization_id == ctx.organization.id)
        .order_by(AccountingPeriod.start_date, AccountingPeriod.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return page_of(rows, page, page_size, period_dict)


@router.post("/periods", status_code=201)
def create_period(
    payload: AccountingPeriodIn,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    ctx.require("accounting.periods.manage")
    lock_organization(db, ctx)
    overlapping = db.scalar(
        select(AccountingPeriod.id).where(
            AccountingPeriod.organization_id == ctx.organization.id,
            AccountingPeriod.start_date <= payload.end_date,
            AccountingPeriod.end_date >= payload.start_date,
        )
    )
    if overlapping is not None:
        raise ConflictError()
    period = AccountingPeriod(
        organization_id=ctx.organization.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status="OPEN",
    )
    db.add(period)
    db.flush()
    record(
        db,
        "ACCOUNTING_PERIOD_CREATED",
        "accounting_period",
        period.id,
        ctx.organization.id,
        ctx.user.id,
        after={"start_date": period.start_date.isoformat(), "end_date": period.end_date.isoformat()},
    )
    commit(db)
    return period_dict(period)


@router.post("/periods/{period_id}/close")
def close_period(
    period_id: UUID,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    ctx.require("accounting.periods.manage")
    lock_organization(db, ctx)
    period = db.scalar(
        select(AccountingPeriod)
        .where(
            AccountingPeriod.id == period_id,
            AccountingPeriod.organization_id == ctx.organization.id,
        )
        .with_for_update()
    )
    if period is None:
        raise NotFoundError()
    if period.status != "OPEN":
        raise ConflictError()
    period.status = "CLOSED"
    period.closed_at = datetime.now(timezone.utc)
    period.closed_by = ctx.user.id
    record(
        db,
        "ACCOUNTING_PERIOD_CLOSED",
        "accounting_period",
        period.id,
        ctx.organization.id,
        ctx.user.id,
        before={"status": "OPEN"},
        after={"status": "CLOSED", "closed_at": period.closed_at.isoformat()},
    )
    commit(db)
    return period_dict(period)




def opening_dict(db: Session, batch: OpeningBalanceBatch, entry: JournalEntry) -> dict:
    return {
        "id": str(batch.id),
        "organization_id": str(batch.organization_id),
        "journal_id": str(batch.journal_id),
        "booking_date": batch.booking_date.isoformat(),
        "created_by": str(batch.created_by),
        "journal": journal_dict(db, entry),
    }


@router.get("/opening-balance")
def get_opening_balance(
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    ctx.require("accounting.opening.read")
    batch = db.scalar(
        select(OpeningBalanceBatch).where(
            OpeningBalanceBatch.organization_id == ctx.organization.id
        )
    )
    if batch is None:
        raise NotFoundError()
    entry = db.scalar(
        select(JournalEntry).where(
            JournalEntry.id == batch.journal_id,
            JournalEntry.organization_id == ctx.organization.id,
        )
    )
    if entry is None:
        raise NotFoundError()
    return opening_dict(db, batch, entry)


@router.post("/opening-balance", status_code=201)
def create_opening_balance(
    payload: OpeningBalanceIn,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    batch, entry = post_initial_opening(db, ctx, payload)
    commit(db)
    return opening_dict(db, batch, entry)


@router.post("/journals", status_code=201)
def create_journal(
    payload: JournalIn, ctx: Context = Depends(context), db: Session = Depends(db_session)
):
    entry = post_journal(db, ctx, payload)
    commit(db)
    return journal_dict(db, entry)


@router.get("/journals")
def journals(
    branch_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    authorize(db, ctx, "accounting.journals.read", branch_id)
    stmt = select(JournalEntry).where(JournalEntry.organization_id == ctx.organization.id)
    if branch_id is not None:
        stmt = stmt.where(JournalEntry.branch_id == branch_id)
    rows = db.scalars(
        stmt.order_by(JournalEntry.booking_date, JournalEntry.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return page_of(rows, page, page_size, lambda entry: journal_dict(db, entry))


@router.get("/journals/{entry_id}")
def get_journal(entry_id: UUID, ctx: Context = Depends(context), db: Session = Depends(db_session)):
    return journal_dict(db, scoped_entry(db, ctx, entry_id, "accounting.journals.read"))


@router.get("/journal-requests/{request_id}")
def journal_request(
    request_id: UUID,
    branch_id: UUID | None = None,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    # Keep lookup under the existing ledger read grant; posting is not a read grant.
    # Authorize the requested scope before even checking whether an ID exists.
    authorize(db, ctx, "accounting.journals.read", branch_id)
    entry = db.scalar(
        select(JournalEntry).where(
            JournalEntry.organization_id == ctx.organization.id,
            JournalEntry.request_id == request_id,
            JournalEntry.branch_id == branch_id,
        )
    )
    if entry is None:
        # Absence is an observation, not proof an in-flight write cannot commit.
        raise NotFoundError()
    return journal_dict(db, entry)


@router.post("/journals/{entry_id}/reverse", status_code=201)
def reversal(
    entry_id: UUID,
    payload: ReversalIn,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    entry = reverse_journal(db, ctx, entry_id, payload)
    commit(db)
    return journal_dict(db, entry)
