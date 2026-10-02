"""Logout must terminate its refresh capability independently of access expiry."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.models import AuditLog, RefreshSession, User
from app.core.security import token_digest


@pytest.mark.parametrize("access_state", ["expired", "missing"])
def test_logout_revokes_refresh_after_access_expiry(client, merchant, access_state):
    user_id = client.get("/api/v1/auth/me", headers=merchant["headers"]).json()["id"]
    expired = jwt.encode(
        {
            "sub": user_id,
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {expired}"} if access_state == "expired" else {}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    response = client.post(
        "/api/v1/auth/logout", headers=headers, json={"refresh_token": merchant["refresh"]}
    )
    assert response.status_code == 204
    assert response.content == b""
    assert client.post(
        "/api/v1/auth/refresh", json={"refresh_token": merchant["refresh"]}
    ).status_code == 401
    with SessionLocal() as db:
        session = db.scalar(select(RefreshSession).where(
            RefreshSession.token_hash == token_digest(merchant["refresh"])
        ))
        assert session is not None and session.revoked_at is not None
        event = db.scalar(select(AuditLog).where(
            AuditLog.action == "USER_LOGOUT", AuditLog.entity_id == session.id
        ))
        assert event is not None and event.user_id == UUID(user_id)
        assert event.before_data is None and event.after_data is None


def test_logout_is_idempotent_and_unknown_token_does_not_revoke_other_session(client, merchant):
    second = client.post(
        "/api/v1/auth/login",
        json={"email": merchant["email"], "password": "secure-test-password-123"},
    ).json()["refresh_token"]
    payload = {"refresh_token": merchant["refresh"]}
    for candidate in (payload, payload, {"refresh_token": "unknown-disposable-fixture"}):
        assert client.post("/api/v1/auth/logout", json=candidate).status_code == 204
    with SessionLocal() as db:
        session = db.scalar(select(RefreshSession).where(
            RefreshSession.token_hash == token_digest(merchant["refresh"])
        ))
        assert session is not None
        assert db.scalar(select(func.count(AuditLog.id)).where(
            AuditLog.action == "USER_LOGOUT", AuditLog.entity_id == session.id
        )) == 1
    assert client.post("/api/v1/auth/refresh", json=payload).status_code == 401
    assert client.post(
        "/api/v1/auth/refresh", json={"refresh_token": second}
    ).status_code == 200


def test_logout_capability_does_not_depend_on_active_user(client, merchant):
    user_id = UUID(client.get("/api/v1/auth/me", headers=merchant["headers"]).json()["id"])
    with SessionLocal.begin() as db:
        user = db.get(User, user_id)
        assert user is not None
        user.status = "DISABLED"
    assert client.post(
        "/api/v1/auth/logout", json={"refresh_token": merchant["refresh"]}
    ).status_code == 204
    with SessionLocal() as db:
        session = db.scalar(select(RefreshSession).where(
            RefreshSession.token_hash == token_digest(merchant["refresh"])
        ))
        assert session is not None and session.revoked_at is not None
