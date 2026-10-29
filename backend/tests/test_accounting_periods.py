"""Organization-wide accounting period closure on disposable PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.domains.accounting.models import AccountingPeriod, JournalEntry

BASE = "/api/v1/accounting"


def period(client, headers, start="2026-10-01", end="2026-10-31"):
    return client.post(
        BASE + "/periods", headers=headers,
        json={"start_date": start, "end_date": end},
    )


def accounts(client, headers):
    result = []
    for code, kind in [("PER100", "ASSET"), ("PER400", "REVENUE")]:
        response = client.post(
            BASE + "/accounts", headers=headers,
            json={"code": code + str(uuid4())[:6].upper(), "name": code, "account_type": kind},
        )
        assert response.status_code == 201, response.text
        result.append(response.json()["id"])
    return result


def journal(ids, *, booking_date="2026-10-15", request_id=None):
    return {
        "request_id": request_id or str(uuid4()),
        "branch_id": None,
        "booking_date": booking_date,
        "description": "Business service",
        "lines": [
            {"account_id": ids[0], "debit": "22.50"},
            {"account_id": ids[1], "credit": "22.50"},
        ],
    }


def staff(client, merchant, code):
    owner = merchant["headers"]
    email = f"period-{uuid4()}@example.com"
    invited = client.post("/api/v1/users", headers=owner, json={
        "name": code, "email": email, "password": "period-test-password-123"
    })
    assert invited.status_code == 201, invited.text
    roles = client.get("/api/v1/roles", headers=owner, params={"page_size": 100}).json()["items"]
    role = next(role for role in roles if role["code"] == code)
    granted = client.post(f"/api/v1/users/{invited.json()['id']}/roles", headers=owner,
        json={"role_id": role["id"], "branch_id": None})
    assert granted.status_code == 201, granted.text
    login = client.post("/api/v1/auth/login", json={
        "email": email, "password": "period-test-password-123",
    })
    assert login.status_code == 200, login.text
    return {
        "Authorization": "Bearer " + login.json()["access_token"],
        "X-Organization-ID": merchant["org"],
    }


def test_existing_accounting_requires_no_calendar_until_close(client, merchant):
    headers = merchant["headers"]
    ids = accounts(client, headers)
    first = journal(ids)
    old = client.post(BASE + "/journals", headers=headers, json=first)
    assert old.status_code == 201, old.text
    made = period(client, headers)
    assert made.status_code == 201, made.text
    assert made.json()["status"] == "OPEN"
    second = journal(ids)
    assert client.post(BASE + "/journals", headers=headers, json=second).status_code == 201
    closed = client.post(BASE + f"/periods/{made.json()['id']}/close", headers=headers)
    assert closed.status_code == 200, closed.text
    assert closed.json()["closed_by"]
    assert closed.json()["closed_at"]
    assert client.post(BASE + "/journals", headers=headers, json=journal(ids)).status_code == 409
    # Retrying a committed write after a period closes must return the same result.
    assert client.post(BASE + "/journals", headers=headers, json=first).json() == old.json()
    assert client.post(BASE + "/periods", headers=headers, json={
        "start_date": "2026-11-01", "end_date": "2026-11-30",
    }).status_code == 201
    assert client.post(BASE + "/journals", headers=headers,
        json=journal(ids, booking_date="2026-11-04")).status_code == 201
    assert client.post(BASE + f"/periods/{made.json()['id']}/close",
        headers=headers).status_code == 409
    assert len(client.get(BASE + "/periods", headers=headers).json()["items"]) == 2


def test_period_overlap_inclusive_bounds_and_sql_bypass_denied(client, merchant):
    headers = merchant["headers"]
    created = period(client, headers)
    assert created.status_code == 201
    assert period(client, headers, "2026-10-31", "2026-11-20").status_code == 409
    assert period(client, headers, "2026-09-01", "2026-10-01").status_code == 409
    assert period(client, headers, "2026-11-01", "2026-11-30").status_code == 201
    assert period(client, headers, "2026-11-01", "2026-10-31").status_code == 422

    with SessionLocal() as db:
        db.add(AccountingPeriod(
            organization_id=UUID(merchant["org"]),
            start_date=date(2026, 10, 20),
            end_date=date(2026, 10, 28),
            status="OPEN",
        ))
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()

    with SessionLocal() as db:
        old = db.get(AccountingPeriod, UUID(created.json()["id"]))
        assert old is not None
        old.end_date = date(2026, 11, 29)
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()


def test_owner_only_manage_accountant_read_and_cashier_denied(client, merchant):
    headers = merchant["headers"]
    a = staff(client, merchant, "ACCOUNTANT")
    cashier = staff(client, merchant, "CASHIER")
    assert client.get(BASE + "/periods", headers=a).status_code == 200
    assert client.get(BASE + "/periods", headers=cashier).status_code == 403
    assert period(client, a).status_code == 403
    created = period(client, headers)
    assert created.status_code == 201
    assert client.post(BASE + f"/periods/{created.json()['id']}/close",
        headers=a).status_code == 403


def test_periods_are_organization_scoped(client, merchant):
    headers = merchant["headers"]
    created = period(client, headers)
    assert created.status_code == 201
    email = f"foreign-period-{uuid4()}@example.com"
    boot = client.post(
        "/api/v1/bootstrap",
        headers={"X-Bootstrap-Key": get_settings().bootstrap_key},
        json={
            "owner_name": "Other owner",
            "owner_email": email,
            "owner_password": "period-test-password-123",
            "organization_name": "Foreign Merchant",
        },
    )
    assert boot.status_code == 201, boot.text
    login = client.post("/api/v1/auth/login", json={
        "email": email, "password": "period-test-password-123",
    })
    assert login.status_code == 200
    foreign = {
        "Authorization": "Bearer " + login.json()["access_token"],
        "X-Organization-ID": boot.json()["organization"]["id"],
    }
    assert client.get(BASE + "/periods", headers=foreign).json()["items"] == []
    assert client.post(BASE + f"/periods/{created.json()['id']}/close",
        headers=foreign).status_code == 404
    assert period(client, foreign).status_code == 201


def test_sql_cannot_post_directly_or_delete_closed_period(client, merchant):
    headers = merchant["headers"]
    made = period(client, headers)
    assert made.status_code == 201
    assert client.post(BASE + f"/periods/{made.json()['id']}/close",
        headers=headers).status_code == 200
    who = client.get("/api/v1/auth/me", headers=headers).json()["id"]
    with SessionLocal() as db:
        db.add(JournalEntry(
            organization_id=UUID(merchant["org"]),
            branch_id=None,
            request_id=uuid4(), request_hash="f" * 64,
            booking_date=date(2026, 10, 15),
            description="Attempt SQL bypass", currency="SAR",
            status="POSTED", posted_at=datetime.now(timezone.utc),
            posted_by=UUID(who),
        ))
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()
    with SessionLocal() as db:
        p = db.get(AccountingPeriod, UUID(made.json()["id"]))
        db.delete(p)
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()
    with SessionLocal() as db:
        assert db.scalar(
            select(func.count()).select_from(JournalEntry).where(
                JournalEntry.organization_id == UUID(merchant["org"])
            )
        ) == 0


def test_reversal_must_use_nonclosed_booking_date(client, merchant):
    headers = merchant["headers"]
    ids = accounts(client, headers)
    original = client.post(BASE + "/journals", headers=headers, json=journal(ids))
    assert original.status_code == 201
    made = period(client, headers)
    assert made.status_code == 201
    assert client.post(BASE + f"/periods/{made.json()['id']}/close", headers=headers).status_code == 200
    deny = client.post(BASE + f"/journals/{original.json()['id']}/reverse", headers=headers,
        json={"request_id": str(uuid4()), "booking_date": "2026-10-16", "reason": "Closed period"})
    assert deny.status_code == 409
    allowed = client.post(BASE + f"/journals/{original.json()['id']}/reverse", headers=headers,
        json={"request_id": str(uuid4()), "booking_date": "2026-11-01", "reason": "Open correction"})
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["reversal_of_id"] == original.json()["id"]


def test_concurrent_close_and_post_are_serialized(client, merchant):
    headers = merchant["headers"]
    ids = accounts(client, headers)
    made = period(client, headers)
    assert made.status_code == 201
    new = journal(ids)
    def do_close():
        return client.post(BASE + f"/periods/{made.json()['id']}/close", headers=headers).status_code
    def do_post():
        return client.post(BASE + "/journals", headers=headers, json=new).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_close = pool.submit(do_close)
        f_post = pool.submit(do_post)
        closed, posted = f_close.result(), f_post.result()
    assert closed == 200
    assert posted in {201, 409}
    # The same request cannot succeed when retried after closure unless it
    # already posted before closure in this serialized execution.
    replay = client.post(BASE + "/journals", headers=headers, json=new)
    assert replay.status_code == posted
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(JournalEntry).where(
            JournalEntry.organization_id == UUID(merchant["org"])))
    assert count == (1 if posted == 201 else 0)
