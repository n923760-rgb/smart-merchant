"""Regression tests for operator-declared partial/full service receipts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from test_customers import foreign_headers, role_headers
from test_service_charges import post as post_charge
from test_service_charges import prepare as prepare_charge

from app.core.database import SessionLocal
from app.core.models import AuditLog, Permission, Role, RolePermission
from app.domains.accounting.models import Account, JournalEntry
from app.domains.billing import receipts
from app.domains.billing.models import ServiceReceipt

BASE = "/api/v1/billing/service-receipts"


def prepare(client, merchant):
    h = merchant["headers"]
    charge_body = prepare_charge(client, h)
    charge = post_charge(client, h, charge_body)
    account = client.post(
        "/api/v1/accounting/accounts", headers=h,
        json={"code": uuid4().hex[:12].upper(), "name": "Internal settlement bank",
              "account_type": "ASSET"},
    )
    assert account.status_code == 201, account.text
    receipt = {
        "request_id": str(uuid4()), "charge_id": charge["id"],
        "settlement_account_id": account.json()["id"],
        "amount": "10.00", "booking_date": charge["booking_date"],
        "payment_method": "BANK_TRANSFER", "operator_reference": "Owner declared transfer",
        "recording_basis": "Owner recorded receipt after internal confirmation",
        "confirm": True,
    }
    return charge, receipt


def balance(client, h, charge):
    response = client.get(f"/api/v1/billing/service-charges/{charge['id']}/balance", headers=h)
    assert response.status_code == 200, response.text
    return response.json()


def post(client, h, receipt):
    response = client.post(BASE, headers=h, json=receipt)
    assert response.status_code == 201, response.text
    return response.json()


def test_partial_full_recovery_reconcile_and_no_double_effect(client, merchant):
    h = merchant["headers"]
    charge, body = prepare(client, merchant)
    original = balance(client, h, charge)
    assert (original["original_amount"], original["collected_amount"],
            original["outstanding_amount"], original["payment_status"]) == (
                "40.24", "0.00", "40.24", "UNPAID"
            )
    first = post(client, h, body)
    assert first["amount"] == "10.00"
    assert first["status"] == "OPERATOR_RECORDED"
    assert first["external_payment_verified"] is False
    journal = client.get("/api/v1/accounting/journals/" + first["journal_id"], headers=h).json()
    assert journal["total_debit"] == journal["total_credit"] == "10.00"
    assert [(line["account_id"], line["debit"], line["credit"]) for line in journal["lines"]] == [
        (body["settlement_account_id"], "10.00", "0.00"),
        (charge["receivable_account_id"], "0.00", "10.00"),
    ]
    assert post(client, h, body) == first
    assert client.get(BASE + "/" + first["id"], headers=h).json() == first
    assert client.get("/api/v1/billing/service-receipt-requests/" + body["request_id"],
                      headers=h).json() == first
    partial = balance(client, h, charge)
    assert (partial["collected_amount"], partial["outstanding_amount"],
            partial["payment_status"]) == ("10.00", "30.24", "PARTIALLY_PAID")
    last = post(client, h, {**body, "request_id": str(uuid4()), "amount": "30.24"})
    assert last["id"] != first["id"]
    full = balance(client, h, charge)
    assert (full["collected_amount"], full["outstanding_amount"], full["payment_status"]) == (
        "40.24", "0.00", "PAID"
    )
    assert client.post(BASE, headers=h, json={**body, "request_id": str(uuid4()),
                                              "amount": "0.01"}).status_code == 409
    with SessionLocal() as db:
        receipts = db.scalars(select(ServiceReceipt).where(
            ServiceReceipt.organization_id == UUID(merchant["org"]),
            ServiceReceipt.charge_id == UUID(charge["id"]),
        )).all()
        assert len(receipts) == 2
        assert sum((r.amount for r in receipts), Decimal("0")) == Decimal("40.24")


@pytest.mark.parametrize("amount", [0.1, "0.00", "-0.01", "1", "1.2", "1.001", "1e2",
                                    "0001.00", "10000000000000000.00"])
def test_strict_amount_rejected_before_writes(client, merchant, amount):
    charge, body = prepare(client, merchant)
    response = client.post(BASE, headers=merchant["headers"], json={**body, "amount": amount})
    assert response.status_code == 422


@pytest.mark.parametrize("change", [
    {"confirm": False}, {"status": "SETTLED"}, {"currency": "USD"},
    {"organization_id": "not-allowed"}, {"amount": "10.01", "request_id": "same"},
])
def test_strict_receipt_contract_and_conflicting_replay(client, merchant, change):
    _, body = prepare(client, merchant)
    h = merchant["headers"]
    first = post(client, h, body)
    if change.get("request_id") == "same":
        change["request_id"] = body["request_id"]
        assert client.post(BASE, headers=h, json={**body, **change}).status_code == 409
    else:
        assert client.post(BASE, headers=h, json={**body, **change}).status_code == 422
    assert client.get(BASE + "/" + first["id"], headers=h).status_code == 200


def test_overcollection_denied_and_journal_request_collision(client, merchant):
    charge, body = prepare(client, merchant)
    h = merchant["headers"]
    post(client, h, {**body, "amount": "39.99"})
    assert client.post(BASE, headers=h, json={**body, "request_id": str(uuid4()),
                                              "amount": "0.26"}).status_code == 409
    assert balance(client, h, charge)["outstanding_amount"] == "0.25"
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ServiceReceipt).where(
            ServiceReceipt.charge_id == UUID(charge["id"]))) == 1
    collision = {**body, "request_id": charge["request_id"]}
    assert client.post(BASE, headers=h, json=collision).status_code == 409


def test_foreign_charge_and_account_and_read_are_tenant_scoped(client, merchant):
    h = merchant["headers"]
    charge, body = prepare(client, merchant)
    other_h = foreign_headers(client)
    foreign = {"headers": other_h, "org": other_h["X-Organization-ID"]}
    foreign_charge, foreign_receipt = prepare(client, foreign)
    other_saved = post(client, other_h, foreign_receipt)
    assert client.post(BASE, headers=h, json={
        **body, "charge_id": foreign_charge["id"]}).status_code == 404
    assert client.post(BASE, headers=h, json={
        **body, "settlement_account_id": foreign_receipt["settlement_account_id"]}).status_code == 404
    assert client.get(BASE + "/" + other_saved["id"], headers=h).status_code == 404
    assert client.get("/api/v1/billing/service-receipt-requests/" + foreign_receipt["request_id"],
                      headers=h).status_code == 404
    assert client.get("/api/v1/billing/service-charges/" + foreign_charge["id"] + "/balance",
                      headers=h).status_code == 404
    assert balance(client, h, charge)["payment_status"] == "UNPAID"


@pytest.mark.parametrize("role,branch_only,read_status", [
    ("ACCOUNTANT", False, 200), ("ACCOUNTANT", True, 403), ("CASHIER", False, 403),
])
def test_receipt_permissions(client, merchant, role, branch_only, read_status):
    charge, body = prepare(client, merchant)
    saved = post(client, merchant["headers"], body)
    branch = None
    if branch_only:
        branch = client.post("/api/v1/branches", headers=merchant["headers"],
                             json={"name": "Receiving Branch", "code": "RCV01"}).json()["id"]
    restricted = role_headers(client, merchant, role, branch)
    assert client.post(BASE, headers=restricted, json=body).status_code == 403
    assert client.get(BASE + "/" + saved["id"], headers=restricted).status_code == read_status
    assert client.get("/api/v1/billing/service-charges/" + charge["id"] + "/balance",
                      headers=restricted).status_code == read_status


def test_replay_rechecks_permission(client, merchant):
    _, body = prepare(client, merchant)
    h = merchant["headers"]
    post(client, h, body)
    with SessionLocal.begin() as db:
        role = db.scalar(select(Role.id).where(
            Role.organization_id == UUID(merchant["org"]), Role.code == "OWNER"))
        permission = db.scalar(select(Permission.id).where(Permission.code == "billing.receipts.record"))
        db.delete(db.get(RolePermission, (role, permission)))
    assert client.post(BASE, headers=h, json=body).status_code == 403
    assert client.get("/api/v1/billing/service-receipt-requests/" + body["request_id"],
                      headers=h).status_code == 200


@pytest.mark.parametrize("condition", ["wrong_type", "same_account", "inactive", "future", "before_charge", "closed"])
def test_invalid_account_date_and_period(client, merchant, condition):
    charge, body = prepare(client, merchant)
    h = merchant["headers"]
    if condition == "wrong_type":
        bad = client.post("/api/v1/accounting/accounts", headers=h, json={
            "code": uuid4().hex[:12].upper(), "name": "Income", "account_type": "REVENUE"}).json()
        body["settlement_account_id"] = bad["id"]
    elif condition == "same_account":
        body["settlement_account_id"] = charge["receivable_account_id"]
    elif condition == "inactive":
        with SessionLocal.begin() as db:
            db.get(Account, UUID(body["settlement_account_id"])).is_active = False
    elif condition == "future":
        body["booking_date"] = (date.today() + timedelta(days=10)).isoformat()
    elif condition == "before_charge":
        body["booking_date"] = (date.fromisoformat(charge["booking_date"]) - timedelta(days=1)).isoformat()
    elif condition == "closed":
        period = client.post("/api/v1/accounting/periods", headers=h, json={
            "start_date": charge["booking_date"], "end_date": charge["booking_date"]})
        assert period.status_code == 201, period.text
        closed = client.post("/api/v1/accounting/periods/" + period.json()["id"] + "/close", headers=h)
        assert closed.status_code == 200, closed.text
    assert client.post(BASE, headers=h, json=body).status_code == 409
    assert balance(client, h, charge)["outstanding_amount"] == "40.24"


def test_direct_sql_update_and_delete_rejected(client, merchant):
    _, body = prepare(client, merchant)
    saved = post(client, merchant["headers"], body)
    with SessionLocal() as db:
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE service_receipts SET amount = 0 WHERE id = :id"), {"id": saved["id"]})
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(text("DELETE FROM service_receipts WHERE id = :id"), {"id": saved["id"]})
        db.rollback()


def test_simultaneous_overcollection_serializes(client, merchant):
    charge, body = prepare(client, merchant)
    h = merchant["headers"]
    inputs = [{**body, "request_id": str(uuid4()), "amount": "30.00"} for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(
            lambda data: client.post(BASE, headers=h, json=data).status_code, inputs))
    assert sorted(statuses) == [201, 409]
    assert balance(client, h, charge)["outstanding_amount"] == "10.24"



def _financial_counts(organization_id):
    """Count authoritative effects separately to prove rollback/no duplicates."""
    with SessionLocal() as db:
        return {
            name: db.scalar(
                select(func.count()).select_from(model).where(
                    model.organization_id == UUID(organization_id)
                )
            )
            for name, model in (
                ("receipts", ServiceReceipt),
                ("journals", JournalEntry),
                ("audits", AuditLog),
            )
        }


def test_receipt_audit_failure_rolls_back_journal_and_request(client, merchant, monkeypatch):
    charge, body = prepare(client, merchant)
    h = merchant["headers"]
    before = _financial_counts(merchant["org"])

    def broken_audit(*args, **kwargs):
        raise RuntimeError("receipt audit failure injection")

    with monkeypatch.context() as patch:
        patch.setattr(receipts, "record", broken_audit)
        with pytest.raises(RuntimeError, match="receipt audit failure injection"):
            client.post(BASE, headers=h, json=body)

    assert _financial_counts(merchant["org"]) == before
    assert balance(client, h, charge)["outstanding_amount"] == "40.24"
    assert client.get(
        "/api/v1/billing/service-receipt-requests/" + body["request_id"], headers=h
    ).status_code == 404
    recorded = post(client, h, body)
    assert recorded["request_id"] == body["request_id"]
    assert _financial_counts(merchant["org"]) == {
        "receipts": before["receipts"] + 1,
        "journals": before["journals"] + 1,
        "audits": before["audits"] + 2,
    }


def test_direct_sql_overcollection_is_rejected_before_journal_identity(client, merchant):
    charge, body = prepare(client, merchant)
    h = merchant["headers"]
    saved = post(client, h, {**body, "amount": "40.24"})
    before = _financial_counts(merchant["org"])
    with SessionLocal() as db:
        original = db.get(ServiceReceipt, UUID(saved["id"]))
        db.add(ServiceReceipt(
            organization_id=original.organization_id,
            request_id=uuid4(), request_hash=original.request_hash,
            charge_id=original.charge_id, journal_id=original.journal_id,
            settlement_account_id=original.settlement_account_id,
            amount=Decimal("0.01"), booking_date=original.booking_date,
            payment_method=original.payment_method, recording_basis="Direct SQL overpay probe",
            created_by=original.created_by,
        ))
        with pytest.raises(DBAPIError, match="receipt over-collects original receivable"):
            db.flush()
        db.rollback()
    assert _financial_counts(merchant["org"]) == before
    assert balance(client, h, charge)["outstanding_amount"] == "0.00"


def test_direct_sql_receipt_cannot_use_another_charge_journal(client, merchant):
    first_charge, first_body = prepare(client, merchant)
    h = merchant["headers"]
    first_receipt = post(client, h, first_body)
    second_charge, _ = prepare(client, merchant)
    before = _financial_counts(merchant["org"])
    with SessionLocal() as db:
        existing = db.get(ServiceReceipt, UUID(first_receipt["id"]))
        db.add(ServiceReceipt(
            organization_id=existing.organization_id,
            request_id=existing.request_id, request_hash=existing.request_hash,
            charge_id=UUID(second_charge["id"]), journal_id=existing.journal_id,
            settlement_account_id=existing.settlement_account_id,
            amount=existing.amount, booking_date=existing.booking_date,
            payment_method=existing.payment_method, recording_basis="Wrong charge journal probe",
            created_by=existing.created_by,
        ))
        with pytest.raises(DBAPIError, match="receipt journal does not reconcile"):
            db.flush()
        db.rollback()
    assert _financial_counts(merchant["org"]) == before
    assert balance(client, h, first_charge)["outstanding_amount"] == "30.24"
    assert balance(client, h, second_charge)["outstanding_amount"] == "40.24"


def test_receipt_journal_reversal_forbidden_at_api_and_sql(client, merchant):
    charge, body = prepare(client, merchant)
    h = merchant["headers"]
    saved = post(client, h, body)
    before = _financial_counts(merchant["org"])
    reverse = client.post(
        "/api/v1/accounting/journals/" + saved["journal_id"] + "/reverse",
        headers=h,
        json={"request_id": str(uuid4()), "booking_date": body["booking_date"],
              "reason": "Cannot reverse receipt without subledger correction"},
    )
    assert reverse.status_code == 409, reverse.text
    with SessionLocal() as db:
        original = db.get(JournalEntry, UUID(saved["journal_id"]))
        db.add(JournalEntry(
            organization_id=original.organization_id,
            branch_id=original.branch_id,
            request_id=uuid4(), request_hash="0" * 64,
            booking_date=original.booking_date, description="Forged SQL reversal",
            currency=original.currency, status="POSTED",
            reversal_of_id=original.id, posted_by=original.posted_by,
            posted_at=original.posted_at,
        ))
        with pytest.raises(DBAPIError, match="receipt correction requires subledger reconciliation"):
            db.flush()
        db.rollback()
    assert _financial_counts(merchant["org"]) == before
    assert balance(client, h, charge)["outstanding_amount"] == "30.24"


def test_opening_balance_cutover_blocks_receipt_without_changing_charge(client, merchant):
    charge, body = prepare(client, merchant)
    h = merchant["headers"]
    opening = client.post(
        "/api/v1/accounting/opening-balance", headers=h,
        json={
            "request_id": str(uuid4()), "booking_date": body["booking_date"],
            "description": "Opening before any service receipt",
            "lines": [
                {"account_id": charge["receivable_account_id"], "debit": "1.00"},
                {"account_id": charge["revenue_account_id"], "credit": "1.00"},
            ],
        },
    )
    assert opening.status_code == 201, opening.text
    before = _financial_counts(merchant["org"])
    assert client.post(BASE, headers=h, json=body).status_code == 409
    assert _financial_counts(merchant["org"]) == before
    assert balance(client, h, charge)["outstanding_amount"] == "40.24"


def test_simultaneous_same_request_replays_one_receipt(client, merchant):
    charge, body = prepare(client, merchant)
    h = merchant["headers"]
    before = _financial_counts(merchant["org"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(client.post, BASE, headers=h, json=body) for _ in range(2)]
        results = [future.result() for future in futures]
    assert [result.status_code for result in results] == [201, 201]
    assert results[0].json() == results[1].json()
    assert _financial_counts(merchant["org"]) == {
        "receipts": before["receipts"] + 1,
        "journals": before["journals"] + 1,
        "audits": before["audits"] + 2,
    }
    assert balance(client, h, charge)["outstanding_amount"] == "30.24"
