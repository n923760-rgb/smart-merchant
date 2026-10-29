"""Account-group acceptance on disposable PostgreSQL (SM-ACC-004A)."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.models import User
from app.domains.accounting.models import Account, JournalEntry, JournalLine

BASE = "/api/v1/accounting"


def account(client, headers, code, kind, *, parent=None, postable=True):
    payload = {
        "code": code,
        "name": f"Account {code}",
        "account_type": kind,
        "is_postable": postable,
    }
    if parent is not None:
        payload["parent_id"] = parent
    return client.post(BASE + "/accounts", headers=headers, json=payload)


def journal(account_ids, *, request_id=None, amount="125.50"):
    return {
        "request_id": request_id or str(uuid4()),
        "booking_date": "2026-10-29",
        "description": "Services",
        "lines": [
            {"account_id": account_ids[0], "debit": amount},
            {"account_id": account_ids[1], "credit": amount},
        ],
    }


def test_legacy_flat_accounts_remain_postable_and_hierarchy_books_only_to_leaf(client, merchant):
    headers = merchant["headers"]
    cash = account(client, headers, "CASH10", "ASSET").json()
    revenue = account(client, headers, "REV10", "REVENUE").json()
    assert cash["parent_id"] is None and cash["is_postable"] is True
    assert revenue["is_postable"] is True
    original = client.post(
        BASE + "/journals",
        headers=headers,
        json=journal((cash["id"], revenue["id"])),
    )
    assert original.status_code == 201, original.text
    assert original.json()["total_debit"] == "125.50"
    # An existing posted journal remains verifiable after new groups are created.
    assets = account(client, headers, "G100", "ASSET", postable=False).json()
    assert assets["parent_id"] is None and assets["is_postable"] is False
    subgroup = account(
        client, headers, "G101", "ASSET", parent=assets["id"], postable=False
    ).json()
    nested = account(client, headers, "CASH11", "ASSET", parent=subgroup["id"]).json()
    assert nested["parent_id"] == subgroup["id"]
    assert nested["is_postable"] is True
    booked = client.post(
        BASE + "/journals",
        headers=headers,
        json=journal((nested["id"], revenue["id"])),
    )
    assert booked.status_code == 201, booked.text
    denied = client.post(
        BASE + "/journals",
        headers=headers,
        json=journal((assets["id"], revenue["id"])),
    )
    assert denied.status_code == 409
    assert client.get(BASE + f"/journals/{original.json()['id']}", headers=headers).json() == (
        original.json()
    )
    assert client.get(BASE + "/accounts", headers=headers).status_code == 200


def test_parent_must_be_active_nonpostable_and_same_kind(client, merchant):
    headers = merchant["headers"]
    leaf = account(client, headers, "P200", "ASSET").json()
    group = account(client, headers, "P201", "ASSET", postable=False).json()
    assert account(client, headers, "P202", "ASSET", parent=leaf["id"]).status_code == 409
    assert account(client, headers, "P203", "LIABILITY", parent=group["id"]).status_code == 409
    with SessionLocal() as db:
        parent = db.get(Account, UUID(group["id"]))
        assert parent is not None
        parent.is_active = False
        db.commit()
    assert account(client, headers, "P204", "ASSET", parent=group["id"]).status_code == 409


def test_account_parent_is_tenant_scoped_and_cannot_be_written_by_cashier(client, merchant):
    h = merchant["headers"]
    group = account(client, h, "T100", "ASSET", postable=False).json()
    email = f"other-org-{uuid4()}@example.com"
    registration = client.post(
        "/api/v1/bootstrap",
        headers={"X-Bootstrap-Key": get_settings().bootstrap_key},
        json={
            "owner_name": "Other Owner",
            "owner_email": email,
            "owner_password": "hierarchy-disposable-password",
            "organization_name": "Other Organization",
        },
    )
    assert registration.status_code == 201, registration.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "hierarchy-disposable-password"},
    )
    assert login.status_code == 200
    other_headers = {
        "Authorization": "Bearer " + login.json()["access_token"],
        "X-Organization-ID": registration.json()["organization"]["id"],
    }
    assert account(
        client, other_headers, "T101", "ASSET", parent=group["id"]
    ).status_code == 404

    # Cashier grants do not imply global account-management access.
    cashier_email = f"cashier-{uuid4()}@example.com"
    invitation = client.post(
        "/api/v1/users",
        headers=h,
        json={
            "name": "Cashier",
            "email": cashier_email,
            "password": "hierarchy-disposable-password",
        },
    )
    assert invitation.status_code == 201
    roles = client.get("/api/v1/roles", headers=h, params={"page_size": 100}).json()["items"]
    cashier_role = next(x for x in roles if x["code"] == "CASHIER")
    assignment = client.post(
        f"/api/v1/users/{invitation.json()['id']}/roles",
        headers=h,
        json={"role_id": cashier_role["id"], "branch_id": None},
    )
    assert assignment.status_code == 201
    cashier_login = client.post(
        "/api/v1/auth/login",
        json={"email": cashier_email, "password": "hierarchy-disposable-password"},
    )
    assert cashier_login.status_code == 200
    restricted = {
        "Authorization": "Bearer " + cashier_login.json()["access_token"],
        "X-Organization-ID": merchant["org"],
    }
    assert account(client, restricted, "T102", "ASSET", parent=group["id"]).status_code == 403


@pytest.mark.parametrize(
    "mutate",
    [
        lambda a, other: setattr(a, "is_postable", True),
        lambda a, other: setattr(a, "account_type", "LIABILITY"),
        lambda a, other: setattr(a, "parent_id", UUID(other)),
    ],
)
def test_database_rejects_account_structure_mutation(client, merchant, mutate):
    headers = merchant["headers"]
    group = account(client, headers, "M100", "ASSET", postable=False).json()
    other = account(client, headers, "M101", "ASSET", postable=False).json()
    with SessionLocal() as db:
        target = db.get(Account, UUID(group["id"]))
        assert target is not None
        mutate(target, other["id"])
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()


def test_database_rejects_invalid_parent_even_without_api(client, merchant):
    headers = merchant["headers"]
    leaf = account(client, headers, "D100", "ASSET").json()
    with SessionLocal() as db:
        db.add(
            Account(
                organization_id=UUID(merchant["org"]),
                code="D101",
                name="Forbidden child",
                account_type="ASSET",
                is_active=True,
                is_postable=True,
                parent_id=UUID(leaf["id"]),
            )
        )
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()


def test_database_denies_direct_journal_lines_for_summary_accounts(client, merchant):
    headers = merchant["headers"]
    group = account(client, headers, "J100", "ASSET", postable=False).json()
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    with SessionLocal() as db:
        entry = JournalEntry(
            organization_id=UUID(merchant["org"]),
            branch_id=None,
            request_id=uuid4(),
            request_hash="0" * 64,
            booking_date=date(2026, 10, 29),
            description="Rejected direct SQL summary posting",
            currency="SAR",
            status="DRAFT",
            posted_by=UUID(me.json()["id"]),
        )
        db.add(entry)
        db.flush()
        db.add(
            JournalLine(
                organization_id=UUID(merchant["org"]),
                entry_id=entry.id,
                account_id=UUID(group["id"]),
                line_number=1,
                debit=Decimal("10.00"),
                credit=Decimal("0.00"),
                description=None,
            )
        )
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count()).select_from(JournalEntry).where(
                    JournalEntry.organization_id == UUID(merchant["org"])
                )
            )
            == 0
        )
