"""Permanent customer identity is scoped and never inferred from contact data."""

from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.models import AuditLog, Permission, Role, RolePermission
from app.domains.accounting.models import JournalEntry
from app.domains.billing.models import ServiceDraft
from app.domains.customers import service
from app.domains.customers.models import Customer

BASE = "/api/v1/customers"


def payload(**changes):
    return {
        "request_id": str(uuid4()),
        "display_name": "عميل الخدمات",
        "email": "customer@example.com",
        **changes,
    }


def role_headers(client, merchant, role_code, branch_id=None):
    h = merchant["headers"]
    email = f"customer-role-{uuid4()}@example.com"
    user = client.post("/api/v1/users", headers=h, json={
        "name": "Customer Operator", "email": email, "password": "customer-test-password-123",
    })
    assert user.status_code == 201, user.text
    roles = client.get("/api/v1/roles", headers=h, params={"page_size": 100}).json()["items"]
    role_id = next(row["id"] for row in roles if row["code"] == role_code)
    assigned = client.post(f"/api/v1/users/{user.json()['id']}/roles", headers=h, json={
        "role_id": role_id, "branch_id": branch_id,
    })
    assert assigned.status_code == 201, assigned.text
    login = client.post("/api/v1/auth/login", json={
        "email": email, "password": "customer-test-password-123",
    })
    assert login.status_code == 200, login.text
    return {
        "Authorization": "Bearer " + login.json()["access_token"],
        "X-Organization-ID": merchant["org"],
    }


def foreign_headers(client):
    email = f"foreign-customer-{uuid4()}@example.com"
    boot = client.post("/api/v1/bootstrap", headers={
        "X-Bootstrap-Key": get_settings().bootstrap_key,
    }, json={
        "owner_name": "Other owner", "owner_email": email,
        "owner_password": "customer-test-password-123", "organization_name": "Other merchant",
    })
    assert boot.status_code == 201, boot.text
    login = client.post("/api/v1/auth/login", json={
        "email": email, "password": "customer-test-password-123",
    })
    assert login.status_code == 200, login.text
    return {
        "Authorization": "Bearer " + login.json()["access_token"],
        "X-Organization-ID": boot.json()["organization"]["id"],
    }


def test_customer_create_read_and_request_recovery_have_no_financial_effect(client, merchant):
    h, body = merchant["headers"], payload()
    response = client.post(BASE, headers=h, json=body)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["organization_id"] == merchant["org"]
    assert data["request_id"] == body["request_id"]
    assert data["display_name"] == body["display_name"]
    assert data["email"] == body["email"]
    assert data["identity_status"] == "OPERATOR_CREATED"
    assert "request_hash" not in data
    assert "balance" not in data
    assert client.get(BASE + "/" + data["id"], headers=h).json() == data
    assert client.get("/api/v1/customer-requests/" + body["request_id"], headers=h).json() == data
    assert client.get(BASE, headers=h).json()["items"] == [data]
    with SessionLocal() as db:
        for model in (JournalEntry, ServiceDraft):
            assert db.scalar(select(func.count()).select_from(model).where(
                model.organization_id == UUID(merchant["org"])
            )) == 0
        events = db.scalars(select(AuditLog).where(
            AuditLog.organization_id == UUID(merchant["org"]),
            AuditLog.action == "CUSTOMER_CREATED",
        )).all()
        assert len(events) == 1
        assert str(events[0].entity_id) == data["id"]
        assert events[0].after_data == {"request_id": body["request_id"]}
        assert events[0].before_data is None


