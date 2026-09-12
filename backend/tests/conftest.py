import os
from uuid import uuid4

import pytest
import redis
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://merchant:merchant@localhost:5432/smart_merchant_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("JWT_SECRET", "test-secret-for-disposable-test-database-00000000")
os.environ.setdefault("BOOTSTRAP_KEY", "test-bootstrap-key-for-disposable-test-db-000000")

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    redis.Redis.from_url(os.environ["REDIS_URL"]).flushdb()
    return TestClient(app)


@pytest.fixture
def merchant(client):
    email = f"owner-{uuid4()}@example.test"
    response = client.post(
        "/api/v1/bootstrap",
        headers={"X-Bootstrap-Key": os.environ["BOOTSTRAP_KEY"]},
        json={
            "owner_name": "Owner",
            "owner_email": email,
            "owner_password": "secure-test-password-123",
            "organization_name": "Test Merchant",
        },
    )
    assert response.status_code == 201, response.text
    org = response.json()["organization"]["id"]
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "secure-test-password-123"}
    )
    assert login.status_code == 200, login.text
    return {
        "org": org,
        "email": email,
        "headers": {
            "Authorization": f"Bearer {login.json()['access_token']}",
            "X-Organization-ID": org,
        },
        "refresh": login.json()["refresh_token"],
    }
