from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from test_customers import foreign_headers, role_headers
from test_tax_assessments import BASE as ASSESSMENTS
from test_tax_assessments import prepare as tax_prepare
from test_tax_profiles import body as profile_body

from app.core.database import SessionLocal
from app.core.models import AuditLog, Organization, Permission, Role, RolePermission
from app.domains.accounting.models import Account, JournalEntry, JournalLine
from app.domains.billing import charges
from app.domains.billing.models import ServiceCharge

BASE = "/api/v1/billing/service-charges"


def prepare(client, h, *, lines=None, future=0):
    tax_body, _ = tax_prepare(client, h, lines=lines)
    tax_body["assessment_date"] = profile_body(future)["effective_from"]
    assessment = client.post(ASSESSMENTS, headers=h, json=tax_body)
    assert assessment.status_code == 201, assessment.text
    customer = client.post("/api/v1/customers", headers=h, json={"request_id": str(uuid4()), "display_name": "Selected customer"})
    assert customer.status_code == 201, customer.text
    mapping = {}
    for field, kind in (("receivable", "ASSET"), ("revenue", "REVENUE"), ("tax", "LIABILITY")):
        account = client.post("/api/v1/accounting/accounts", headers=h, json={"code": uuid4().hex[:12].upper(), "name": kind, "account_type": kind})
        assert account.status_code == 201, account.text
        mapping[field + "_account_id"] = account.json()["id"]
    return {"request_id": str(uuid4()), "assessment_id": assessment.json()["id"],
            "customer_id": customer.json()["id"], "booking_date": tax_body["assessment_date"],
            "approval_basis": "Customer and source reviewed for internal accounting", "confirm": True, **mapping}


def counts(org):
    with SessionLocal() as db:
        return {m.__tablename__: db.scalar(select(func.count()).select_from(m).where(m.organization_id == UUID(org)))
                for m in (ServiceCharge, JournalEntry, JournalLine, AuditLog)}