def test_replay_normalizes_input_and_changed_content_conflicts(client, merchant):
    h, body = merchant["headers"], payload(display_name="  Customer  ")
    first = client.post(BASE, headers=h, json=body)
    assert first.status_code == 201, first.text
    body["display_name"] = "Customer"
    assert client.post(BASE, headers=h, json=body).json() == first.json()
    for field, changed in (("display_name", "Changed"), ("email", "other@example.com")):
        edited = {**body, field: changed}
        assert client.post(BASE, headers=h, json=edited).status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Customer).where(
            Customer.organization_id == UUID(merchant["org"])
        )) == 1
        assert db.scalar(select(func.count()).select_from(AuditLog).where(
            AuditLog.organization_id == UUID(merchant["org"]),
            AuditLog.action == "CUSTOMER_CREATED",
        )) == 1


def test_same_contacts_with_distinct_request_ids_are_distinct_customers(client, merchant):
    first = client.post(BASE, headers=merchant["headers"], json=payload())
    second = client.post(BASE, headers=merchant["headers"], json=payload())
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_optional_email_and_bounded_pagination(client, merchant):
    h = merchant["headers"]
    ids = set()
    for _ in range(3):
        response = client.post(BASE, headers=h, json=payload(email=None))
        assert response.status_code == 201, response.text
        assert response.json()["email"] is None
        ids.add(response.json()["id"])
    pages = [client.get(BASE, headers=h, params={"page": p, "page_size": 2}).json()
             for p in (1, 2)]
    assert [len(p["items"]) for p in pages] == [2, 1]
    assert {row["id"] for p in pages for row in p["items"]} == ids
    assert client.get(BASE, headers=h, params={"page_size": 101}).status_code == 422
    assert client.get(BASE, headers=h, params={"page": 0}).status_code == 422


@pytest.mark.parametrize("changes", [
    {"display_name": "   "}, {"display_name": "a" * 181}, {"email": "invalid"},
    {"request_id": "invalid"}, {"organization_id": str(uuid4())},
    {"created_by": str(uuid4())}, {"identity_status": "VERIFIED"}, {"balance": "500.00"},
])
def test_customer_rejects_invalid_and_server_owned_fields(client, merchant, changes):
    result = client.post(BASE, headers=merchant["headers"], json=payload(**changes))
    assert result.status_code == 422, result.text


def test_customer_tenant_isolation_including_request_recovery(client, merchant):
    body = payload()
    original = client.post(BASE, headers=merchant["headers"], json=body)
    assert original.status_code == 201
    other = foreign_headers(client)
    assert client.get(BASE + "/" + original.json()["id"], headers=other).status_code == 404
    assert client.get("/api/v1/customer-requests/" + body["request_id"], headers=other).status_code == 404
    assert client.get(BASE, headers=other).json()["items"] == []
    # Request keys are scoped by organization, not globally shared.
    created = client.post(BASE, headers=other, json=body)
    assert created.status_code == 201, created.text
    assert created.json()["id"] != original.json()["id"]
    assert created.json()["organization_id"] == other["X-Organization-ID"]


@pytest.mark.parametrize("role_code,branch_only,allowed", [
    ("ACCOUNTANT", False, True), ("ACCOUNTANT", True, False),
    ("CASHIER", False, False), ("MANAGER", False, False),
])
def test_customer_requires_organization_financial_grants(
    client, merchant, role_code, branch_only, allowed
):
    body = payload()
    created = client.post(BASE, headers=merchant["headers"], json=body)
    assert created.status_code == 201
    branch = None
    if branch_only:
        response = client.post("/api/v1/branches", headers=merchant["headers"], json={
            "name": "Abha", "code": "ABH01",
        })
        assert response.status_code == 201, response.text
        branch = response.json()["id"]
    h = role_headers(client, merchant, role_code, branch)
    expected = 200 if allowed else 403
    assert client.get(BASE, headers=h).status_code == expected
    assert client.get(BASE + "/" + created.json()["id"], headers=h).status_code == expected
    assert client.get("/api/v1/customer-requests/" + body["request_id"], headers=h).status_code == expected
    assert client.post(BASE, headers=h, json=payload()).status_code == (201 if allowed else 403)


