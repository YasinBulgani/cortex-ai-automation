"""İlk roller, izinler ve admin kullanıcı (idempotent). Çalıştır: cd backend && PYTHONPATH=. python scripts/seed.py"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.auth.permissions import ROLE_PERMISSIONS
from app.domains.auth.service import hash_password
from app.infra.database import SessionLocal
from app.infra.models import Role, RolePermission, User


def seed(db: Session) -> None:
    roles_data = ["admin", "operator", "viewer"]
    roles: dict[str, Role] = {}
    for name in roles_data:
        r = db.scalar(select(Role).where(Role.name == name))
        if r is None:
            r = Role(name=name)
            db.add(r)
            db.flush()
        roles[name] = r

    # Seed permissions for each role
    for role_name, perms in ROLE_PERMISSIONS.items():
        role = roles.get(role_name)
        if role is None:
            continue
        existing = {rp.permission for rp in role.permissions}
        for perm in perms:
            if perm not in existing:
                db.add(RolePermission(role_id=role.id, permission=perm))

    # Admin user
    email = os.environ.get("SEED_ADMIN_EMAIL", "admin@example.com")
    password = os.environ.get("SEED_ADMIN_PASSWORD", "admin123")
    reset_admin_pw = os.environ.get("SEED_RESET_ADMIN_PASSWORD", "").lower() in (
        "1",
        "true",
        "yes",
    )
    _default_tenant = "00000000-0000-0000-0000-000000000001"
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            tenant_id=_default_tenant,
        )
        db.add(user)
        db.flush()
    else:
        if not getattr(user, "tenant_id", None):
            user.tenant_id = _default_tenant
        if reset_admin_pw:
            user.password_hash = hash_password(password)
    if roles["admin"] not in user.roles:
        user.roles.append(roles["admin"])

    # Operator user (for RBAC testing)
    op_email = "operator@test.com"
    op_user = db.scalar(select(User).where(User.email == op_email))
    if op_user is None:
        op_user = User(
            email=op_email,
            password_hash=hash_password("test123"),
            is_active=True,
            tenant_id=_default_tenant,
        )
        db.add(op_user)
        db.flush()
    if roles["operator"] not in op_user.roles:
        op_user.roles.append(roles["operator"])

    # Viewer user (for RBAC testing)
    vw_email = "viewer@test.com"
    vw_user = db.scalar(select(User).where(User.email == vw_email))
    if vw_user is None:
        vw_user = User(email=vw_email, password_hash=hash_password("test123"), is_active=True)
        db.add(vw_user)
        db.flush()
    if roles["viewer"] not in vw_user.roles:
        vw_user.roles.append(roles["viewer"])

    # Disabled user (for auth testing)
    dis_email = "disabled@test.com"
    dis_user = db.scalar(select(User).where(User.email == dis_email))
    if dis_user is None:
        dis_user = User(email=dis_email, password_hash=hash_password("test123"), is_active=False)
        db.add(dis_user)
        db.flush()

    # test@test.com — kolay giriş için (admin yetkisi)
    test_email = "test@test.com"
    test_user = db.scalar(select(User).where(User.email == test_email))
    if test_user is None:
        test_user = User(
            email=test_email,
            password_hash=hash_password("test"),
            is_active=True,
            full_name="Test Kullanıcı",
        )
        db.add(test_user)
        db.flush()
    if roles["admin"] not in test_user.roles:
        test_user.roles.append(roles["admin"])

    db.commit()
    print(f"Seed tamam: {email} / (parola env veya varsayılan admin123)")
    if reset_admin_pw:
        print("  — Mevcut admin parolası SEED_RESET_ADMIN_PASSWORD=1 ile güncellendi.")
    print(f"  + {op_email} (operator), {vw_email} (viewer), {dis_email} (disabled)")
    print(f"  + {test_email} / test (admin) — geliştirici hızlı giriş")


if __name__ == "__main__":
    s = SessionLocal()
    try:
        seed(s)
    finally:
        s.close()
