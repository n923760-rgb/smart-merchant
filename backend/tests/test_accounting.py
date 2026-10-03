"""Disposable PostgreSQL API and database invariants for the general ledger."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.models import AuditLog, Branch, Membership, Terminal, User
from app.domains.accounting.models import Account, JournalEntry, JournalLine

BASE = "/api/v1/accounting"
PASSWORD = "accounting-disposable-password-123"


def new_accounts(client, headers):
    ids = []
    for code, name, kind in [("1000", "Cash", "ASSET"), ("4000", "Service revenue", "REVENUE")]:
        result = client.post(
            BASE + "/accounts",
            headers=headers,
            json={"code": code, "name": name, "account_type": kind},
        )
        assert result.status_code == 201, result.text
        ids.append(result.json()["id"])
    return ids


def journal_payload(ids, *, branch_id=None, amount="100.00"):
    return {
        "request_id": str(uuid4()),
        "booking_date": "2026-10-03",
        "description": "Service revenue",
        "branch_id": branch_id,
        "lines": [
            {"account_id": ids[0], "debit": amount},
            {"account_id": ids[1], "credit": amount},
        ],
    }


def post(client, headers, payload):
    result = client.post(BASE + "/journals", headers=headers, json=payload)
    assert result.status_code == 201, result.text
    return result.json()


def employee(client, merchant, *, role_code="ACCOUNTANT", branch_id=None):
    headers = merchant["headers"]
    email = f"ledger-{uuid4()}@example.com"
    result = client.post(
        "/api/v1/users",
        headers=headers,
        json={"name": role_code, "email": email, "password": PASSWORD},
    )
    assert result.status_code == 201, result.text
    roles = client.get("/api/v1/roles", headers=headers, params={"page_size": 100}).json()["items"]
    role = next(r for r in roles if r["code"] == role_code)
    result = client.post(
        f"/api/v1/users/{result.json()['id']}/roles",
        headers=headers,
        json={"role_id": role["id"], "branch_id": branch_id},
    )
    assert result.status_code == 201, result.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Organization-ID": merchant["org"],
    }


def new_branch(client, headers, code):
    result = client.post("/api/v1/branches", headers=headers, json={"code": code, "name": code})
    assert result.status_code == 201, result.text
    return result.json()["id"]


def test_services_accounting_has_no_pos_dependency_and_posts_once(client, merchant):
    headers = merchant["headers"]
    ids = new_accounts(client, headers)
    payload = journal_payload(ids)
    first = post(client, headers, payload)
    assert first["total_debit"] == first["total_credit"] == "100.00"
    assert first["status"] == "POSTED" and first["branch_id"] is None
    assert first["currency"] == "SAR"
    assert post(client, headers, payload) == first
    payload["lines"][0]["debit"] = "100"
    assert post(client, headers, payload) == first
    payload["description"] = "Collision"
    assert client.post(BASE + "/journals", headers=headers, json=payload).status_code == 409
    with SessionLocal() as db:
        org = UUID(merchant["org"])
        assert (
            db.scalar(
                select(func.count())
                .select_from(JournalEntry)
                .where(JournalEntry.organization_id == org)
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count()).select_from(Terminal).where(Terminal.organization_id == org)
            )
            == 0
        )
        assert (
            db.scalar(select(func.count()).select_from(Branch).where(Branch.organization_id == org))
            == 0
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.organization_id == org, AuditLog.action == "JOURNAL_POSTED")
            )
            == 1
        )


def test_invalid_journal_leaves_no_financial_or_audit_state(client, merchant):
    headers = merchant["headers"]
    payload = journal_payload(new_accounts(client, headers))
    payload["lines"][1]["credit"] = "99.99"
    assert client.post(BASE + "/journals", headers=headers, json=payload).status_code == 422
    with SessionLocal() as db:
        assert not db.scalar(
            select(JournalEntry.id).where(JournalEntry.organization_id == UUID(merchant["org"]))
        )
        assert not db.scalar(
            select(AuditLog.id).where(
                AuditLog.organization_id == UUID(merchant["org"]),
                AuditLog.action == "JOURNAL_POSTED",
            )
        )


def test_cashier_cannot_post_or_create_accounts(client, merchant):
    ids = new_accounts(client, merchant["headers"])
    cashier = employee(client, merchant, role_code="CASHIER")
    assert (
        client.post(BASE + "/journals", headers=cashier, json=journal_payload(ids)).status_code
        == 403
    )
    assert (
        client.post(
            BASE + "/accounts",
            headers=cashier,
            json={"code": "5000", "name": "Expense", "account_type": "EXPENSE"},
        ).status_code
        == 403
    )


def test_accountant_posts_without_device_management(client, merchant):
    ids = new_accounts(client, merchant["headers"])
    accountant = employee(client, merchant)
    entry = post(client, accountant, journal_payload(ids))
    assert client.get(BASE + f"/journals/{entry['id']}", headers=accountant).status_code == 200
    assert client.get("/api/v1/terminals", headers=accountant).status_code == 403


def test_branch_permissions_do_not_leak_unscoped_or_other_branch_journals(client, merchant):
    headers = merchant["headers"]
    ids = new_accounts(client, headers)
    b1, b2 = new_branch(client, headers, "B1"), new_branch(client, headers, "B2")
    restricted = employee(client, merchant, branch_id=b1)
    own = post(client, restricted, journal_payload(ids, branch_id=b1))
    other = post(client, headers, journal_payload(ids, branch_id=b2))
    unscoped = post(client, headers, journal_payload(ids))
    assert (
        client.post(
            BASE + "/journals", headers=restricted, json=journal_payload(ids, branch_id=b2)
        ).status_code
        == 403
    )
    assert (
        client.post(BASE + "/journals", headers=restricted, json=journal_payload(ids)).status_code
        == 403
    )
    assert client.get(BASE + "/journals", headers=restricted).status_code == 403
    for entry in [other, unscoped]:
        assert client.get(BASE + f"/journals/{entry['id']}", headers=restricted).status_code == 403
    listing = client.get(BASE + "/journals", headers=restricted, params={"branch_id": b1})
    assert [r["id"] for r in listing.json()["items"]] == [own["id"]]
    assert (
        client.get(BASE + "/accounts", headers=restricted, params={"branch_id": b1}).status_code
        == 200
    )
    assert (
        client.post(
            BASE + "/accounts",
            headers=restricted,
            json={"code": "5000", "name": "Expense", "account_type": "EXPENSE"},
        ).status_code
        == 403
    )


def test_foreign_accounts_branches_and_journals_are_not_found(client, merchant):
    from app.core.config import get_settings

    email = f"other-ledger-owner-{uuid4()}@example.com"
    org = client.post(
        "/api/v1/bootstrap",
        headers={"X-Bootstrap-Key": get_settings().bootstrap_key},
        json={
            "owner_name": "Other",
            "owner_email": email,
            "owner_password": PASSWORD,
            "organization_name": "Other",
        },
    )
    assert org.status_code == 201, org.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    other = {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Organization-ID": org.json()["organization"]["id"],
    }
    foreign = new_accounts(client, other)
    entry = post(client, other, journal_payload(foreign))
    own = new_accounts(client, merchant["headers"])
    payload = journal_payload([own[0], foreign[1]])
    assert (
        client.post(BASE + "/journals", headers=merchant["headers"], json=payload).status_code
        == 404
    )
    payload = journal_payload(own, branch_id=new_branch(client, other, "FOREIGN"))
    assert (
        client.post(BASE + "/journals", headers=merchant["headers"], json=payload).status_code
        == 404
    )
    assert (
        client.get(BASE + f"/journals/{entry['id']}", headers=merchant["headers"]).status_code
        == 404
    )
    assert (
        client.post(
            BASE + f"/journals/{entry['id']}/reverse",
            headers=merchant["headers"],
            json={"request_id": str(uuid4()), "booking_date": "2026-10-03", "reason": "Correct"},
        ).status_code
        == 404
    )
    listing = client.get(BASE + "/accounts", headers=merchant["headers"]).json()["items"]
    assert {row["id"] for row in listing} == set(own)


def test_reversal_is_exact_idempotent_and_preserves_original(client, merchant):
    headers = merchant["headers"]
    original = post(client, headers, journal_payload(new_accounts(client, headers)))
    body = {
        "request_id": str(uuid4()),
        "booking_date": "2026-10-03",
        "reason": "Correct wrong entry",
    }
    endpoint = BASE + f"/journals/{original['id']}/reverse"
    result = client.post(endpoint, headers=headers, json=body)
    assert result.status_code == 201, result.text
    reversal = result.json()
    assert reversal["reversal_of_id"] == original["id"]
    for old, new in zip(original["lines"], reversal["lines"], strict=True):
        assert old["account_id"] == new["account_id"]
        assert old["debit"] == new["credit"] and old["credit"] == new["debit"]
    assert client.post(endpoint, headers=headers, json=body).json() == reversal
    body["request_id"] = str(uuid4())
    assert client.post(endpoint, headers=headers, json=body).status_code == 409
    assert client.get(BASE + f"/journals/{original['id']}", headers=headers).json() == original


@pytest.mark.parametrize(
    "mutation", ["header_update", "header_delete", "line_update", "line_delete", "line_insert"]
)
def test_database_freezes_posted_records(client, merchant, mutation):
    headers = merchant["headers"]
    original = post(client, headers, journal_payload(new_accounts(client, headers)))
    with SessionLocal() as db:
        params = {
            "id": UUID(original["id"]),
            "org": UUID(merchant["org"]),
            "account": UUID(original["lines"][0]["account_id"]),
            "new": uuid4(),
        }
        sql = {
            "header_update": "UPDATE journal_entries SET description = 'Changed' WHERE id = :id",
            "header_delete": "DELETE FROM journal_entries WHERE id = :id",
            "line_update": "UPDATE journal_lines SET description = 'Changed' WHERE entry_id = :id",
            "line_delete": "DELETE FROM journal_lines WHERE entry_id = :id",
            "line_insert": """INSERT INTO journal_lines
                (id, organization_id, entry_id, account_id, line_number, debit, credit)
                VALUES (:new, :org, :id, :account, 3, 1, 0)""",
        }[mutation]
        with pytest.raises(DBAPIError):
            db.execute(text(sql), params)
            db.commit()
        db.rollback()
    assert client.get(BASE + f"/journals/{original['id']}", headers=headers).json() == original


def test_database_rejects_unbalanced_or_unfinished_commit(client, merchant):
    headers = merchant["headers"]
    ids = new_accounts(client, headers)
    actor = client.get("/api/v1/auth/me", headers=headers).json()["id"]
    for unfinished in (False, True):
        with SessionLocal() as db:
            entry = JournalEntry(
                organization_id=UUID(merchant["org"]),
                request_id=uuid4(),
                request_hash="a" * 64,
                booking_date=date(2026, 10, 3),
                description="Invalid direct database operation",
                currency="SAR",
                status="DRAFT",
                posted_by=UUID(actor),
            )
            db.add(entry)
            db.flush()
            db.add_all(
                [
                    JournalLine(
                        organization_id=entry.organization_id,
                        entry_id=entry.id,
                        account_id=UUID(ids[0]),
                        line_number=1,
                        debit=100,
                        credit=0,
                    ),
                    JournalLine(
                        organization_id=entry.organization_id,
                        entry_id=entry.id,
                        account_id=UUID(ids[1]),
                        line_number=2,
                        debit=0,
                        credit=99,
                    ),
                ]
            )
            db.flush()
            if not unfinished:
                entry.status = "POSTED"
                entry.posted_at = datetime.now(timezone.utc)
            with pytest.raises(DBAPIError):
                db.commit()
            db.rollback()


def test_concurrent_replay_and_reversal_create_one_effect(client, merchant):
    headers = merchant["headers"]
    payload = journal_payload(new_accounts(client, headers))
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(
            workers.map(
                lambda _: client.post(BASE + "/journals", headers=headers, json=payload), range(2)
            )
        )
    assert [r.status_code for r in results] == [201, 201]
    assert results[0].json()["id"] == results[1].json()["id"]
    original = results[0].json()
    endpoint = BASE + f"/journals/{original['id']}/reverse"
    bodies = [
        {"request_id": str(uuid4()), "booking_date": "2026-10-03", "reason": "Reverse"}
        for _ in range(2)
    ]
    with ThreadPoolExecutor(max_workers=2) as workers:
        reversals = list(
            workers.map(lambda b: client.post(endpoint, headers=headers, json=b), bodies)
        )
    assert sorted(r.status_code for r in reversals) == [201, 409]
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(JournalEntry)
                .where(JournalEntry.organization_id == UUID(merchant["org"]))
            )
            == 2
        )


def test_audit_failure_rolls_back_journal_and_lines(client, merchant):
    headers = merchant["headers"]
    payload = journal_payload(new_accounts(client, headers))

    def fail_audit(session, flush_context, instances):
        if any(isinstance(row, AuditLog) and row.action == "JOURNAL_POSTED" for row in session.new):
            raise RuntimeError("Injected disposable audit failure")

    event.listen(Session, "before_flush", fail_audit)
    try:
        with pytest.raises(RuntimeError):
            client.post(BASE + "/journals", headers=headers, json=payload)
    finally:
        event.remove(Session, "before_flush", fail_audit)
    with SessionLocal() as db:
        assert not db.scalar(
            select(JournalEntry.id).where(JournalEntry.organization_id == UUID(merchant["org"]))
        )
        assert not db.scalar(
            select(JournalLine.id).where(JournalLine.organization_id == UUID(merchant["org"]))
        )


def test_inactive_context_and_account_cannot_post(client, merchant):
    headers = merchant["headers"]
    ids = new_accounts(client, headers)
    b1 = new_branch(client, headers, "INACTIVE")
    with SessionLocal() as db:
        branch = db.get(Branch, UUID(b1))
        branch.status = "INACTIVE"
        db.commit()
    assert (
        client.post(
            BASE + "/journals", headers=headers, json=journal_payload(ids, branch_id=b1)
        ).status_code
        == 409
    )
    with SessionLocal() as db:
        account = db.get(Account, UUID(ids[0]))
        account.is_active = False
        db.commit()
    assert (
        client.post(BASE + "/journals", headers=headers, json=journal_payload(ids)).status_code
        == 409
    )


@pytest.mark.parametrize("model", [Membership, User])
def test_suspended_actor_or_membership_cannot_post(client, merchant, model):
    headers = merchant["headers"]
    ids = new_accounts(client, headers)
    actor = client.get("/api/v1/auth/me", headers=headers).json()["id"]
    with SessionLocal() as db:
        if model is Membership:
            row = db.scalar(
                select(Membership).where(
                    Membership.user_id == UUID(actor),
                    Membership.organization_id == UUID(merchant["org"]),
                )
            )
        else:
            row = db.get(User, UUID(actor))
        row.status = "SUSPENDED"
        db.commit()
    assert client.post(
        BASE + "/journals", headers=headers, json=journal_payload(ids)
    ).status_code in {401, 404}