def post(client, h, body):
    response = client.post(BASE, headers=h, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_atomic_charge_reconciles_customer_source_journal_and_recovery(client, merchant):
    h = merchant["headers"]
    body = prepare(client, h)
    row = post(client, h, body)
    assert row["status"] == "POSTED" and row["document_kind"] == "INTERNAL_SERVICE_CHARGE"
    assert row["can_issue_tax_invoice"] is False
    assert (row["net_amount"], row["tax_amount"], row["original_amount"]) == ("34.99", "5.25", "40.24")
    assert row["customer_id"] == body["customer_id"]
    journal = client.get("/api/v1/accounting/journals/" + row["journal_id"], headers=h).json()
    assert journal["total_debit"] == journal["total_credit"] == "40.24"
    assert journal["branch_id"] is None and journal["booking_date"] == body["booking_date"]
    assert [(line["account_id"], line["debit"], line["credit"]) for line in journal["lines"]] == [
        (body["receivable_account_id"], "40.24", "0.00"), (body["revenue_account_id"], "0.00", "34.99"),
        (body["tax_account_id"], "0.00", "5.25")]
    before = counts(merchant["org"])
    assert post(client, h, body) == row
    assert client.get(BASE + "/" + row["id"], headers=h).json() == row
    assert client.get("/api/v1/billing/service-charge-requests/" + body["request_id"], headers=h).json() == row
    assert counts(merchant["org"]) == before
    with SessionLocal() as db:
        event = db.scalar(select(AuditLog).where(AuditLog.entity_id == UUID(row["id"])))
        assert set(event.after_data) == {"request_id", "draft_id", "assessment_id", "customer_id", "journal_id"}
        assert body["approval_basis"] not in str(event.after_data)


def test_different_request_or_reassessment_cannot_repeat_source_effect(client, merchant):
    h = merchant["headers"]; body = prepare(client, h); row = post(client, h, body)
    assessment = client.get(ASSESSMENTS + "/" + body["assessment_id"], headers=h).json()
    reassessed = client.post(ASSESSMENTS, headers=h, json={"request_id": str(uuid4()), "draft_id": row["draft_id"],
        "assessment_date": body["booking_date"], "category": "STANDARD_15", "classification_basis": "New review"})
    assert reassessed.status_code == 201
    before = counts(merchant["org"])
    for new_assessment in (assessment["id"], reassessed.json()["id"]):
        assert client.post(BASE, headers=h, json={**body, "request_id": str(uuid4()), "assessment_id": new_assessment}).status_code == 409
    assert client.post(BASE, headers=h, json={**body, "approval_basis": "Different"}).status_code == 409
    assert counts(merchant["org"]) == before


@pytest.mark.parametrize("extra", [{"confirm": False}, {"approval_basis": " "}, {"original_amount": "1.00"}, {"organization_id": str(uuid4())}, {"journal_id": str(uuid4())}, {"branch_id": str(uuid4())}])
def test_strict_approval_and_server_fields(client, merchant, extra):
    body = prepare(client, merchant["headers"])
    assert client.post(BASE, headers=merchant["headers"], json={**body, **extra}).status_code == 422


@pytest.mark.parametrize("field", ["assessment_id", "customer_id", "receivable_account_id", "revenue_account_id", "tax_account_id"])
def test_foreign_references_and_charge_recovery_are_scoped(client, merchant, field):
    h = merchant["headers"]; body = prepare(client, h)
    other_h = foreign_headers(client); other = prepare(client, other_h)
    row = post(client, other_h, other)
    before = counts(merchant["org"])
    assert client.post(BASE, headers=h, json={**body, field: other[field]}).status_code == 404
    assert client.get(BASE + "/" + row["id"], headers=h).status_code == 404
    assert client.get("/api/v1/billing/service-charge-requests/" + other["request_id"], headers=h).status_code == 404
    assert counts(merchant["org"]) == before


@pytest.mark.parametrize("role,branch_only,read_status", [("ACCOUNTANT", False, 200), ("ACCOUNTANT", True, 403), ("CASHIER", False, 403)])
def test_global_owner_approval_and_scoped_read_permissions(client, merchant, role, branch_only, read_status):
    h = merchant["headers"]; body = prepare(client, h); row = post(client, h, body)
    branch = None
    if branch_only:
        branch = client.post("/api/v1/branches", headers=h, json={"name": "Abha", "code": "ABH01"}).json()["id"]
    restricted = role_headers(client, merchant, role, branch)
    assert client.post(BASE, headers=restricted, json=body).status_code == 403
    assert client.get(BASE + "/" + row["id"], headers=restricted).status_code == read_status


@pytest.mark.parametrize("permission", ["billing.charges.read", "billing.charges.approve", "billing.drafts.read", "billing.tax.read", "customers.read", "accounting.accounts.read", "accounting.journals.post"])
def test_each_permission_required_even_for_replay(client, merchant, permission):
    h = merchant["headers"]; body = prepare(client, h); post(client, h, body)
    with SessionLocal.begin() as db:
        role = db.scalar(select(Role.id).where(Role.organization_id == UUID(merchant["org"]), Role.code == "OWNER"))
        pid = db.scalar(select(Permission.id).where(Permission.code == permission))
        db.delete(db.get(RolePermission, (role, pid)))
    assert client.post(BASE, headers=h, json=body).status_code == 403


@pytest.mark.parametrize("condition", ["inactive", "wrong_type", "summary", "currency", "date", "future", "stale_profile"])
def test_recheck_configuration_and_mapping(client, merchant, condition):
    h = merchant["headers"]; body = prepare(client, h, future=2 if condition in {"future", "stale_profile"} else 0)
    if condition == "inactive":
        with SessionLocal.begin() as db:
            db.get(Account, UUID(body["tax_account_id"])).is_active = False
    elif condition in {"wrong_type", "summary"}:
        a = client.post("/api/v1/accounting/accounts", headers=h, json={"code": uuid4().hex[:12].upper(), "name": "Bad", "account_type": "ASSET", "is_postable": condition != "summary"})
        body["tax_account_id"] = a.json()["id"]
    elif condition == "currency":
        with SessionLocal.begin() as db:
            db.get(Organization, UUID(merchant["org"])).currency = "USD"
    elif condition == "date":
        body["booking_date"] = (date.fromisoformat(body["booking_date"]) - timedelta(days=1)).isoformat()
    elif condition == "stale_profile":
        response = client.post("/api/v1/billing/tax-profiles", headers=h, json=profile_body(1))
        assert response.status_code == 201
    before = counts(merchant["org"])
    assert client.post(BASE, headers=h, json=body).status_code == 409
    assert counts(merchant["org"]) == before


def test_closed_period_cutover_replay_and_generic_uuid_collision(client, merchant):
    h = merchant["headers"]; body = prepare(client, h)
    opening = client.post("/api/v1/accounting/opening-balance", headers=h, json={
        "request_id": str(uuid4()), "booking_date": body["booking_date"], "description": "Opening",
        "lines": [{"account_id": body["receivable_account_id"], "debit": "1.00"}, {"account_id": body["revenue_account_id"], "credit": "1.00"}]})
    assert opening.status_code == 201, opening.text
    assert client.post(BASE, headers=h, json=body).status_code == 409
    # Collision is caught before cutover and cannot adopt another operation's journal.
    journal_id = opening.json()["journal"]["request_id"]
    assert client.post(BASE, headers=h, json={**body, "request_id": journal_id}).status_code == 409


def test_close_after_posting_allows_replay_but_not_new_source_effect(client, merchant):
    h = merchant["headers"]; body = prepare(client, h); row = post(client, h, body)
    period = client.post("/api/v1/accounting/periods", headers=h, json={"start_date": body["booking_date"], "end_date": body["booking_date"]})
    assert period.status_code == 201
    assert client.post("/api/v1/accounting/periods/" + period.json()["id"] + "/close", headers=h).status_code == 200
    assert post(client, h, body) == row
    # Use another immutable source under the same existing registered profile.
    from test_service_billing_drafts import draft_payload
    draft = client.post("/api/v1/billing/service-drafts", headers=h, json=draft_payload()).json()
    a = client.post(ASSESSMENTS, headers=h, json={"request_id": str(uuid4()), "draft_id": draft["id"], "assessment_date": body["booking_date"], "category": "STANDARD_15", "classification_basis": "Reviewed"})
    assert a.status_code == 201
    assert client.post(BASE, headers=h, json={**body, "request_id": str(uuid4()), "assessment_id": a.json()["id"]}).status_code == 409


def test_tiny_tax_rounds_to_zero_and_generic_reversal_is_blocked(client, merchant):
    h = merchant["headers"]; body = prepare(client, h, lines=[{"service_name": "Tiny", "quantity": "1", "unit_price": "0.01"}])
    row = post(client, h, body)
    assert row["original_amount"] == "0.01" and row["tax_amount"] == "0.00"
    response = client.post("/api/v1/accounting/journals/" + row["journal_id"] + "/reverse", headers=h,
        json={"request_id": str(uuid4()), "booking_date": body["booking_date"], "reason": "Cannot orphan AR"})
    assert response.status_code == 409, response.text
    with SessionLocal() as db:
        original = db.get(JournalEntry, UUID(row["journal_id"]))
        db.add(JournalEntry(organization_id=original.organization_id, request_id=uuid4(), request_hash="a" * 64,
            booking_date=original.booking_date, description="SQL reversal", currency="SAR", status="DRAFT",
            reversal_of_id=original.id, posted_by=original.posted_by))
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


@pytest.mark.parametrize("action", ["update", "delete", "source", "account", "journal", "customer"])
def test_sql_immutability_tenant_and_reconciliation(client, merchant, action):
    h = merchant["headers"]; body = prepare(client, h); row = post(client, h, body)
    with SessionLocal() as db:
        charge = db.get(ServiceCharge, UUID(row["id"]))
        if action == "update":
            charge.approval_basis = "Mutated"
        elif action == "delete":
            db.delete(charge)
        else:
            values = {c.name: getattr(charge, c.name) for c in ServiceCharge.__table__.columns if c.name not in {"id", "created_at"}}
            values.update(request_id=uuid4())
            field = {"source": "draft_id", "account": "tax_account_id", "journal": "journal_id", "customer": "customer_id"}[action]
            values[field] = uuid4()
            db.add(ServiceCharge(**values))
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_simultaneous_different_requests_post_source_once_and_audit_failure_rolls_back(client, merchant, monkeypatch):
    h = merchant["headers"]; body = prepare(client, h)
    before = counts(merchant["org"])
    def failed(*args, **kwargs):
        raise RuntimeError("injected charge audit failure")
    with monkeypatch.context() as m:
        m.setattr(charges, "record", failed)
        with pytest.raises(RuntimeError, match="injected charge audit failure"):
            client.post(BASE, headers=h, json=body)
    assert counts(merchant["org"]) == before
    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = [pool.submit(client.post, BASE, headers=h, json={**body, "request_id": str(uuid4())}) for _ in range(2)]
        assert sorted(c.result().status_code for c in calls) == [201, 409]
    after = counts(merchant["org"])
    assert after["service_charges"] == before["service_charges"] + 1
    assert after["journal_entries"] == before["journal_entries"] + 1
    assert after["audit_logs"] == before["audit_logs"] + 2


@pytest.mark.parametrize("mismatch", ["amount", "request", "date", "source", "account"])
def test_sql_new_charge_cannot_adopt_nonmatching_posted_journal(client, merchant, mismatch):
    h = merchant["headers"]; body = prepare(client, h)
    assessment = client.get(ASSESSMENTS + "/" + body["assessment_id"], headers=h).json()
    journal_payload = {"request_id": body["request_id"], "booking_date": body["booking_date"], "description": "Direct SQL qualification",
        "lines": [{"account_id": body["receivable_account_id"], "debit": "40.24"},
                  {"account_id": body["revenue_account_id"], "credit": "34.99"},
                  {"account_id": body["tax_account_id"], "credit": "5.25"}]}
    if mismatch == "amount":
        journal_payload["lines"][0]["debit"] = "41.24"
        journal_payload["lines"][1]["credit"] = "35.99"
    journal = client.post("/api/v1/accounting/journals", headers=h, json=journal_payload)
    assert journal.status_code == 201, journal.text
    with SessionLocal() as db:
        j = db.get(JournalEntry, UUID(journal.json()["id"]))
        values = {k: UUID(body[k]) for k in ("assessment_id", "customer_id", "receivable_account_id", "revenue_account_id", "tax_account_id")}
        values.update(organization_id=j.organization_id, draft_id=UUID(assessment["draft_id"]), journal_id=j.id,
            request_id=j.request_id, request_hash=j.request_hash, booking_date=j.booking_date,
            approval_basis="SQL guard qualification", created_by=j.posted_by)
        if mismatch == "request":
            values["request_id"] = uuid4()
        elif mismatch == "date":
            values["booking_date"] = j.booking_date - timedelta(days=1)
        elif mismatch == "source":
            values["draft_id"] = uuid4()
        elif mismatch == "account":
            values["tax_account_id"] = values["receivable_account_id"]
        db.add(ServiceCharge(**values))
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
    assert counts(merchant["org"])["service_charges"] == 0


def test_simultaneous_same_request_returns_one_identical_charge(client, merchant):
    h = merchant["headers"]; body = prepare(client, h)
    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = [pool.submit(client.post, BASE, headers=h, json=body) for _ in range(2)]
        replies = [call.result() for call in calls]
    assert [r.status_code for r in replies] == [201, 201]
    assert replies[0].json() == replies[1].json()
