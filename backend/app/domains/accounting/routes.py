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
from app.domains.accounting.models import Account, JournalEntry
from app.domains.accounting.schemas import AccountIn, JournalIn, ReversalIn
from app.domains.accounting.service import (
    authorize,
    journal_dict,
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
    }


@router.post("/accounts", status_code=201)
def create_account(
    payload: AccountIn, ctx: Context = Depends(context), db: Session = Depends(db_session)
):
    ctx.require("accounting.accounts.manage")
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
