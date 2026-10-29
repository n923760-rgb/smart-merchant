from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.idempotency import request_digest
from app.core.models import AuditLog, Organization
from app.core.permissions import Context, scoped_branch
from app.domains.accounting.models import (
    Account,
    AccountingPeriod,
    JournalEntry,
    JournalLine,
    OpeningBalanceBatch,
)
from app.domains.accounting.schemas import JournalIn, OpeningBalanceIn, ReversalIn


def authorize(
    db: Session, ctx: Context, permission: str, branch_id: UUID | None, *, active: bool = False
) -> None:
    if branch_id is None:
        ctx.require(permission)
    else:
        branch = scoped_branch(db, ctx, branch_id, permission)
        if active and branch.status != "ACTIVE":
            raise ConflictError()


def journal_digest(payload: JournalIn) -> str:
    data = payload.model_dump(mode="json")
    for row, line in zip(data["lines"], payload.lines, strict=True):
        row["debit"] = format(line.debit, ".2f")
        row["credit"] = format(line.credit, ".2f")
    return request_digest({"operation": "POST_JOURNAL", **data})


def journal_dict(db: Session, entry: JournalEntry) -> dict:
    lines = db.scalars(
        select(JournalLine)
        .where(
            JournalLine.entry_id == entry.id, JournalLine.organization_id == entry.organization_id
        )
        .order_by(JournalLine.line_number)
    ).all()
    return {
        "id": str(entry.id),
        "organization_id": str(entry.organization_id),
        "branch_id": str(entry.branch_id) if entry.branch_id else None,
        "request_id": str(entry.request_id),
        "booking_date": entry.booking_date.isoformat(),
        "description": entry.description,
        "currency": entry.currency,
        "status": entry.status,
        "reversal_of_id": str(entry.reversal_of_id) if entry.reversal_of_id else None,
        "posted_by": str(entry.posted_by),
        "posted_at": entry.posted_at.isoformat() if entry.posted_at else None,
        "total_debit": format(sum((line.debit for line in lines), Decimal("0")), ".2f"),
        "total_credit": format(sum((line.credit for line in lines), Decimal("0")), ".2f"),
        "lines": [
            {
                "account_id": str(line.account_id),
                "line_number": line.line_number,
                "debit": format(line.debit, ".2f"),
                "credit": format(line.credit, ".2f"),
                "description": line.description,
            }
            for line in lines
        ],
    }


def scoped_entry(db: Session, ctx: Context, entry_id: UUID, permission: str) -> JournalEntry:
    entry = db.scalar(
        select(JournalEntry).where(
            JournalEntry.id == entry_id, JournalEntry.organization_id == ctx.organization.id
        )
    )
    if entry is None:
        raise NotFoundError()
    authorize(db, ctx, permission, entry.branch_id)
    return entry


def lock_organization(db: Session, ctx: Context) -> None:
    # Serialize this initial low-volume journal command across workers, including
    # first insertion of a request ID. This is not a Redis/expiring replay guard.
    db.scalar(
        select(Organization.id).where(Organization.id == ctx.organization.id).with_for_update()
    )


def existing_request(
    db: Session, ctx: Context, request_id: UUID, digest: str
) -> JournalEntry | None:
    entry = db.scalar(
        select(JournalEntry).where(
            JournalEntry.organization_id == ctx.organization.id,
            JournalEntry.request_id == request_id,
        )
    )
    if entry is None:
        return None
    # Recheck permissions against the original entry before returning its data.
    authorize(db, ctx, "accounting.journals.post", entry.branch_id)
    if entry.request_hash != digest:
        raise ConflictError()
    return entry


def write_entry(
    db: Session,
    ctx: Context,
    payload: JournalIn,
    digest: str,
    *,
    reversal_of: JournalEntry | None = None,
) -> JournalEntry:
    ids = {line.account_id for line in payload.lines}
    accounts = db.scalars(
        select(Account).where(Account.organization_id == ctx.organization.id, Account.id.in_(ids))
    ).all()
    if len(accounts) != len(ids):
        raise NotFoundError()
    # A summary account is never a posting target, including reversal commands.
    # All historic accounts were migrated as postable roots, so valid reversals remain available.
    if any(not account.is_postable for account in accounts):
        raise ConflictError()
    if reversal_of is None and any(not account.is_active for account in accounts):
        raise ConflictError()
    # Only new journal effects are subject to the closing barrier; existing
    # same-request replays return their historical result without another write.
    if db.scalar(
        select(AccountingPeriod.id).where(
            AccountingPeriod.organization_id == ctx.organization.id,
            AccountingPeriod.start_date <= payload.booking_date,
            AccountingPeriod.end_date >= payload.booking_date,
            AccountingPeriod.status == "CLOSED",
        )
    ) is not None:
        raise ConflictError()
    cutoff = db.scalar(
        select(OpeningBalanceBatch.booking_date).where(
            OpeningBalanceBatch.organization_id == ctx.organization.id,
        )
    )
    if cutoff is not None and payload.booking_date <= cutoff:
        raise ConflictError()
    if ctx.organization.currency != "SAR":
        # The initial ledger qualifies SAR (two-decimal amounts), not every currency.
        raise ConflictError()
    entry = JournalEntry(
        organization_id=ctx.organization.id,
        branch_id=payload.branch_id,
        request_id=payload.request_id,
        request_hash=digest,
        booking_date=payload.booking_date,
        description=payload.description,
        currency=ctx.organization.currency,
        status="DRAFT",
        reversal_of_id=reversal_of.id if reversal_of else None,
        posted_by=ctx.user.id,
    )
    db.add(entry)
    db.flush()
    for number, line in enumerate(payload.lines, start=1):
        db.add(
            JournalLine(
                organization_id=ctx.organization.id,
                entry_id=entry.id,
                line_number=number,
                **line.model_dump(),
            )
        )
    db.flush()
    entry.status = "POSTED"
    entry.posted_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            organization_id=ctx.organization.id,
            branch_id=entry.branch_id,
            user_id=ctx.user.id,
            action="JOURNAL_REVERSED" if reversal_of else "JOURNAL_POSTED",
            entity_type="journal_entry",
            entity_id=entry.id,
            after_data={
                "status": "POSTED",
                "reversal_of_id": str(reversal_of.id) if reversal_of else None,
                "request_id": str(payload.request_id),
            },
        )
    )
    db.flush()
    return entry


