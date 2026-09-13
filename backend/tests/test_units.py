from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from app.core.config import Settings, get_settings
from app.core.idempotency import request_digest
from app.core.security import access_subject, access_token, hash_password, verify_password


def test_argon2_passwords_are_salted_and_one_way():
    first = hash_password("secure-example-password")
    second = hash_password("secure-example-password")
    assert first != second
    assert verify_password("secure-example-password", first)
    assert not verify_password("incorrect-password", first)
    assert "secure-example-password" not in first


def test_idempotency_digest_is_order_independent():
    assert request_digest({"a": 1, "b": 2}) == request_digest({"b": 2, "a": 1})


def test_access_token_signature_and_expiration():
    user_id = uuid4()
    assert access_subject(access_token(user_id)) == user_id
    expired = jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        access_subject(expired)


def test_production_rejects_wildcard_cors_and_weak_secrets():
    with pytest.raises(ValueError):
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://localhost/db",
            redis_url="redis://localhost/0",
            jwt_secret="weak",
            bootstrap_key="weak",
            cors_origins=["*"],
        )
