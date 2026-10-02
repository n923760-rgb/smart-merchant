from uuid import UUID

from sqlalchemy.orm import Session

from app.core.models import AuditLog


def record(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    organization_id: UUID | None,
    user_id: UUID | None,
    *,
    branch_id: UUID | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            organization_id=organization_id,
            user_id=user_id,
            branch_id=branch_id,
            before_data=before,
            after_data=after,
        )
    )
