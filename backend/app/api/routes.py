import hmac
from datetime import datetime, timezone
from uuid import UUID

import redis
from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas import (
    AssignRoleIn,
    BootstrapIn,
    BranchIn,
    BranchPatch,
    LoginIn,
    OrganizationPatch,
    RefreshIn,
    TerminalIn,
    TerminalPatch,
    UserIn,
    page_of,
)
from app.core.audit import record
from app.core.config import get_settings
from app.core.database import db_session
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitedError,
)
from app.core.models import (
    AuditLog,
    Branch,
    BranchSettings,
    Membership,
    MembershipRole,
    Organization,
    Permission,
    Role,
    RolePermission,
    Terminal,
    User,
)
from app.core.permissions import Context, context, current_user, scoped_branch
from app.core.security import (
    access_token,
    hash_password,
    issue_refresh,
    revoke_refresh,
    rotate_refresh,
    verify_password,
)

router = APIRouter(prefix="/api/v1")

PERMISSIONS = (
    "organization.read",
    "organization.manage",
    "branches.read",
    "branches.create",
    "branches.update",
    "users.read",
    "users.invite",
    "users.manage",
    "roles.read",
    "roles.manage",
    "terminals.read",
    "terminals.manage",
    "audit.read",
)
ROLES = ("OWNER", "ADMIN", "MANAGER", "ACCOUNTANT", "SUPERVISOR", "CASHIER", "INVENTORY_MANAGER")


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError() from exc


def limiter(key: str, limit: int = 10) -> None:
    client = redis.Redis.from_url(get_settings().redis_url)
    count = client.incr(key)
    if count == 1:
        client.expire(key, 60)
    if count > limit:
        raise RateLimitedError()


def branch_dict(branch: Branch) -> dict:
    return {
        "id": str(branch.id),
        "organization_id": str(branch.organization_id),
        "name": branch.name,
        "code": branch.code,
        "city": branch.city,
        "region": branch.region,
        "status": branch.status,
    }


def user_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "status": user.status,
    }


def terminal_dict(terminal: Terminal) -> dict:
    return {
        "id": str(terminal.id),
        "name": terminal.name,
        "branch_id": str(terminal.branch_id),
        "activation_status": terminal.activation_status,
        "last_seen_at": terminal.last_seen_at.isoformat() if terminal.last_seen_at else None,
        "app_version": terminal.app_version,
    }


def organization_dict(org: Organization) -> dict:
    return {
        "id": str(org.id),
        "name": org.name,
        "status": org.status,
        "currency": org.currency,
        "timezone": org.timezone,
    }


@router.post("/bootstrap", status_code=201)
def bootstrap(
    payload: BootstrapIn,
    request: Request,
    bootstrap_key: str = Header(alias="X-Bootstrap-Key"),
    db: Session = Depends(db_session),
):
    limiter(f"bootstrap:{request.client.host if request.client else 'unknown'}", 4)
    if not hmac.compare_digest(bootstrap_key, get_settings().bootstrap_key):
        raise AuthenticationError()
    if db.scalar(select(User.id).where(User.email == payload.owner_email.lower())):
        raise ConflictError()
    user = User(
        name=payload.owner_name,
        email=payload.owner_email.lower(),
        password_hash=hash_password(payload.owner_password),
    )
    org = Organization(name=payload.organization_name)
    db.add_all([user, org])
    db.flush()
    member = Membership(user_id=user.id, organization_id=org.id)
    db.add(member)
    for code in PERMISSIONS:
        if not db.scalar(select(Permission).where(Permission.code == code)):
            db.add(Permission(code=code))
    db.flush()
    for code in ROLES:
        role = Role(organization_id=org.id, name=code.replace("_", " ").title(), code=code)
        db.add(role)
        db.flush()
        granted = (
            PERMISSIONS
            if code == "OWNER"
            else ("organization.read", "branches.read", "terminals.read")
            if code in {"MANAGER", "SUPERVISOR"}
            else ()
        )
        for permission in db.scalars(select(Permission).where(Permission.code.in_(granted))):
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        if code == "OWNER":
            db.add(MembershipRole(organization_id=org.id, membership_id=member.id, role_id=role.id))
    record(db, "ORGANIZATION_CREATED", "organization", org.id, org.id, user.id)
    commit(db)
    return {"organization": organization_dict(org), "owner": user_dict(user)}