def post_journal(db: Session, ctx: Context, payload: JournalIn) -> JournalEntry:
    authorize(db, ctx, "accounting.journals.post", payload.branch_id, active=True)
    lock_organization(db, ctx)
    digest = journal_digest(payload)
    original = existing_request(db, ctx, payload.request_id, digest)
    return original or write_entry(db, ctx, payload, digest)


def reverse_journal(db: Session, ctx: Context, entry_id: UUID, payload: ReversalIn) -> JournalEntry:
    original = scoped_entry(db, ctx, entry_id, "accounting.journals.reverse")
    authorize(db, ctx, "accounting.journals.post", original.branch_id)
    lock_organization(db, ctx)
    digest = request_digest(
        {
            "operation": "REVERSE_JOURNAL",
            "entry_id": str(entry_id),
            **payload.model_dump(mode="json"),
        }
    )
    replay = existing_request(db, ctx, payload.request_id, digest)
    if replay:
        return replay
    if db.scalar(
        select(OpeningBalanceBatch.id).where(
            OpeningBalanceBatch.organization_id == ctx.organization.id,
            OpeningBalanceBatch.journal_id == entry_id,
        )
    ) is not None:
        raise ConflictError()
    if original.reversal_of_id is not None or db.scalar(
        select(JournalEntry.id).where(
            JournalEntry.organization_id == ctx.organization.id,
            JournalEntry.reversal_of_id == entry_id,
        )
    ):
        raise ConflictError()
    lines = db.scalars(
        select(JournalLine)
        .where(JournalLine.entry_id == entry_id, JournalLine.organization_id == ctx.organization.id)
        .order_by(JournalLine.line_number)
    ).all()
    reversal = JournalIn.model_validate(
        {
            "request_id": payload.request_id,
            "branch_id": original.branch_id,
            "booking_date": payload.booking_date,
            "description": payload.reason,
            "lines": [
                {
                    "account_id": line.account_id,
                    "debit": format(line.credit, ".2f"),
                    "credit": format(line.debit, ".2f"),
                    "description": line.description,
                }
                for line in lines
            ],
        }
    )
    return write_entry(db, ctx, reversal, digest, reversal_of=original)


def post_initial_opening(
    db: Session, ctx: Context, payload: OpeningBalanceIn
) -> tuple[OpeningBalanceBatch, JournalEntry]:
    # Initial cutover is a global owner action; ordinary branch posting rights
    # must not authorize an organization's opening balances.
    ctx.require("accounting.opening.manage")
    ctx.require("accounting.journals.post")
    lock_organization(db, ctx)

    entry_payload = JournalIn.model_validate(
        {
            "request_id": payload.request_id,
            "booking_date": payload.booking_date,
            "branch_id": None,
            "description": payload.description,
            "lines": [line.model_dump(mode="json") for line in payload.lines],
        }
    )
    digest = request_digest({
        "operation": "INITIAL_OPENING_BALANCE",
        "journal_digest": journal_digest(entry_payload),
    })
    old = existing_request(db, ctx, payload.request_id, digest)
    if old is not None:
        previous = db.scalar(
            select(OpeningBalanceBatch).where(
                OpeningBalanceBatch.organization_id == ctx.organization.id,
                OpeningBalanceBatch.journal_id == old.id,
            )
        )
        if previous is None:
            raise ConflictError()
        return previous, old

    if db.scalar(
        select(OpeningBalanceBatch.id).where(
            OpeningBalanceBatch.organization_id == ctx.organization.id
        )
    ) is not None:
        raise ConflictError()

    # A cutover can be initialized after later-dated ordinary journals, but it
    # may never overwrite or reclassify transactions on or before its date.
    if db.scalar(
        select(JournalEntry.id).where(
            JournalEntry.organization_id == ctx.organization.id,
            JournalEntry.status == "POSTED",
            JournalEntry.booking_date <= payload.booking_date,
        )
    ) is not None:
        raise ConflictError()

    entry = write_entry(db, ctx, entry_payload, digest)
    db.flush()
    batch = OpeningBalanceBatch(
        organization_id=ctx.organization.id,
        journal_id=entry.id,
        booking_date=payload.booking_date,
        created_by=ctx.user.id,
    )
    db.add(batch)
    db.add(
        AuditLog(
            organization_id=ctx.organization.id,
            branch_id=None,
            user_id=ctx.user.id,
            action="INITIAL_OPENING_BALANCE_POSTED",
            entity_type="opening_balance",
            entity_id=batch.id,
            after_data={
                "journal_id": str(entry.id),
                "booking_date": payload.booking_date.isoformat(),
                "request_id": str(payload.request_id),
            },
        )
    )
    db.flush()
    return batch, entry
