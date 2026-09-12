"""Tenant-aware replay guard for future state-changing APIs.

The caller is responsible for using the same database transaction for domain writes
and the completed response. A failed operation must roll the whole transaction back.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.core.models import IdempotencyKey


def request_digest(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def replay(
    db: Session, organization_id: UUID, key: str, operation: str, digest: str
) -> dict | None:
    if not key or len(key) > 200:
        raise ConflictError()
    row = db.scalar(
        select(IdempotencyKey)
        .where(
            IdempotencyKey.organization_id == organization_id,
            IdempotencyKey.key == key,
            IdempotencyKey.operation == operation,
        )
        .with_for_update()
    )
    if row is None:
        return None
    if row.request_hash != digest or row.expires_at <= datetime.now(timezone.utc):
        raise ConflictError()
    return row.response_data


def remember(
    db: Session,
    organization_id: UUID,
    key: str,
    operation: str,
    digest: str,
    response: dict,
    hours: int = 24,
) -> None:
    db.add(
        IdempotencyKey(
            organization_id=organization_id,
            key=key,
            operation=operation,
            request_hash=digest,
            response_data=response,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
        )
    )