@router.post("/auth/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(db_session)):
    email = payload.email.lower()
    limiter(f"login:ip:{request.client.host if request.client else 'unknown'}", 20)
    limiter(f"login:email:{email}", 10)
    user = db.scalar(select(User).where(User.email == email))
    if (
        not user
        or user.status != "ACTIVE"
        or not verify_password(payload.password, user.password_hash)
    ):
        record(
            db,
            "USER_LOGIN_FAILED",
            "user",
            user.id if user else None,
            None,
            user.id if user else None,
        )
        commit(db)
        raise AuthenticationError()
    user.last_login_at = datetime.now(timezone.utc)
    record(db, "USER_LOGIN", "user", user.id, None, user.id)
    refresh = issue_refresh(db, user.id)
    commit(db)
    return {"access_token": access_token(user.id), "refresh_token": refresh, "token_type": "bearer"}


@router.post("/auth/refresh")
def refresh(payload: RefreshIn, request: Request, db: Session = Depends(db_session)):
    limiter(f"refresh:{request.client.host if request.client else 'unknown'}", 30)
    rotated = rotate_refresh(db, payload.refresh_token)
    if rotated is None:
        raise AuthenticationError()
    user_id, refresh_token = rotated
    user = db.get(User, user_id)
    if user is None or user.status != "ACTIVE":
        db.rollback()
        raise AuthenticationError()
    commit(db)
    return {
        "access_token": access_token(user_id),
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/auth/logout", status_code=204)
def logout(
    payload: RefreshIn, user: User = Depends(current_user), db: Session = Depends(db_session)
):
    revoke_refresh(db, payload.refresh_token, user.id)
    commit(db)


@router.get("/auth/me")
def me(user: User = Depends(current_user), db: Session = Depends(db_session)):
    memberships = db.scalars(
        select(Membership)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(
            Membership.user_id == user.id,
            Membership.status == "ACTIVE",
            Organization.status == "ACTIVE",
        )
    ).all()
    return {**user_dict(user), "organizations": [str(m.organization_id) for m in memberships]}


@router.get("/auth/context")
def auth_context(ctx: Context = Depends(context)):
    return {
        "organization": organization_dict(ctx.organization),
        "permissions": sorted(ctx.org_permissions),
        "branch_permissions": {
            str(branch): sorted(codes) for branch, codes in ctx.branch_permissions.items()
        },
    }


@router.get("/organizations")
def organizations(ctx: Context = Depends(context)):
    ctx.require("organization.read")
    return [organization_dict(ctx.organization)]


@router.patch("/organizations")
def update_organization(
    payload: OrganizationPatch, ctx: Context = Depends(context), db: Session = Depends(db_session)
):
    ctx.require("organization.manage")
    org = ctx.organization
    before = organization_dict(org)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(org, field, value)
    record(
        db,
        "ORGANIZATION_UPDATED",
        "organization",
        org.id,
        org.id,
        ctx.user.id,
        before=before,
        after=organization_dict(org),
    )
    commit(db)
    return organization_dict(org)


@router.get("/permissions")
def permissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    ctx.require("roles.read")
    rows = db.scalars(
        select(Permission).order_by(Permission.code).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return page_of(rows, page, page_size, lambda p: {"id": str(p.id), "code": p.code})


@router.get("/roles")
def roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    ctx.require("roles.read")
    rows = db.scalars(
        select(Role)
        .where(Role.organization_id == ctx.organization.id)
        .order_by(Role.code)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return page_of(
        rows, page, page_size, lambda r: {"id": str(r.id), "code": r.code, "name": r.name}
    )


@router.get("/branches")
def branches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    stmt = select(Branch).where(Branch.organization_id == ctx.organization.id)
    if status:
        stmt = stmt.where(Branch.status == status)
    if search:
        stmt = stmt.where(Branch.name.ilike(f"%{search}%"))
    if "branches.read" not in ctx.org_permissions:
        allowed = [b for b in ctx.branch_permissions if ctx.permits("branches.read", b)]
        if not allowed:
            raise PermissionDeniedError()
        stmt = stmt.where(Branch.id.in_(allowed))
    rows = db.scalars(
        stmt.order_by(Branch.created_at, Branch.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return page_of(rows, page, page_size, branch_dict)


@router.get("/branches/{branch_id}")
def get_branch(branch_id: UUID, ctx: Context = Depends(context), db: Session = Depends(db_session)):
    return branch_dict(scoped_branch(db, ctx, branch_id, "branches.read"))


@router.post("/branches", status_code=201)
def create_branch(
    payload: BranchIn, ctx: Context = Depends(context), db: Session = Depends(db_session)
):
    ctx.require("branches.create")
    branch = Branch(organization_id=ctx.organization.id, **payload.model_dump())
    db.add(branch)
    db.flush()
    db.add(BranchSettings(branch_id=branch.id, organization_id=ctx.organization.id))
    record(
        db,
        "BRANCH_CREATED",
        "branch",
        branch.id,
        ctx.organization.id,
        ctx.user.id,
        branch_id=branch.id,
        after=branch_dict(branch),
    )
    commit(db)
    return branch_dict(branch)


@router.patch("/branches/{branch_id}")
def update_branch(
    branch_id: UUID,
    payload: BranchPatch,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    branch = scoped_branch(db, ctx, branch_id, "branches.update")
    before = branch_dict(branch)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "status" and value not in {"ACTIVE", "INACTIVE", "SUSPENDED"}:
            raise ConflictError()
        setattr(branch, field, value)
    record(
        db,
        "BRANCH_UPDATED",
        "branch",
        branch.id,
        ctx.organization.id,
        ctx.user.id,
        branch_id=branch.id,
        before=before,
        after=branch_dict(branch),
    )
    commit(db)
    return branch_dict(branch)


@router.get("/users")
def users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    ctx.require("users.read")
    stmt = (
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.organization_id == ctx.organization.id)
    )
    if status:
        stmt = stmt.where(User.status == status)
    if search:
        stmt = stmt.where(User.name.ilike(f"%{search}%"))
    rows = db.execute(
        stmt.order_by(User.created_at, User.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return page_of(
        rows,
        page,
        page_size,
        lambda row: {
            **user_dict(row[0]),
            "membership_id": str(row[1].id),
            "membership_status": row[1].status,
        },
    )


@router.get("/users/{user_id}")
def get_user(user_id: UUID, ctx: Context = Depends(context), db: Session = Depends(db_session)):
    ctx.require("users.read")
    member = db.scalar(
        select(Membership).where(
            Membership.organization_id == ctx.organization.id, Membership.user_id == user_id
        )
    )
    if member is None:
        raise NotFoundError()
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError()
    assignments = db.execute(
        select(MembershipRole.id, Role.code, MembershipRole.branch_id)
        .join(Role, Role.id == MembershipRole.role_id)
        .where(
            MembershipRole.organization_id == ctx.organization.id,
            MembershipRole.membership_id == member.id,
        )
    ).all()
    return {
        **user_dict(user),
        "membership_id": str(member.id),
        "membership_status": member.status,
        "roles": [
            {"assignment_id": str(id_), "code": code, "branch_id": str(branch) if branch else None}
            for id_, code, branch in assignments
        ],
    }


@router.post("/users", status_code=201)
def invite_user(
    payload: UserIn, ctx: Context = Depends(context), db: Session = Depends(db_session)
):
    ctx.require("users.invite")
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user:
        user = User(
            name=payload.name,
            email=payload.email.lower(),
            phone=payload.phone,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        db.flush()
    elif user.status != "ACTIVE":
        raise ConflictError()
    if db.scalar(
        select(Membership).where(
            Membership.user_id == user.id, Membership.organization_id == ctx.organization.id
        )
    ):
        raise ConflictError()
    member = Membership(user_id=user.id, organization_id=ctx.organization.id)
    db.add(member)
    commit(db)
    return {**user_dict(user), "membership_id": str(member.id)}


def owner_count(db: Session, organization_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count(MembershipRole.id))
            .join(Role, Role.id == MembershipRole.role_id)
            .join(Membership, Membership.id == MembershipRole.membership_id)
            .join(User, User.id == Membership.user_id)
            .where(
                MembershipRole.organization_id == organization_id,
                MembershipRole.branch_id.is_(None),
                Role.code == "OWNER",
                Membership.status == "ACTIVE",
                User.status == "ACTIVE",
            )
        )
        or 0
    )


@router.post("/users/{user_id}/disable")
def disable_user(user_id: UUID, ctx: Context = Depends(context), db: Session = Depends(db_session)):
    ctx.require("users.manage")
    db.scalar(
        select(Organization.id).where(Organization.id == ctx.organization.id).with_for_update()
    )
    member = db.scalar(
        select(Membership)
        .where(Membership.user_id == user_id, Membership.organization_id == ctx.organization.id)
        .with_for_update()
    )
    if not member:
        raise NotFoundError()
    # A globally shared user cannot be disabled from one merchant: suspend membership instead.
    if (
        db.scalar(
            select(MembershipRole.id)
            .join(Role, Role.id == MembershipRole.role_id)
            .where(
                MembershipRole.membership_id == member.id,
                Role.code == "OWNER",
                MembershipRole.branch_id.is_(None),
            )
        )
        and owner_count(db, ctx.organization.id) <= 1
    ):
        raise ConflictError()
    member.status = "SUSPENDED"
    record(db, "USER_DISABLED", "membership", member.id, ctx.organization.id, ctx.user.id)
    commit(db)
    return {"membership_id": str(member.id), "status": member.status}


@router.post("/users/{user_id}/roles", status_code=201)
def assign_role(
    user_id: UUID,
    payload: AssignRoleIn,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    ctx.require("roles.manage")
    member = db.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.organization_id == ctx.organization.id,
            Membership.status == "ACTIVE",
        )
    )
    role = db.scalar(
        select(Role).where(Role.id == payload.role_id, Role.organization_id == ctx.organization.id)
    )
    if not member or not role:
        raise NotFoundError()
    if payload.branch_id:
        scoped_branch(db, ctx, payload.branch_id, "branches.read")
    grants = set(
        db.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
        )
    )
    if not grants.issubset(ctx.org_permissions):
        raise PermissionDeniedError()
    if role.code == "OWNER" and (
        payload.branch_id is not None
        or "OWNER"
        not in set(
            db.scalars(
                select(Role.code)
                .join(MembershipRole, MembershipRole.role_id == Role.id)
                .where(
                    MembershipRole.membership_id == ctx.membership.id,
                    MembershipRole.branch_id.is_(None),
                )
            )
        )
    ):
        raise PermissionDeniedError()
    if db.scalar(
        select(MembershipRole.id).where(
            MembershipRole.membership_id == member.id,
            MembershipRole.role_id == role.id,
            MembershipRole.branch_id == payload.branch_id,
        )
    ):
        raise ConflictError()
    assignment = MembershipRole(
        organization_id=ctx.organization.id,
        membership_id=member.id,
        role_id=role.id,
        branch_id=payload.branch_id,
    )
    db.add(assignment)
    db.flush()
    record(
        db,
        "ROLE_ASSIGNED",
        "membership_role",
        assignment.id,
        ctx.organization.id,
        ctx.user.id,
        branch_id=payload.branch_id,
        after={"role": role.code, "user_id": str(user_id)},
    )
    commit(db)
    return {
        "id": str(assignment.id),
        "role": role.code,
        "branch_id": str(payload.branch_id) if payload.branch_id else None,
    }


@router.delete("/users/{user_id}/roles/{assignment_id}", status_code=204)
def remove_role(
    user_id: UUID,
    assignment_id: UUID,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    ctx.require("roles.manage")
    db.scalar(
        select(Organization.id).where(Organization.id == ctx.organization.id).with_for_update()
    )
    assignment = db.scalar(
        select(MembershipRole)
        .join(Membership, Membership.id == MembershipRole.membership_id)
        .where(
            MembershipRole.id == assignment_id,
            MembershipRole.organization_id == ctx.organization.id,
            Membership.user_id == user_id,
        )
        .with_for_update()
    )
    if not assignment:
        raise NotFoundError()
    role = db.scalar(
        select(Role).where(
            Role.id == assignment.role_id, Role.organization_id == ctx.organization.id
        )
    )
    if role is None:
        raise NotFoundError()
    if role.code == "OWNER" and owner_count(db, ctx.organization.id) <= 1:
        raise ConflictError()
    grants = set(
        db.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
        )
    )
    if not grants.issubset(ctx.org_permissions):
        raise PermissionDeniedError()
    db.delete(assignment)
    record(
        db,
        "ROLE_REMOVED",
        "membership_role",
        assignment_id,
        ctx.organization.id,
        ctx.user.id,
        branch_id=assignment.branch_id,
    )
    commit(db)


@router.get("/terminals")
def terminals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    branch: UUID | None = None,
    status: str | None = None,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    stmt = select(Terminal).where(Terminal.organization_id == ctx.organization.id)
    if branch:
        stmt = stmt.where(Terminal.branch_id == branch)
    if status:
        stmt = stmt.where(Terminal.activation_status == status)
    if "terminals.read" not in ctx.org_permissions:
        allowed = [b for b in ctx.branch_permissions if ctx.permits("terminals.read", b)]
        if not allowed:
            raise PermissionDeniedError()
        stmt = stmt.where(Terminal.branch_id.in_(allowed))
    rows = db.scalars(
        stmt.order_by(Terminal.created_at, Terminal.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return page_of(rows, page, page_size, terminal_dict)


@router.post("/terminals", status_code=201)
def create_terminal(
    payload: TerminalIn, ctx: Context = Depends(context), db: Session = Depends(db_session)
):
    scoped_branch(db, ctx, payload.branch_id, "terminals.manage")
    terminal = Terminal(organization_id=ctx.organization.id, **payload.model_dump())
    db.add(terminal)
    db.flush()
    record(
        db,
        "TERMINAL_CREATED",
        "terminal",
        terminal.id,
        ctx.organization.id,
        ctx.user.id,
        branch_id=payload.branch_id,
        after=terminal_dict(terminal),
    )
    commit(db)
    return terminal_dict(terminal)


@router.patch("/terminals/{terminal_id}")
def rename_terminal(
    terminal_id: UUID,
    payload: TerminalPatch,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    terminal = db.scalar(
        select(Terminal).where(
            Terminal.id == terminal_id, Terminal.organization_id == ctx.organization.id
        )
    )
    if not terminal:
        raise NotFoundError()
    ctx.require("terminals.manage", terminal.branch_id)
    terminal.name = payload.name
    commit(db)
    return terminal_dict(terminal)


@router.post("/terminals/{terminal_id}/revoke")
def revoke_terminal(
    terminal_id: UUID, ctx: Context = Depends(context), db: Session = Depends(db_session)
):
    terminal = db.scalar(
        select(Terminal).where(
            Terminal.id == terminal_id, Terminal.organization_id == ctx.organization.id
        )
    )
    if not terminal:
        raise NotFoundError()
    ctx.require("terminals.manage", terminal.branch_id)
    terminal.activation_status = "REVOKED"
    record(
        db,
        "TERMINAL_REVOKED",
        "terminal",
        terminal.id,
        ctx.organization.id,
        ctx.user.id,
        branch_id=terminal.branch_id,
    )
    commit(db)
    return terminal_dict(terminal)


@router.get("/audit")
def audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    branch: UUID | None = None,
    ctx: Context = Depends(context),
    db: Session = Depends(db_session),
):
    ctx.require("audit.read")
    stmt = select(AuditLog).where(AuditLog.organization_id == ctx.organization.id)
    if branch:
        stmt = stmt.where(AuditLog.branch_id == branch)
    rows = db.scalars(
        stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return page_of(
        rows,
        page,
        page_size,
        lambda row: {
            "id": str(row.id),
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": str(row.entity_id) if row.entity_id else None,
            "created_at": row.created_at.isoformat(),
        },
    )
