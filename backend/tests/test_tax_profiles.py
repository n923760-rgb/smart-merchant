from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from test_customers import foreign_headers, role_headers

from app.core.database import SessionLocal
from app.core.models import AuditLog
from app.domains.accounting.models import JournalEntry
from app.domains.billing import tax_profile
from app.domains.billing.models import TaxProfile

BASE = "/api/v1/billing/tax-profiles"
READ = "/api/v1/billing/tax-profile"


def body(days=0, **changes):
    return {"request_id": str(uuid4()), "effective_from": (datetime.now(ZoneInfo("Asia/Riyadh")).date() + timedelta(days=days)).isoformat(), "registration_status": "REGISTERED", "vat_number": "300000000000003", **changes}


def read(client, headers, day):
    return client.get(READ, headers=headers, params={"effective_on": day})


def test_temporal_selection_unknown_default_no_fiscal_or_ledger_effect(client, merchant):
    h = merchant["headers"]
    a, b = body(), body(2, registration_status="NOT_REGISTERED", vat_number=None)
    assert read(client, h, a["effective_from"]).json()["profile"] is None
    first = client.post(BASE, headers=h, json=a)
    second = client.post(BASE, headers=h, json=b)
    assert first.status_code == second.status_code == 201
    assert read(client, h, a["effective_from"]).json()["profile"] == first.json()
    assert read(client, h, b["effective_from"]).json()["profile"] == second.json()
    assert first.json()["verification_status"] == "OPERATOR_DECLARED"
    assert first.json()["can_issue_tax_invoice"] is False
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(JournalEntry).where(JournalEntry.organization_id == UUID(merchant["org"]))) == 0
        rows = db.scalars(select(AuditLog).where(AuditLog.organization_id == UUID(merchant["org"]), AuditLog.action == "TAX_PROFILE_DECLARED")).all()
        assert len(rows) == 2
        assert all(set(row.after_data) == {"request_id", "effective_from"} for row in rows)


def test_replay_conflict_and_no_backdating_or_same_date(client, merchant):
    h, a = merchant["headers"], body()
    first = client.post(BASE, headers=h, json=a)
    assert first.status_code == 201
    assert client.post(BASE, headers=h, json=a).json() == first.json()
    assert client.post(BASE, headers=h, json={**a, "vat_number": "311111111111113"}).status_code == 409
    assert client.post(BASE, headers=h, json=body()).status_code == 409
    assert client.post(BASE, headers=h, json=body(-1)).status_code == 409
    assert client.post(BASE, headers=h, json=body(3)).status_code == 201
    assert client.post(BASE, headers=h, json=body(2)).status_code == 409
    assert client.post(BASE, headers=h, json=a).json() == first.json()


@pytest.mark.parametrize("changes", [
    {"vat_number": None}, {"vat_number": "123"}, {"vat_number": 300000000000003},
    {"registration_status": "NOT_REGISTERED"}, {"registration_status": "INVALID"},
    {"verification_status": "VERIFIED"}, {"organization_id": str(uuid4())},
])
def test_invalid_and_server_owned_fields_are_rejected(client, merchant, changes):
    assert client.post(BASE, headers=merchant["headers"], json=body(**changes)).status_code == 422


@pytest.mark.parametrize("role,branch_only,can_read", [("ACCOUNTANT", False, True), ("ACCOUNTANT", True, False), ("CASHIER", False, False)])
def test_global_owner_writes_and_accountant_reads(client, merchant, role, branch_only, can_read):
    branch_id = None
    if branch_only:
        branch = client.post("/api/v1/branches", headers=merchant["headers"], json={"name": "Abha", "code": "ABH01"})
        assert branch.status_code == 201
        branch_id = branch.json()["id"]
    h = role_headers(client, merchant, role, branch_id)
    a = body()
    assert client.post(BASE, headers=h, json=a).status_code == 403
    assert read(client, h, a["effective_from"]).status_code == (200 if can_read else 403)


def test_other_tenant_gets_no_profile_and_request_keys_are_local(client, merchant):
    a = body()
    assert client.post(BASE, headers=merchant["headers"], json=a).status_code == 201
    other = foreign_headers(client)
    assert read(client, other, a["effective_from"]).json()["profile"] is None
    made = client.post(BASE, headers=other, json=a)
    assert made.status_code == 201
    assert made.json()["organization_id"] != merchant["org"]


@pytest.mark.parametrize("action", ["update", "delete", "backdate", "inconsistent_number"])
def test_sql_guards(client, merchant, action):
    a = body()
    saved = client.post(BASE, headers=merchant["headers"], json=a)
    assert saved.status_code == 201
    with SessionLocal() as db:
        row = db.get(TaxProfile, UUID(saved.json()["id"]))
        if action == "delete":
            db.delete(row)
        elif action == "update":
            row.vat_number = "311111111111113"
        elif action == "backdate":
            db.add(TaxProfile(organization_id=row.organization_id, request_id=uuid4(), request_hash="0"*64, effective_from=datetime.now(ZoneInfo("Asia/Riyadh")).date()-timedelta(days=1), registration_status="UNKNOWN", created_by=row.created_by))
        else:
            db.add(TaxProfile(organization_id=row.organization_id, request_id=uuid4(), request_hash="0"*64, effective_from=datetime.now(ZoneInfo("Asia/Riyadh")).date()+timedelta(days=1), registration_status="UNKNOWN", vat_number=row.vat_number, created_by=row.created_by))
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_unknown_declaration_and_concurrent_different_requests_same_date(client, merchant):
    h = merchant["headers"]
    payloads = [body(registration_status="UNKNOWN", vat_number=None) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = [pool.submit(client.post, BASE, headers=h, json=p) for p in payloads]
        replies = [c.result() for c in calls]
    assert sorted(r.status_code for r in replies) == [201, 409]
    profile = read(client, h, payloads[0]["effective_from"]).json()["profile"]
    assert profile["registration_status"] == "UNKNOWN"
    assert profile["vat_number"] is None
    assert profile["can_issue_tax_invoice"] is False


def test_concurrent_replay_and_atomic_audit_failure(client, merchant, monkeypatch):
    a, h = body(), merchant["headers"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = [pool.submit(client.post, BASE, headers=h, json=a) for _ in range(2)]
        replies = [c.result() for c in calls]
    assert [r.status_code for r in replies] == [201, 201]
    assert replies[0].json() == replies[1].json()
    b = body(1)

    def failed(*args, **kwargs):
        raise RuntimeError("injected audit failure")

    monkeypatch.setattr(tax_profile, "record", failed)
    with pytest.raises(RuntimeError, match="injected audit"):
        client.post(BASE, headers=h, json=b)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(TaxProfile).where(TaxProfile.organization_id == UUID(merchant["org"]))) == 1