def test_replay_rechecks_create_and_lookup_rechecks_read_permissions(client, merchant):
    h = role_headers(client, merchant, "ACCOUNTANT")
    body = payload()
    original = client.post(BASE, headers=h, json=body)
    assert original.status_code == 201
    with SessionLocal.begin() as db:
        role = db.scalar(select(Role).where(
            Role.organization_id == UUID(merchant["org"]), Role.code == "ACCOUNTANT",
        ))
        permission = db.scalar(select(Permission.id).where(Permission.code == "customers.create"))
        grant = db.get(RolePermission, (role.id, permission))
        db.delete(grant)
    assert client.post(BASE, headers=h, json=body).status_code == 403
    assert client.get(BASE, headers=h).status_code == 200
    with SessionLocal.begin() as db:
        read = db.scalar(select(Permission.id).where(Permission.code == "customers.read"))
        db.delete(db.get(RolePermission, (role.id, read)))
    assert client.get("/api/v1/customer-requests/" + body["request_id"], headers=h).status_code == 403


def test_customer_missing_or_unauthenticated_context_is_rejected(client, merchant):
    assert client.get(BASE).status_code == 401
    assert client.post(BASE, json=payload()).status_code == 401
    assert client.get(BASE, headers={"Authorization": merchant["headers"]["Authorization"]}).status_code == 401
    assert client.get(BASE + "/" + str(uuid4()), headers=merchant["headers"]).status_code == 404
    assert client.get("/api/v1/customer-requests/" + str(uuid4()), headers=merchant["headers"]).status_code == 404


@pytest.mark.parametrize("action", ["rename", "move", "rekey", "delete"])
def test_sql_cannot_mutate_customer_identity_or_contact_snapshot(client, merchant, action):
    created = client.post(BASE, headers=merchant["headers"], json=payload())
    assert created.status_code == 201
    with SessionLocal() as db:
        customer = db.get(Customer, UUID(created.json()["id"]))
        if action == "delete":
            db.delete(customer)
        elif action == "move":
            customer.organization_id = uuid4()
        elif action == "rekey":
            customer.request_id = uuid4()
        else:
            customer.display_name = "Replacement"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_sql_rejects_duplicate_request_and_blank_name(client, merchant):
    created = client.post(BASE, headers=merchant["headers"], json=payload())
    assert created.status_code == 201
    data = created.json()
    for name, request_id in (("Another", UUID(data["request_id"])), ("  ", uuid4())):
        with SessionLocal() as db:
            db.add(Customer(
                organization_id=UUID(merchant["org"]), request_id=request_id,
                request_hash="0" * 64, display_name=name, created_by=UUID(data["created_by"]),
            ))
            with pytest.raises(DBAPIError):
                db.commit()
            db.rollback()


def test_customer_and_audit_are_atomic(client, merchant, monkeypatch):
    body = payload()

    def broken_audit(*args, **kwargs):
        raise RuntimeError("injected disposable audit failure")

    monkeypatch.setattr(service, "record", broken_audit)
    with pytest.raises(RuntimeError, match="disposable audit failure"):
        client.post(BASE, headers=merchant["headers"], json=body)
    with SessionLocal() as db:
        assert db.scalar(select(Customer.id).where(
            Customer.organization_id == UUID(merchant["org"]),
            Customer.request_id == UUID(body["request_id"]),
        )) is None


def test_concurrent_retry_creates_one_customer_and_one_audit(client, merchant):
    body = payload()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(client.post, BASE, headers=merchant["headers"], json=body)
                   for _ in range(2)]
        replies = [future.result() for future in futures]
    assert [r.status_code for r in replies] == [201, 201]
    assert replies[0].json() == replies[1].json()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Customer).where(
            Customer.organization_id == UUID(merchant["org"])
        )) == 1
        assert db.scalar(select(func.count()).select_from(AuditLog).where(
            AuditLog.organization_id == UUID(merchant["org"]),
            AuditLog.action == "CUSTOMER_CREATED",
        )) == 1
