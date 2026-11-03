from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from test_customers import foreign_headers, role_headers
from test_service_billing_drafts import draft_payload
from test_tax_profiles import body as profile_body

from app.core.database import SessionLocal
from app.core.models import AuditLog
from app.domains.accounting.models import JournalEntry
from app.domains.billing import tax_assessment
from app.domains.billing.models import TaxAssessment

BASE = "/api/v1/billing/service-tax-assessments"


def prepare(client, headers, status="REGISTERED", *, profile=True, lines=None):
    date = profile_body()["effective_from"]
    saved_profile = None
    if profile:
        data = profile_body(registration_status=status, vat_number="300000000000003" if status == "REGISTERED" else None)
        response = client.post("/api/v1/billing/tax-profiles", headers=headers, json=data)
        assert response.status_code == 201, response.text
        saved_profile = response.json()
    draft = draft_payload()
    if lines is not None:
        draft["lines"] = lines
    response = client.post("/api/v1/billing/service-drafts", headers=headers, json=draft)
    assert response.status_code == 201, response.text
    return {"request_id": str(uuid4()), "draft_id": response.json()["id"], "assessment_date": date,
            "category": "STANDARD_15", "classification_basis": "Operator reviewed standard-category classification"}, saved_profile


def test_exact_assessment_is_immutable_pinned_and_not_financial_approval(client, merchant):
    h = merchant["headers"]
    body, profile = prepare(client, h)
    response = client.post(BASE, headers=h, json=body)
    assert response.status_code == 201, response.text
    row = response.json()
    assert (row["net_amount"], row["tax_amount"], row["gross_amount"]) == ("34.99", "5.25", "40.24")
    assert row["profile_id"] == profile["id"] and row["draft_id"] == body["draft_id"]
    assert row["tax_status"] == "OPERATOR_ASSESSED"
    assert row["approval_status"] == "NOT_APPROVED"
    assert row["can_post"] is False and row["can_issue_tax_invoice"] is False
    assert row["amount_due"] is None
    assert client.get(BASE + "/" + row["id"], headers=h).json() == row
    assert client.post(BASE, headers=h, json=body).json() == row
    assert client.post(BASE, headers=h, json={**body, "classification_basis": "Changed basis"}).status_code == 409
    draft = client.get("/api/v1/billing/service-drafts/" + body["draft_id"], headers=h).json()
    assert draft["status"] == "DRAFT" and draft["tax_status"] == "NOT_EVALUATED"
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(JournalEntry).where(JournalEntry.organization_id == UUID(merchant["org"]))) == 0
        events = db.scalars(select(AuditLog).where(AuditLog.organization_id == UUID(merchant["org"]), AuditLog.action == "SERVICE_TAX_ASSESSED")).all()
        assert len(events) == 1
        assert events[0].after_data == {"request_id": body["request_id"], "draft_id": body["draft_id"], "profile_id": profile["id"]}


def test_profile_changes_do_not_recalculate_saved_assessment(client, merchant):
    h = merchant["headers"]
    body, original_profile = prepare(client, h)
    future = profile_body(3)
    body["assessment_date"] = future["effective_from"]
    first = client.post(BASE, headers=h, json=body)
    assert first.status_code == 201, first.text
    scheduled = client.post("/api/v1/billing/tax-profiles", headers=h, json=profile_body(2))
    assert scheduled.status_code == 201, scheduled.text
    assert client.post(BASE, headers=h, json=body).json() == first.json()
    assert first.json()["profile_id"] == original_profile["id"]
    reassessed = client.post(BASE, headers=h, json={**body, "request_id": str(uuid4())})
    assert reassessed.status_code == 201
    assert reassessed.json()["profile_id"] == scheduled.json()["id"]
    assert client.get(BASE + "/" + first.json()["id"], headers=h).json() == first.json()


@pytest.mark.parametrize("status", ["MISSING", "UNKNOWN", "NOT_REGISTERED"])
def test_unqualified_registration_does_not_silently_mean_zero_tax(client, merchant, status):
    body, _ = prepare(client, merchant["headers"], status=status, profile=status != "MISSING")
    assert client.post(BASE, headers=merchant["headers"], json=body).status_code == 409


