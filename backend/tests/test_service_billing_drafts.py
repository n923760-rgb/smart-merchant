"""Internal draft must never be mistaken for an issued tax invoice."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.domains.accounting.models import JournalEntry
from app.domains.billing.models import ServiceDraft, ServiceDraftLine

BASE = "/api/v1/billing/service-drafts"


def draft_payload(*, request_id=None, customer_name="Internal Demo Customer"):
    return {
        "request_id": request_id or str(uuid4()),
        "customer_name": customer_name,
        "customer_email": "sample@example.com",
        "lines": [
            {"service_name": "Consulting", "quantity": "1.500", "unit_price": "9.99"},
            {"service_name": "Setup", "quantity": "2.000", "unit_price": "10.00"},
        ],
    }


def test_draft_decimal_rounding_nonfiscal_and_no_journal_effect(client, merchant):
    response = client.post(BASE, headers=merchant["headers"], json=draft_payload())
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "DRAFT"
    assert data["document_kind"] == "INTERNAL_SERVICE_DRAFT"
    assert data["tax_status"] == "NOT_EVALUATED"
    assert data["currency"] == "SAR"
    assert data["lines"][0]["line_total"] == "14.99"
    assert data["lines"][0]["quantity"] == "1.500"
    assert data["lines"][1]["line_total"] == "20.00"
    assert data["amount_before_tax"] == "34.99"
    assert "tax_total" not in data
    assert "invoice_number" not in data
    assert client.get(BASE + "/" + data["id"], headers=merchant["headers"]).json() == data
    listed = client.get(BASE, headers=merchant["headers"])
    assert listed.status_code == 200
    assert data["id"] in [row["id"] for row in listed.json()["items"]]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(JournalEntry).where(
            JournalEntry.organization_id == UUID(merchant["org"])
        )) == 0


def test_permanent_request_identity_same_content_no_duplicate_and_mismatch_conflict(
    client, merchant
):
    h = merchant["headers"]
    body = draft_payload()
    first = client.post(BASE, headers=h, json=body)
    assert first.status_code == 201
    replay = client.post(BASE, headers=h, json=body)
    assert replay.status_code == 201
    assert replay.json() == first.json()
    changed = draft_payload(request_id=body["request_id"])
    changed["lines"][0]["unit_price"] = "19.99"
    assert client.post(BASE, headers=h, json=changed).status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ServiceDraft).where(
            ServiceDraft.organization_id == UUID(merchant["org"])
        )) == 1


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["lines"][0].update({"quantity": 1.5}),
        lambda p: p["lines"][0].update({"unit_price": 9.99}),
        lambda p: p["lines"][0].update({"quantity": "-1.000"}),
        lambda p: p["lines"][0].update({"quantity": "0.000"}),
        lambda p: p["lines"][0].update({"unit_price": "-0.01"}),
        lambda p: p["lines"][0].update({"unit_price": "1.001"}),
        lambda p: p["lines"][0].update({"quantity": "1.0001"}),
        lambda p: p.update({"lines": []}),
        lambda p: p.update({"lines": p["lines"] * 51}),
    ],
)
def test_invalid_decimal_quantity_price_and_line_counts_rejected(client, merchant, change):
    data = draft_payload()
    change(data)
    result = client.post(BASE, headers=merchant["headers"], json=data)
    assert result.status_code == 422, result.text


def test_sql_rejects_header_and_line_mutations(client, merchant):
    draft = client.post(BASE, headers=merchant["headers"], json=draft_payload())
    assert draft.status_code == 201, draft.text
    draft_id = UUID(draft.json()["id"])
    with SessionLocal() as db:
        stored = db.get(ServiceDraft, draft_id)
        stored.customer_name = "A different customer"
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()
    with SessionLocal() as db:
        row = db.scalar(select(ServiceDraftLine).where(ServiceDraftLine.draft_id == draft_id))
        row.unit_price = row.unit_price + 1
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()
    with SessionLocal() as db:
        db.delete(db.get(ServiceDraft, draft_id))
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()
    with SessionLocal() as db:
        old = db.get(ServiceDraft, draft_id)
        db.add(ServiceDraftLine(
            organization_id=old.organization_id, draft_id=draft_id, line_number=3,
            service_name="Late unauthorized service",
            quantity="1.000", unit_price="2.00", line_total="2.00",
        ))
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()


def test_unsealed_direct_sql_draft_cannot_commit(client, merchant):
    owner = client.get("/api/v1/auth/me", headers=merchant["headers"])
    assert owner.status_code == 200
    with SessionLocal() as db:
        db.add(ServiceDraft(
            organization_id=UUID(merchant["org"]),
            request_id=uuid4(),
            request_hash="0" * 64,
            customer_name="Broken half-built document",
            customer_email=None,
            currency="SAR",
            status="BUILDING",
            tax_status="NOT_EVALUATED",
            document_kind="INTERNAL_SERVICE_DRAFT",
            amount_before_tax="2.00",
            created_by=UUID(owner.json()["id"]),
        ))
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_only_tenant_owner_or_accountant_can_access_drafts(client, merchant):
    h = merchant["headers"]
    created = client.post(BASE, headers=h, json=draft_payload())
    assert created.status_code == 201, created.text
    email = f"draft-accountant-{uuid4()}@example.com"
    invite = client.post("/api/v1/users", headers=h, json={
        "name": "Draft Accountant", "email": email, "password": "draft-test-password-123",
    })
    assert invite.status_code == 201, invite.text
    roles = client.get("/api/v1/roles", headers=h, params={"page_size": 100}).json()["items"]
    accountant_role = next(row["id"] for row in roles if row["code"] == "ACCOUNTANT")
    assigned = client.post(
        f"/api/v1/users/{invite.json()['id']}/roles",
        headers=h, json={"role_id": accountant_role, "branch_id": None}
    )
    assert assigned.status_code == 201
    login = client.post("/api/v1/auth/login", json={
        "email": email, "password": "draft-test-password-123",
    })
    assert login.status_code == 200
    accountant = {
        "Authorization": "Bearer " + login.json()["access_token"],
        "X-Organization-ID": merchant["org"],
    }
    assert client.get(BASE, headers=accountant).status_code == 200
    assert client.post(BASE, headers=accountant, json=draft_payload()).status_code == 201
    # A user with no financial grants must not see customer identity.
    cashier_email = f"cashier-{uuid4()}@example.com"
    invited = client.post("/api/v1/users", headers=h, json={
        "name": "Cashier", "email": cashier_email, "password": "draft-test-password-123",
    })
    cashier_role = next(row["id"] for row in roles if row["code"] == "CASHIER")
    assert client.post(f"/api/v1/users/{invited.json()['id']}/roles",
        headers=h, json={"role_id": cashier_role, "branch_id": None}).status_code == 201
    cashier_login = client.post("/api/v1/auth/login", json={
        "email": cashier_email, "password": "draft-test-password-123",
    })
    restricted = {
        "Authorization": "Bearer " + cashier_login.json()["access_token"],
        "X-Organization-ID": merchant["org"],
    }
    assert client.get(BASE, headers=restricted).status_code == 403
    assert client.get(BASE + "/" + created.json()["id"], headers=restricted).status_code == 403
    assert client.post(BASE, headers=restricted, json=draft_payload()).status_code == 403


def test_other_organization_cannot_read_customer_draft(client, merchant):
    owner = merchant["headers"]
    created = client.post(BASE, headers=owner, json=draft_payload())
    assert created.status_code == 201
    email = f"foreign-service-{uuid4()}@example.com"
    boot = client.post(
        "/api/v1/bootstrap",
        headers={"X-Bootstrap-Key": get_settings().bootstrap_key},
        json={
            "owner_name": "Other tenant",
            "owner_email": email,
            "owner_password": "draft-test-password-123",
            "organization_name": "Other tenant's services",
        },
    )
    assert boot.status_code == 201, boot.text
    login = client.post("/api/v1/auth/login",
        json={"email": email, "password": "draft-test-password-123"})
    assert login.status_code == 200
    other = {
        "Authorization": "Bearer " + login.json()["access_token"],
        "X-Organization-ID": boot.json()["organization"]["id"],
    }
    assert client.get(BASE + "/" + created.json()["id"], headers=other).status_code == 404
    assert client.get(BASE, headers=other).json()["items"] == []
    assert client.post(BASE, headers=other, json=draft_payload()).status_code == 201
