import os
from uuid import UUID

from sqlalchemy import select

from app.api.routes import PERMISSIONS, ROLES
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.models import (
    Branch,
    BranchSettings,
    Membership,
    MembershipRole,
    Organization,
    Permission,
    Role,
    RolePermission,
    User,
)
from app.core.security import hash_password


def seed():
    if get_settings().app_env not in {"local", "development"}:
        raise RuntimeError("Demo seed is available only in local/development")
    password = os.environ.get("DEV_SEED_PASSWORD")
    if not password or len(password) < 12:
        raise RuntimeError("Set DEV_SEED_PASSWORD to a unique value of at least 12 characters")
    org_id = UUID("00000000-0000-4000-8000-000000000001")
    with SessionLocal.begin() as db:
        if db.get(Organization, org_id):
            print("Demo already seeded")
            return
        org = Organization(id=org_id, name="Smart Merchant Demo")
        db.add(org)
        permission_rows = {}
        for code in PERMISSIONS:
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if not permission:
                permission = Permission(code=code)
                db.add(permission)
                db.flush()
            permission_rows[code] = permission
        role_rows = {}
        for code in ROLES:
            role = Role(organization_id=org_id, code=code, name=code.replace("_", " ").title())
            db.add(role)
            db.flush()
            role_rows[code] = role
            codes = (
                PERMISSIONS
                if code == "OWNER"
                else ("organization.read", "branches.read", "terminals.read")
                if code == "MANAGER"
                else ()
            )
            for permission_code in codes:
                db.add(
                    RolePermission(
                        role_id=role.id, permission_id=permission_rows[permission_code].id
                    )
                )
        branches = {}
        for name, code in (("Abha", "ABH01"), ("Khamis Mushait", "KHM01")):
            branch = Branch(organization_id=org_id, name=name, code=code)
            db.add(branch)
            db.flush()
            branches[code] = branch
            db.add(BranchSettings(branch_id=branch.id, organization_id=org_id))
        for code, role, branch in (
            ("owner", "OWNER", None),
            ("manager", "MANAGER", branches["ABH01"].id),
            ("cashier", "CASHIER", branches["ABH01"].id),
        ):
            user = User(
                name=code.title(),
                email=f"{code}@demo.example",
                password_hash=hash_password(password),
            )
            db.add(user)
            db.flush()
            member = Membership(organization_id=org_id, user_id=user.id)
            db.add(member)
            db.flush()
            db.add(
                MembershipRole(
                    organization_id=org_id,
                    membership_id=member.id,
                    role_id=role_rows[role].id,
                    branch_id=branch,
                )
            )
    print("Demo ready: owner@demo.example, manager@demo.example, cashier@demo.example")


if __name__ == "__main__":
    seed()
