"""Exactly-once initial opening-balance acceptance on disposable PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.domains.accounting.models import JournalEntry, OpeningBalanceBatch

BASE = "/api/v1/accounting"


def account_pair(client, headers):
    ids = []
    for code, kind in (("OB100", "ASSET"), ("OB300", "EQUITY")):
        response = client.post(
            BASE + "/accounts", headers=headers,
            json={
                "code": code + uuid4().hex[:8].upper(),
                "name": "Opening " + code,
                "account_type": kind,
            },
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])
    return ids


def payload(ids, *, booking_date="2026-09-30", request_id=None, amount="300.50"):
    return {
        "request_id": request_id or str(uuid4()),
        "booking_date": booking_date,
        "description": "Initial merchant equity",
        "lines": [
            {"account_id": ids[0], "debit": amount, "credit": "0.00"},
            {"account_id": ids[1], "debit": "0.00", "credit": amount},
        ],
    }


def journal_payload(opening, *, booking_date="2026-10-01", request_id=None):
    return {
        "request_id": request_id or str(uuid4()),
        "branch_id": None,
        "booking_date": booking_date,
        "description": "After opening",
        "lines": opening["lines"],
    }


def test_opening_is_one_time_and_exact_replay_without_duplicate_effect(client, merchant):
    headers = merchant["headers"]
    pair = account_pair(client, headers)
    data = payload(pair)
    first = client.post(BASE + "/opening-balance", headers=headers, json=data)
    assert first.status_code == 201, first.text
    created = first.json()
    assert created["journal"]["total_debit"] == "300.50"
    assert created["journal"]["total_credit"] == "300.50"
    assert created["booking_date"] == data["booking_date"]
    assert created["journal"]["branch_id"] is None
    assert client.get(BASE + "/opening-balance", headers=headers).json() == created

    repeated = client.post(BASE + "/opening-balance", headers=headers, json=data)
    assert repeated.status_code == 201, repeated.text
    assert repeated.json() == created
    assert client.post(BASE + "/opening-balance", headers=headers,
        json=payload(pair)).status_code == 409
    changed = {**data, "description": "Changed requested opening"}
    assert client.post(BASE + "/opening-balance", headers=headers, json=changed).status_code == 409

    assert client.post(BASE + "/journals", headers=headers,
        json=journal_payload(data, booking_date="2026-09-30")).status_code == 409
    assert client.post(BASE + "/journals", headers=headers,
        json=journal_payload(data, booking_date="2026-09-29")).status_code == 409
    assert client.post(BASE + "/journals", headers=headers,
        json=journal_payload(data, booking_date="2026-10-01")).status_code == 201
    assert client.post(BASE + "/journals", headers=headers,
        json=journal_payload(data, request_id=data["request_id"])).status_code == 409

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(OpeningBalanceBatch).where(
            OpeningBalanceBatch.organization_id == UUID(merchant["org"])
        )) == 1
        assert db.scalar(select(func.count()).select_from(JournalEntry).where(
            JournalEntry.organization_id == UUID(merchant["org"])
        )) == 2


def test_opening_must_be_balanced_and_use_postable_accounts(client, merchant):
    headers = merchant["headers"]
    pair = account_pair(client, headers)
    invalid = payload(pair)
    invalid["lines"][1]["credit"] = "300.49"
    assert client.post(BASE + "/opening-balance", headers=headers, json=invalid).status_code == 422
    group = client.post(BASE + "/accounts", headers=headers, json={
        "code": "OBGROUP", "name": "Asset group",
        "account_type": "ASSET", "is_postable": False,
    })
    assert group.status_code == 201
    forbidden = payload([group.json()["id"], pair[1]])
    assert client.post(BASE + "/opening-balance", headers=headers, json=forbidden).status_code == 409


def test_existing_earlier_journal_forbids_retroactive_opening(client, merchant):
    headers = merchant["headers"]
    pair = account_pair(client, headers)
    posted = client.post(BASE + "/journals", headers=headers,
        json=journal_payload(payload(pair), booking_date="2026-10-01"))
    assert posted.status_code == 201
    assert client.post(BASE + "/opening-balance", headers=headers,
        json=payload(pair, booking_date="2026-10-02")).status_code == 409
    # Initial cutover may precede known activity, if no history exists at/before it.
    created = client.post(BASE + "/opening-balance", headers=headers,
        json=payload(pair, booking_date="2026-09-30"))
    assert created.status_code == 201, created.text


def test_closed_accounting_period_denies_opening(client, merchant):
    headers = merchant["headers"]
    pair = account_pair(client, headers)
    p = client.post(BASE + "/periods", headers=headers, json={
        "start_date": "2026-09-01", "end_date": "2026-09-30",
    })
    assert p.status_code == 201, p.text
    assert client.post(BASE + f"/periods/{p.json()['id']}/close",
        headers=headers).status_code == 200
    assert client.post(BASE + "/opening-balance", headers=headers,
        json=payload(pair)).status_code == 409
    assert client.get(BASE + "/opening-balance", headers=headers).status_code == 404


def test_direct_sql_cannot_edit_batch_or_post_before_cutover(client, merchant):
    headers = merchant["headers"]
    pair = account_pair(client, headers)
    made = client.post(BASE + "/opening-balance", headers=headers, json=payload(pair))
    assert made.status_code == 201, made.text
    batch_id = UUID(made.json()["id"])
    with SessionLocal() as db:
        batch = db.get(OpeningBalanceBatch, batch_id)
        assert batch is not None
        batch.booking_date = date(2026, 9, 29)
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()
    with SessionLocal() as db:
        batch = db.get(OpeningBalanceBatch, batch_id)
        assert batch is not None
        db.delete(batch)
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    with SessionLocal() as db:
        db.add(JournalEntry(
            organization_id=UUID(merchant["org"]), branch_id=None,
            request_id=uuid4(), request_hash="a" * 64,
            booking_date=date(2026, 9, 29), description="SQL backdate attempt",
            currency="SAR", status="POSTED", posted_at=datetime.now(timezone.utc),
            posted_by=UUID(me.json()["id"]),
        ))
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()

    denied = client.post(BASE + f"/journals/{made.json()['journal_id']}/reverse",
        headers=headers,
        json={
            "request_id": str(uuid4()), "booking_date": "2026-10-03",
            "reason": "Opening cannot be reversed casually",
        })
    assert denied.status_code == 409


def test_accountant_reads_but_does_not_post_and_cashier_has_no_access(client, merchant):
    headers = merchant["headers"]
    email = f"opening-accountant-{uuid4()}@example.com"
    created = client.post("/api/v1/users", headers=headers,
        json={"name": "Accountant", "email": email, "password": "opening-test-password-2026"})
    assert created.status_code == 201, created.text
    roles = client.get("/api/v1/roles", headers=headers,
        params={"page_size": 100}).json()["items"]
    role_id = next(r["id"] for r in roles if r["code"] == "ACCOUNTANT")
    grant = client.post(f"/api/v1/users/{created.json()['id']}/roles",
        headers=headers, json={"role_id": role_id, "branch_id": None})
    assert grant.status_code == 201, grant.text
    login = client.post("/api/v1/auth/login", json={
        "email": email, "password": "opening-test-password-2026",
    })
    assert login.status_code == 200, login.text
    accountant = {
        "Authorization": "Bearer " + login.json()["access_token"],
        "X-Organization-ID": merchant["org"],
    }
    pair = account_pair(client, headers)
    assert client.post(BASE + "/opening-balance", headers=accountant,
        json=payload(pair)).status_code == 403
    assert client.post(BASE + "/opening-balance", headers=headers,
        json=payload(pair)).status_code == 201
    assert client.get(BASE + "/opening-balance", headers=accountant).status_code == 200


def test_cross_tenant_opening_is_never_readable(client, merchant):
    owner = merchant["headers"]
    pair = account_pair(client, owner)
    assert client.post(BASE + "/opening-balance", headers=owner,
        json=payload(pair)).status_code == 201
    email = f"opening-second-{uuid4()}@example.com"
    boot = client.post("/api/v1/bootstrap",
        headers={"X-Bootstrap-Key": get_settings().bootstrap_key},
        json={
            "owner_name": "Other Opening Merchant",
            "owner_email": email,
            "owner_password": "opening-test-password-2026",
            "organization_name": "Another business",
        })
    assert boot.status_code == 201, boot.text
    login = client.post("/api/v1/auth/login",
        json={"email": email, "password": "opening-test-password-2026"})
    assert login.status_code == 200
    other = {
        "Authorization": "Bearer " + login.json()["access_token"],
        "X-Organization-ID": boot.json()["organization"]["id"],
    }
    assert client.get(BASE + "/opening-balance", headers=other).status_code == 404
    assert client.get(BASE + "/opening-balance", headers=owner).status_code == 200


def test_two_opening_commands_cannot_both_post(client, merchant):
    h = merchant["headers"]
    pair = account_pair(client, h)
    def apply(data):
        return client.post(BASE + "/opening-balance", headers=h, json=data).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [
            pool.submit(apply, payload(pair)),
            pool.submit(apply, payload(pair)),
        ]
        results = [j.result() for j in jobs]
    assert sorted(results) == [201, 409]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(OpeningBalanceBatch).where(
            OpeningBalanceBatch.organization_id == UUID(merchant["org"])
        )) == 1
        assert db.scalar(select(func.count()).select_from(JournalEntry).where(
            JournalEntry.organization_id == UUID(merchant["org"])
        )) == 1