def test_category_rounding_uses_aggregate_and_overflow_rolls_back(client, merchant):
    h = merchant["headers"]
    body, _ = prepare(client, h, lines=[{"service_name": "Tiny service", "quantity": "1", "unit_price": "0.10"}] * 2)
    row = client.post(BASE, headers=h, json=body)
    assert row.status_code == 201, row.text
    assert row.json()["tax_amount"] == "0.03"
    large = draft_payload()
    large["lines"] = [{"service_name": "Large", "quantity": "10000.000", "unit_price": "999999999999.99"}]
    draft = client.post("/api/v1/billing/service-drafts", headers=h, json=large)
    assert draft.status_code == 201, draft.text
    assert client.post(BASE, headers=h, json={**body, "request_id": str(uuid4()), "draft_id": draft.json()["id"]}).status_code == 409


@pytest.mark.parametrize("change", [{"category": "ZERO"}, {"classification_basis": " "}, {"tax_amount": "0.00"}, {"profile_id": str(uuid4())}, {"can_post": True}, {"organization_id": str(uuid4())}])
def test_strict_classification_and_server_owned_fields(client, merchant, change):
    body, _ = prepare(client, merchant["headers"])
    assert client.post(BASE, headers=merchant["headers"], json={**body, **change}).status_code == 422


@pytest.mark.parametrize("role,branch_only,read_status", [("ACCOUNTANT", False, 200), ("ACCOUNTANT", True, 403), ("CASHIER", False, 403)])
def test_owner_manage_accountant_read_and_branch_denial(client, merchant, role, branch_only, read_status):
    h = merchant["headers"]
    body, _ = prepare(client, h)
    row = client.post(BASE, headers=h, json=body)
    assert row.status_code == 201
    branch_id = None
    if branch_only:
        branch = client.post("/api/v1/branches", headers=h, json={"name": "Abha", "code": "ABH01"})
        assert branch.status_code == 201
        branch_id = branch.json()["id"]
    restricted = role_headers(client, merchant, role, branch_id)
    assert client.post(BASE, headers=restricted, json=body).status_code == 403
    assert client.get(BASE + "/" + row.json()["id"], headers=restricted).status_code == read_status


def test_tenant_isolation_on_source_and_saved_read(client, merchant):
    body, _ = prepare(client, merchant["headers"])
    row = client.post(BASE, headers=merchant["headers"], json=body)
    assert row.status_code == 201
    other = foreign_headers(client)
    assert client.get(BASE + "/" + row.json()["id"], headers=other).status_code == 404
    assert client.post(BASE, headers=other, json=body).status_code == 404


@pytest.mark.parametrize("action", ["update", "delete", "wrong_totals", "wrong_source", "wrong_profile"])
def test_sql_guard_rejects_mutation_or_inconsistent_snapshot(client, merchant, action):
    h = merchant["headers"]
    body, _ = prepare(client, h)
    response = client.post(BASE, headers=h, json=body)
    assert response.status_code == 201
    with SessionLocal() as db:
        row = db.get(TaxAssessment, UUID(response.json()["id"]))
        if action == "update":
            row.classification_basis = "Mutated"
        elif action == "delete":
            db.delete(row)
        else:
            values = {c.name: getattr(row, c.name) for c in TaxAssessment.__table__.columns if c.name not in {"id", "created_at"}}
            values["request_id"] = uuid4()
            if action == "wrong_totals":
                values.update(net_amount="10.00", tax_amount="1.50", gross_amount="11.50")
            elif action == "wrong_source":
                values["draft_id"] = uuid4()
            else:
                values["profile_id"] = uuid4()
            db.add(TaxAssessment(**values))
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_concurrent_replay_and_atomic_audit(client, merchant, monkeypatch):
    h = merchant["headers"]
    body, _ = prepare(client, h)
    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = [pool.submit(client.post, BASE, headers=h, json=body) for _ in range(2)]
        replies = [c.result() for c in calls]
    assert [r.status_code for r in replies] == [201, 201]
    assert replies[0].json() == replies[1].json()

    def failed(*args, **kwargs):
        raise RuntimeError("injected assessment audit failure")

    monkeypatch.setattr(tax_assessment, "record", failed)
    with pytest.raises(RuntimeError, match="injected assessment audit failure"):
        client.post(BASE, headers=h, json={**body, "request_id": str(uuid4())})
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(TaxAssessment).where(TaxAssessment.organization_id == UUID(merchant["org"]))) == 1
