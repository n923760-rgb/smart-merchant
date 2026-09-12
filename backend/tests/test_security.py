from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.models import AuditLog, User


def test_expired_access_token(client, merchant):
    user_id = client.get("/api/v1/auth/me", headers=merchant["headers"]).json()["id"]
    token = jwt.encode(
        {
            "sub": user_id,
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code
        == 401
    )


def test_disabled_user_rejected(client, merchant):
    user_id = UUID(client.get("/api/v1/auth/me", headers=merchant["headers"]).json()["id"])
    with SessionLocal.begin() as db:
        db.get(User, user_id).status = "DISABLED"
    assert client.get("/api/v1/auth/me", headers=merchant["headers"]).status_code == 401
    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": merchant["refresh"]}).status_code
        == 401
    )


def test_audit_database_is_append_only(client, merchant):
    from sqlalchemy import select
    from sqlalchemy.exc import DBAPIError

    with SessionLocal() as db:
        log = db.scalar(select(AuditLog).where(AuditLog.organization_id == UUID(merchant["org"])))
        assert log is not None
        log.action = "TAMPERED"
        try:
            db.commit()
        except DBAPIError:
            db.rollback()
        else:
            raise AssertionError("Audit mutation unexpectedly succeeded")
