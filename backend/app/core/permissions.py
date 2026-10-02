from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import db_session
from app.core.exceptions import AuthenticationError, NotFoundError, PermissionDeniedError
from app.core.models import (
    Branch,
    Membership,
    MembershipRole,
    Organization,
    Permission,
    Role,
    RolePermission,
    User,
)
from app.core.security import access_subject


@dataclass(frozen=True)
class Context:
    user: User
    organization: Organization
    membership: Membership
    org_permissions: frozenset[str]
    branch_permissions: dict[UUID, frozenset[str]]

    def permits(self, code: str, branch_id: UUID | None = None) -> bool:
        return code in self.org_permissions or (
            branch_id is not None and code in self.branch_permissions.get(branch_id, frozenset())
        )

    def require(self, code: str, branch_id: UUID | None = None) -> None:
        if not self.permits(code, branch_id):
            raise PermissionDeniedError()


def current_user(
    authorization: str | None = Header(default=None), db: Session = Depends(db_session)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError()
    try:
        user_id = access_subject(authorization[7:])
    except Exception as exc:
        raise AuthenticationError() from exc
    user = db.get(User, user_id)
    if user is None or user.status != "ACTIVE":
        raise AuthenticationError()
    return user


def context(
    user: User = Depends(current_user),
    organization_id: UUID | None = Header(default=None, alias="X-Organization-ID"),
    db: Session = Depends(db_session),
) -> Context:
    if organization_id is None:
        raise AuthenticationError()
    org = db.get(Organization, organization_id)
    member = db.scalar(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user.id,
            Membership.status == "ACTIVE",
        )
    )
    if not org or org.status != "ACTIVE" or not member:
        raise NotFoundError()
    rows = db.execute(
        select(MembershipRole.branch_id, Permission.code)
        .join(Role, Role.id == MembershipRole.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(
            MembershipRole.membership_id == member.id,
            MembershipRole.organization_id == organization_id,
        )
    ).all()
    global_perms = frozenset(code for branch, code in rows if branch is None)
    scoped: dict[UUID, set[str]] = {}
    for branch, code in rows:
        if branch is not None:
            scoped.setdefault(branch, set()).add(code)
    return Context(
        user,
        org,
        member,
        global_perms,
        {branch: frozenset(codes) for branch, codes in scoped.items()},
    )


def scoped_branch(db: Session, ctx: Context, branch_id: UUID, permission: str) -> Branch:
    branch = db.scalar(
        select(Branch).where(Branch.id == branch_id, Branch.organization_id == ctx.organization.id)
    )
    if branch is None:
        raise NotFoundError()
    ctx.require(permission, branch_id)
    return branch
