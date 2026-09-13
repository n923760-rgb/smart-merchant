import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.models import RefreshSession

hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except VerificationError:
        return False


def now() -> datetime:
    return datetime.now(timezone.utc)


def access_token(user_id: UUID) -> str:
    settings = get_settings()
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "exp": now() + timedelta(seconds=settings.jwt_access_ttl),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def access_subject(token: str) -> UUID:
    payload = jwt.decode(
        token,
        get_settings().jwt_secret,
        algorithms=["HS256"],
        options={"require": ["exp", "sub", "type"]},
    )
    if payload["type"] != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    return UUID(payload["sub"])


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_refresh(db: Session, user_id: UUID) -> str:
    token = secrets.token_urlsafe(48)
    db.add(
        RefreshSession(
            user_id=user_id,
            token_hash=token_digest(token),
            expires_at=now() + timedelta(seconds=get_settings().jwt_refresh_ttl),
        )
    )
    return token


def revoke_refresh(db: Session, token: str, user_id: UUID) -> None:
    session = db.scalar(
        select(RefreshSession)
        .where(RefreshSession.token_hash == token_digest(token), RefreshSession.user_id == user_id)
        .with_for_update()
    )
    if session and session.revoked_at is None:
        session.revoked_at = now()


def rotate_refresh(db: Session, token: str) -> tuple[UUID, str] | None:
    session = db.scalar(
        select(RefreshSession)
        .where(RefreshSession.token_hash == token_digest(token))
        .with_for_update()
    )
    if not session or session.revoked_at or session.expires_at <= now():
        return None
    session.revoked_at = now()
    return session.user_id, issue_refresh(db, session.user_id)
