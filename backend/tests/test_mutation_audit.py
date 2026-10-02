"""Tenant-safe success audit and rollback proof for membership/terminal mutations."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import routes
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.models import (
    AuditLog,
    Membership,
    MembershipRole,
    Permission,
    Role,
    RolePermission,
    Terminal,
    User,
)

PASSWORD = "audit-disposable-password-123"


def invite(client, headers, email=None):
    email = email or f"audit-{uuid4()}@example.com"
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={"name": "Fixture employee", "email": email, "password": PASSWORD},
    )
    return response, email


def terminal(client, headers, code):
    branch = client.post(
        "/api/v1/branches", headers=headers, json={"name": code, "code": code}
    )
    assert branch.status_code == 201, branch.text
    response = client.post(
        "/api/v1/terminals",
        headers=headers,
        json={
            "name": "Front desk",
            "branch_id": branch.json()["id"],
            "device_identifier": str(uuid4()),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def events(organization, action):
    with SessionLocal() as db:
        return list(db.scalars(select(AuditLog).where(
            AuditLog.organization_id == UUID(organization), AuditLog.action == action
        )))


def other_merchant(client):
    email = f"audit-owner-{uuid4()}@example.com"
    response = client.post(
        "/api/v1/bootstrap",
        headers={"X-Bootstrap-Key": get_settings().bootstrap_key},
        json={
            "owner_name": "Other owner",
            "owner_email": email,
            "owner_password": PASSWORD,
            "organization_name": "Other merchant",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    return data, {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Organization-ID": data["organization"]["id"],
    }


def test_new_invitation_records_membership_actor_and_minimal_snapshot(client, merchant):
    response, email = invite(client, merchant["headers"])
    assert response.status_code == 201, response.text
    data = response.json()
    actor = client.get("/api/v1/auth/me", headers=merchant["headers"]).json()["id"]
    rows = events(merchant["org"], "USER_INVITED")
    assert len(rows) == 1
    event = rows[0]
    assert event.entity_type == "membership"
    assert event.entity_id == UUID(data["membership_id"])
    assert event.user_id == UUID(actor)
    assert event.branch_id is None and event.before_data is None
    assert event.after_data == {"user_id": data["id"], "status": "ACTIVE"}
    assert event.metadata_ is None
    assert PASSWORD not in str(event.after_data)
    assert email not in str(event.after_data)
    duplicate, _ = invite(client, merchant["headers"], email)
    assert duplicate.status_code == 409
    assert len(events(merchant["org"], "USER_INVITED")) == 1
    visible = client.get("/api/v1/audit", headers=merchant["headers"]).json()["items"]
    assert any(row["id"] == str(event.id) for row in visible)


def test_existing_user_invitation_does_not_copy_other_tenant_or_change_credentials(
    client, merchant
):
    other, headers = other_merchant(client)
    existing = other["owner"]
    with SessionLocal() as db:
        user = db.get(User, UUID(existing["id"]))
        original_hash = user.password_hash
    response, _ = invite(client, merchant["headers"], existing["email"])
    assert response.status_code == 201, response.text
    assert response.json()["id"] == existing["id"]
    assert response.json()["name"] == existing["name"]
    with SessionLocal() as db:
        user = db.get(User, UUID(existing["id"]))
        assert user.password_hash == original_hash
    rows = events(merchant["org"], "USER_INVITED")
    assert len(rows) == 1
    assert rows[0].after_data == {"user_id": existing["id"], "status": "ACTIVE"}
    assert events(other["organization"]["id"], "USER_INVITED") == []
    foreign_visible = client.get("/api/v1/audit", headers=headers).json()["items"]
    assert str(rows[0].id) not in {row["id"] for row in foreign_visible}


def test_terminal_rename_snapshots_and_noop_are_explicit_commands(client, merchant):
    device = terminal(client, merchant["headers"], "AUD01")
    actor = client.get("/api/v1/auth/me", headers=merchant["headers"]).json()["id"]
    for name in ("Coffee bar", "Pickup", "Pickup"):
        response = client.patch(
            f"/api/v1/terminals/{device['id']}",
            headers=merchant["headers"],
            json={"name": name},
        )
        assert response.status_code == 200, response.text
    rows = events(merchant["org"], "TERMINAL_RENAMED")
    assert len(rows) == 3
    assert sorted((row.before_data["name"], row.after_data["name"]) for row in rows) == [
        ("Coffee bar", "Pickup"), ("Front desk", "Coffee bar"), ("Pickup", "Pickup")
    ]
    for row in rows:
        assert row.entity_type == "terminal"
        assert row.entity_id == UUID(device["id"])
        assert row.branch_id == UUID(device["branch_id"])
        assert row.user_id == UUID(actor)
        assert set(row.before_data) == {"name"} and set(row.after_data) == {"name"}


def test_foreign_terminal_rename_is_not_found_and_creates_no_event(client, merchant):
    device = terminal(client, merchant["headers"], "AUD02")
    other, headers = other_merchant(client)
    response = client.patch(
        f"/api/v1/terminals/{device['id']}", headers=headers, json={"name": "Foreign"}
    )
    assert response.status_code == 404
    assert events(merchant["org"], "TERMINAL_RENAMED") == []
    assert events(other["organization"]["id"], "TERMINAL_RENAMED") == []
    with SessionLocal() as db:
        assert db.get(Terminal, UUID(device["id"])).name == "Front desk"


def test_branch_permission_cannot_rename_other_branch_or_invite_globally(client, merchant):
    first = terminal(client, merchant["headers"], "AUD03")
    second = terminal(client, merchant["headers"], "AUD04")
    response, email = invite(client, merchant["headers"])
    assert response.status_code == 201
    member = response.json()
    with SessionLocal.begin() as db:
        role = Role(organization_id=UUID(merchant["org"]), code="AUDIT_TEST", name="Fixture")
        db.add(role)
        db.flush()
        permissions = db.scalars(select(Permission).where(
            Permission.code.in_(["terminals.manage", "users.invite"])
        ))
        for permission in permissions:
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        db.add(MembershipRole(
            organization_id=UUID(merchant["org"]),
            membership_id=UUID(member["membership_id"]),
            role_id=role.id,
            branch_id=UUID(first["branch_id"]),
        ))
    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Organization-ID": merchant["org"],
    }
    assert client.patch(
        f"/api/v1/terminals/{first['id']}", headers=headers, json={"name": "Allowed"}
    ).status_code == 200
    assert client.patch(
        f"/api/v1/terminals/{second['id']}", headers=headers, json={"name": "Denied"}
    ).status_code == 403
    denied, denied_email = invite(client, headers)
    assert denied.status_code == 403
    assert len(events(merchant["org"], "USER_INVITED")) == 1
    assert len(events(merchant["org"], "TERMINAL_RENAMED")) == 1
    with SessionLocal() as db:
        assert db.scalar(select(User.id).where(User.email == denied_email)) is None
        assert db.get(Terminal, UUID(second["id"])).name == "Front desk"


@pytest.mark.parametrize("operation", ["invite", "rename"])
def test_audit_failure_rolls_back_the_business_mutation(client, merchant, monkeypatch, operation):
    original = routes.record
    action = "USER_INVITED" if operation == "invite" else "TERMINAL_RENAMED"

    def invalid_actor(db, event_action, entity_type, entity_id, organization_id, user_id, **kwargs):
        original(
            db, event_action, entity_type, entity_id, organization_id,
            uuid4() if event_action == action else user_id, **kwargs
        )

    monkeypatch.setattr(routes, "record", invalid_actor)
    if operation == "invite":
        response, email = invite(client, merchant["headers"])
        assert response.status_code == 409
        with SessionLocal() as db:
            assert db.scalar(select(User.id).where(User.email == email)) is None
    else:
        device = terminal(client, merchant["headers"], "AUD05")
        response = client.patch(
            f"/api/v1/terminals/{device['id']}",
            headers=merchant["headers"],
            json={"name": "Must roll back"},
        )
        assert response.status_code == 409
        with SessionLocal() as db:
            assert db.get(Terminal, UUID(device["id"])).name == "Front desk"
    assert events(merchant["org"], action) == []


def test_membership_flush_conflict_remains_409_without_success_audit(client, merchant, monkeypatch):
    original_flush = Session.flush
    injected = False

    def duplicate_membership(db, objects=None):
        nonlocal injected
        member = next((row for row in db.new if isinstance(row, Membership)), None)
        if member is not None and not injected:
            injected = True
            db.add(Membership(
                user_id=member.user_id, organization_id=member.organization_id
            ))
        return original_flush(db, objects)

    monkeypatch.setattr(Session, "flush", duplicate_membership)
    response, email = invite(client, merchant["headers"])
    assert injected
    assert response.status_code == 409
    assert events(merchant["org"], "USER_INVITED") == []
    with SessionLocal() as db:
        assert db.scalar(select(User.id).where(User.email == email)) is None
