"""Read-only service allocation must never become an unqualified AR posting."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_customers import foreign_headers, role_headers

from app.core.database import SessionLocal
from app.core.models import AuditLog, Organization, Permission, Role, RolePermission
from app.domains.accounting.models import Account, JournalEntry, JournalLine
from app.domains.billing.models import ServiceDraft

BASE = "/api/v1/billing/service-obligation-previews"


def prepare(client, headers, *, zero=False):
    draft = client.post("/api/v1/billing/service-drafts", headers=headers, json={
        "request_id": str(uuid4()), "customer_name": "Source name, not an identity",
        "customer_email": "source@example.com",
        "lines": [
            {"service_name": "Consulting", "quantity": "1.500", "unit_price": "0.00" if zero else "9.99"},
            {"service_name": "Setup", "quantity": "2.000", "unit_price": "0.00" if zero else "10.00"},
        ],
    })
    assert draft.status_code == 201, draft.text
    customer = client.post("/api/v1/customers", headers=headers, json={
        "request_id": str(uuid4()), "display_name": "Explicitly selected customer",
    })
    assert customer.status_code == 201, customer.text
    accounts = []
    for kind in ("ASSET", "REVENUE"):
        account = client.post("/api/v1/accounting/accounts", headers=headers, json={
            "code": "PRE" + uuid4().hex[:12].upper(), "name": kind, "account_type": kind,
        })
        assert account.status_code == 201, account.text
        accounts.append(account.json()["id"])
    return {
        "draft_id": draft.json()["id"], "customer_id": customer.json()["id"],
        "receivable_account_id": accounts[0], "revenue_account_id": accounts[1],
        "booking_date": "2026-11-01",
    }


def counts(organization):
    with SessionLocal() as db:
        return {
            model.__tablename__: db.scalar(select(func.count()).select_from(model).where(
                model.organization_id == UUID(organization)
            )) for model in (JournalEntry, JournalLine, ServiceDraft, AuditLog)
        }


def test_exact_pre_tax_preview_explicit_identity_unknown_tax_and_no_effect(client, merchant):
    h = merchant["headers"]
    body = prepare(client, h)
    before = counts(merchant["org"])
    first = client.post(BASE, headers=h, json=body)
    assert first.status_code == 200, first.text
    data = first.json()
    assert data["document_kind"] == "INTERNAL_SERVICE_OBLIGATION_PREVIEW"
    assert data["organization_id"] == merchant["org"]
    assert data["selected_customer"]["id"] == body["customer_id"]
    assert data["selected_customer"]["display_name"] == "Explicitly selected customer"
    assert data["selected_customer"]["identity_status"] == "OPERATOR_CREATED"
    assert data["draft_customer_snapshot"]["name"] == "Source name, not an identity"
    assert data["can_post"] is False
    assert data["approval_status"] == "NOT_APPROVED"
    assert data["tax_status"] == "NOT_EVALUATED"
    assert data["tax_total"] is None and data["amount_due"] is None
    assert data["amount_before_tax"] == "34.99"
    assert data["branch_id"] is None
    assert data["pre_tax_allocation"] == [
        {"account_id": body["receivable_account_id"], "side": "DEBIT", "amount": "34.99"},
        {"account_id": body["revenue_account_id"], "side": "CREDIT", "amount": "34.99"},
    ]
    assert set(data["blocking_reasons"]) == {
        "TAX_POLICY_UNQUALIFIED", "FINANCIAL_APPROVAL_REQUIRED", "POSTING_NOT_IMPLEMENTED",
    }
    for key in ("request_id", "journal_id", "invoice_number", "lines"):
        assert key not in data
    assert client.post(BASE, headers=h, json=body).json() == data
    assert counts(merchant["org"]) == before
    saved = client.get("/api/v1/billing/service-drafts/" + body["draft_id"], headers=h).json()
    assert saved["status"] == "DRAFT" and saved["tax_status"] == "NOT_EVALUATED"
    assert "customer_id" not in saved  # Preview cannot silently persist a link.


@pytest.mark.parametrize("role,branch_only,expected", [
    ("ACCOUNTANT", False, 200), ("ACCOUNTANT", True, 403), ("CASHIER", False, 403),
])
def test_preview_requires_global_combined_read_permissions(
    client, merchant, role, branch_only, expected
):
    body = prepare(client, merchant["headers"])
    branch_id = None
    if branch_only:
        branch = client.post("/api/v1/branches", headers=merchant["headers"], json={
            "name": "Abha", "code": "ABH01",
        })
        assert branch.status_code == 201, branch.text
        branch_id = branch.json()["id"]
    h = role_headers(client, merchant, role, branch_id)
    assert client.post(BASE, headers=h, json=body).status_code == expected


@pytest.mark.parametrize("permission", [
    "billing.drafts.read", "customers.read", "accounting.accounts.read",
    "accounting.periods.read", "accounting.opening.read",
])
def test_missing_any_required_read_grant_denies_even_known_ids(client, merchant, permission):
    body = prepare(client, merchant["headers"])
    h = role_headers(client, merchant, "ACCOUNTANT")
    with SessionLocal.begin() as db:
        role = db.scalar(select(Role.id).where(
            Role.organization_id == UUID(merchant["org"]), Role.code == "ACCOUNTANT",
        ))
        permission_id = db.scalar(select(Permission.id).where(Permission.code == permission))
        db.delete(db.get(RolePermission, (role, permission_id)))
    assert client.post(BASE, headers=h, json=body).status_code == 403


@pytest.mark.parametrize("key", [
    "draft_id", "customer_id", "receivable_account_id", "revenue_account_id",
])
@pytest.mark.parametrize("foreign", [True, False])
def test_each_foreign_or_missing_reference_is_not_found(client, merchant, key, foreign):
    body = prepare(client, merchant["headers"])
    other = prepare(client, foreign_headers(client)) if foreign else None
    body[key] = other[key] if other else str(uuid4())
    response = client.post(BASE, headers=merchant["headers"], json=body)
    assert response.status_code == 404, response.text


@pytest.mark.parametrize("condition", ["inactive_ar", "inactive_revenue", "summary", "wrong_type", "same_account"])
def test_unsuitable_account_mappings_cannot_be_presented_as_valid(client, merchant, condition):
    h = merchant["headers"]
    body = prepare(client, h)
    if condition in {"inactive_ar", "inactive_revenue"}:
        key = "receivable_account_id" if condition == "inactive_ar" else "revenue_account_id"
        with SessionLocal.begin() as db:
            db.get(Account, UUID(body[key])).is_active = False
    elif condition == "same_account":
        body["revenue_account_id"] = body["receivable_account_id"]
    else:
        account = client.post("/api/v1/accounting/accounts", headers=h, json={
            "code": "PRE" + uuid4().hex[:12].upper(), "name": condition,
            "account_type": "ASSET" if condition == "summary" else "LIABILITY",
            "is_postable": condition != "summary",
        })
        assert account.status_code == 201, account.text
        body["receivable_account_id"] = account.json()["id"]
    assert client.post(BASE, headers=h, json=body).status_code == 409


def test_closed_period_and_opening_cutover_are_explicit_blockers(client, merchant):
    h = merchant["headers"]
    body = prepare(client, h)
    opening = client.post("/api/v1/accounting/opening-balance", headers=h, json={
        "request_id": str(uuid4()), "booking_date": "2026-10-31", "description": "Initial cutover",
        "lines": [
            {"account_id": body["receivable_account_id"], "debit": "10.00"},
            {"account_id": body["revenue_account_id"], "credit": "10.00"},
        ],
    })
    assert opening.status_code == 201, opening.text
    period = client.post("/api/v1/accounting/periods", headers=h, json={
        "start_date": "2026-10-01", "end_date": "2026-10-31",
    })
    assert period.status_code == 201, period.text
    assert client.post("/api/v1/accounting/periods/" + period.json()["id"] + "/close", headers=h).status_code == 200
    before = counts(merchant["org"])
    for day in ("2026-10-30", "2026-10-31"):
        body["booking_date"] = day
        response = client.post(BASE, headers=h, json=body)
        assert response.status_code == 200, response.text
        assert response.json()["can_post"] is False
        assert "ACCOUNTING_PERIOD_CLOSED" in response.json()["blocking_reasons"]
        assert "ON_OR_BEFORE_OPENING_CUTOVER" in response.json()["blocking_reasons"]
    body["booking_date"] = "2026-11-01"
    blockers = client.post(BASE, headers=h, json=body).json()["blocking_reasons"]
    assert "ACCOUNTING_PERIOD_CLOSED" not in blockers
    assert "ON_OR_BEFORE_OPENING_CUTOVER" not in blockers
    assert "TAX_POLICY_UNQUALIFIED" in blockers
    assert counts(merchant["org"]) == before


@pytest.mark.parametrize("zero", [True, False])
def test_zero_draft_or_unqualified_currency_is_rejected(client, merchant, zero):
    body = prepare(client, merchant["headers"], zero=zero)
    if not zero:
        with SessionLocal.begin() as db:
            db.get(Organization, UUID(merchant["org"])).currency = "USD"
    assert client.post(BASE, headers=merchant["headers"], json=body).status_code == 409


@pytest.mark.parametrize("extra", [
    {"tax_total": "0.00"}, {"amount_due": "34.99"}, {"can_post": True},
    {"request_id": str(uuid4())}, {"branch_id": str(uuid4())}, {"approval_status": "APPROVED"},
    {"booking_date": "2026-02-30"},
])
def test_client_cannot_supply_approval_tax_posting_or_invalid_date(client, merchant, extra):
    body = prepare(client, merchant["headers"])
    assert client.post(BASE, headers=merchant["headers"], json={**body, **extra}).status_code == 422


def test_preview_requires_authenticated_organization_context(client):
    body = {key: str(uuid4()) for key in (
        "draft_id", "customer_id", "receivable_account_id", "revenue_account_id",
    )}
    body["booking_date"] = "2026-11-01"
    assert client.post(BASE, json=body).status_code == 401
