"""REST endpoints for organizations, teams, invitations, project members."""

from __future__ import annotations

import logging
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import _user_permissions, get_current_user
from app.domains.audit.service import log_audit
from app.domains.auth.service import hash_password
from app.infra.database import get_db
from app.infra.models import Invitation, Team, TeamMember, User

from . import service
from .schemas import (
    InvitationAccept,
    InvitationCreate,
    InvitationOut,
    OrganizationOut,
    OrganizationUpdate,
    ProjectMemberAdd,
    ProjectMemberOut,
    ProjectMemberRoleUpdate,
    TeamCreate,
    TeamMemberAdd,
    TeamMemberOut,
    TeamOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations", tags=["organizations"])


def _require_org_admin(user: User) -> None:
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu islem icin organizasyon yoneticisi olmaniz gerekir.",
        )


def _assert_project_in_tenant(
    db: Session, *, project_id: str, user: User, require_existing: bool = False
) -> None:
    """Verify the project belongs to the caller's tenant.

    prj_projects has no tenant_id column, so tenancy is inferred from the
    project's existing members. A project is "foreign" if it has members but
    none share the caller's tenant_id — in that case mutating it would be a
    cross-tenant privilege grant (IDOR), so we 404.

    When ``require_existing`` is False (e.g. adding the first member of a
    freshly created project) a project with zero members is allowed, since it
    has not yet been claimed by any tenant. When True (role change / removal)
    the target member must already exist, so the project must have at least one
    member in the caller's tenant.
    """
    rows = service.list_project_members_with_user(db, project_id)
    if not rows:
        if require_existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Proje bulunamadi")
        return
    if not any(u.tenant_id == user.tenant_id for _pm, u in rows):
        # Project is owned by another tenant — deny without leaking existence.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proje bulunamadi")


def _invite_accept_url(token: str) -> str:
    base = (settings.app_public_url or "http://localhost:3000").rstrip("/")
    return f"{base}/accept-invite?token={quote(token)}"


def _send_invite_email(email: str, token: str, org_name: str, role: str) -> bool:
    from app.domains.notifications.email_service import send_email

    url = _invite_accept_url(token)
    html = f"""
    <html><body style="font-family: Arial, sans-serif; color:#0f172a;">
      <h2>{org_name} sizi davet ediyor</h2>
      <p>Rol: <strong>{role}</strong></p>
      <p>Davete katilmak icin asagidaki bagi tiklayin (7 gun gecerli):</p>
      <p><a href="{url}" style="background:#2563eb;color:#fff;padding:10px 16px;
         border-radius:8px;text-decoration:none;">Davete katil</a></p>
      <p style="font-size:12px;color:#64748b;">Bu davet sizin icin degilse mesaji yok sayabilirsiniz.</p>
    </body></html>
    """
    try:
        return send_email(email, f"{org_name} davetiniz", html)
    except Exception:
        logger.exception("invite email failed")
        return False


# ── Current org / membership ─────────────────────────────────────
@router.get("/me", response_model=OrganizationOut)
def get_my_organization(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    org = service.get_organization(db, user.tenant_id)
    if not org:
        raise HTTPException(404, detail="Organizasyon bulunamadi")
    return org


@router.patch("/me", response_model=OrganizationOut)
def update_my_organization(
    body: OrganizationUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _require_org_admin(user)
    org = service.get_organization(db, user.tenant_id)
    if not org:
        raise HTTPException(404)
    if body.name is not None:
        org.name = body.name
    db.commit()
    db.refresh(org)
    log_audit(db, actor_user_id=user.id, action="organization.update", resource_type="organization", resource_id=org.id, payload=None, ip=None)
    return org


# ── Teams ────────────────────────────────────────────────────────
@router.get("/me/teams", response_model=list[TeamOut])
def list_org_teams(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(100, ge=1, le=500),
):
    teams = service.list_teams(db, user.tenant_id)[:limit]
    out: list[TeamOut] = []
    for t in teams:
        count = db.scalar(
            select(func.count(TeamMember.user_id)).where(TeamMember.team_id == t.id)
        )
        out.append(
            TeamOut(
                id=t.id,
                organization_id=t.organization_id,
                name=t.name,
                slug=t.slug,
                description=t.description,
                created_at=t.created_at,
                member_count=count,
            )
        )
    return out


@router.post("/me/teams", response_model=TeamOut, status_code=201)
def create_team_endpoint(
    body: TeamCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _require_org_admin(user)
    team = service.create_team(
        db,
        organization_id=user.tenant_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
    )
    db.commit()
    db.refresh(team)
    log_audit(db, actor_user_id=user.id, action="team.create", resource_type="organization", resource_id=team.id, payload=None, ip=None)
    return TeamOut(
        id=team.id,
        organization_id=team.organization_id,
        name=team.name,
        slug=team.slug,
        description=team.description,
        created_at=team.created_at,
        member_count=0,
    )


@router.get("/teams/{team_id}/members", response_model=list[TeamMemberOut])
def list_team_members(
    team_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(200, ge=1, le=1000),
):
    team = db.get(Team, team_id)
    if not team or team.organization_id != user.tenant_id:
        raise HTTPException(404)
    rows = service.list_team_members_with_user(db, team_id)[:limit]
    return [
        TeamMemberOut(
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=tm.role,
            joined_at=tm.joined_at,
        )
        for tm, u in rows
    ]


@router.post("/teams/{team_id}/members", status_code=201)
def add_team_member_endpoint(
    team_id: str,
    body: TeamMemberAdd,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _require_org_admin(user)
    team = db.get(Team, team_id)
    if not team or team.organization_id != user.tenant_id:
        raise HTTPException(404)
    target = db.get(User, body.user_id)
    if not target or target.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="Kullanici bu organizasyonda degil")
    service.add_team_member(db, team_id=team_id, user_id=body.user_id, role=body.role)
    db.commit()
    log_audit(db, actor_user_id=user.id, action="team.member.add", resource_type="organization", resource_id=f"{team_id}:{body.user_id}", payload=None, ip=None)
    return {"ok": True}


@router.delete("/teams/{team_id}/members/{user_id}")
def remove_team_member_endpoint(
    team_id: str,
    user_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _require_org_admin(user)
    team = db.get(Team, team_id)
    if not team or team.organization_id != user.tenant_id:
        raise HTTPException(404)
    ok = service.remove_team_member(db, team_id=team_id, user_id=user_id)
    db.commit()
    log_audit(db, actor_user_id=user.id, action="team.member.remove", resource_type="organization", resource_id=f"{team_id}:{user_id}", payload=None, ip=None)
    return {"ok": ok}


# ── Invitations ──────────────────────────────────────────────────
@router.post("/invitations", response_model=InvitationOut, status_code=201)
def create_invitation_endpoint(
    body: InvitationCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _require_org_admin(user)
    if body.team_id:
        team = db.get(Team, body.team_id)
        if not team or team.organization_id != user.tenant_id:
            raise HTTPException(400, detail="Gecersiz takim")
    inv, raw_token = service.create_invitation(
        db,
        organization_id=user.tenant_id,
        email=body.email,
        role=body.role,
        team_id=body.team_id,
        invited_by=user.id,
    )
    db.commit()
    db.refresh(inv)
    org = service.get_organization(db, user.tenant_id)
    _send_invite_email(body.email, raw_token, org.name if org else "Cortex", body.role)
    log_audit(db, actor_user_id=user.id, action="invitation.create", resource_type="invitation", resource_id=inv.id, payload=None, ip=None)
    return inv


@router.get("/invitations", response_model=list[InvitationOut])
def list_invitations_endpoint(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(200, ge=1, le=500),
):
    _require_org_admin(user)
    return service.list_pending_invitations(db, user.tenant_id)[:limit]


@router.delete("/invitations/{invitation_id}")
def revoke_invitation_endpoint(
    invitation_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _require_org_admin(user)
    inv = db.get(Invitation, invitation_id)
    if not inv or inv.organization_id != user.tenant_id:
        raise HTTPException(404)
    ok = service.revoke_invitation(db, invitation_id=invitation_id)
    db.commit()
    log_audit(db, actor_user_id=user.id, action="invitation.revoke", resource_type="invitation", resource_id=invitation_id, payload=None, ip=None)
    return {"ok": ok}


@router.post("/invitations/accept")
def accept_invitation_endpoint(
    body: InvitationAccept,
    db: Annotated[Session, Depends(get_db)],
):
    """Public endpoint — token ile yeni hesap olustur veya mevcut hesabi ekle.

    Güvenlik: Mevcut kullanıcı varsa onay sadece ilgili kullanıcının kimliğiyle
    yapılmalıdır. Davet tokenı başka bir kullanıcı tarafından kabul edilemez.
    Yeni kullanıcı oluşturma akışında e-posta ve şifre gereklidir.
    """
    inv = service.find_invitation_by_token(db, body.token)
    if not inv:
        raise HTTPException(400, detail="Davet gecersiz, kullanilmis veya suresi dolmus")

    existing_user = db.execute(select(User).where(User.email == inv.email)).scalars().first()
    created = False

    if existing_user is None:
        # New user: password required
        if not body.password:
            raise HTTPException(400, detail="Yeni hesap icin sifre gerekli")
        new_user = User(
            email=inv.email,
            password_hash=hash_password(body.password),
            full_name=body.full_name,
            tenant_id=inv.organization_id,
            is_active=True,
        )
        db.add(new_user)
        db.flush()
        acting_user = new_user
        created = True
    else:
        # Existing user: verify they know their own password before we move
        # them to a new org. This prevents token-based account hijacking.
        if not body.password or not __import__('bcrypt').checkpw(
            body.password.encode("utf-8"), existing_user.password_hash.encode("utf-8")
        ):
            raise HTTPException(401, detail="Kimlik dogrulamasi basarisiz. Mevcut parolanizi girin.")
        if existing_user.tenant_id != inv.organization_id:
            existing_user.tenant_id = inv.organization_id
        acting_user = existing_user

    if inv.team_id:
        service.add_team_member(
            db, team_id=inv.team_id, user_id=acting_user.id, role=inv.role
        )

    service.mark_invitation_accepted(db, invitation_id=inv.id)
    db.commit()
    log_audit(db, actor_user_id=acting_user.id, action="invitation.accept", resource_type="invitation", resource_id=inv.id, payload=None, ip=None)
    return {"ok": True, "created_user": created, "organization_id": inv.organization_id}


# ── Project members (project-level ACL) ──────────────────────────
@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberOut])
def list_project_members_endpoint(
    project_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(200, ge=1, le=1000),
):
    # Ensure requester is a member of this project or org admin
    from app.infra.models import ProjectMember
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        member = db.get(ProjectMember, (project_id, user.id))
        if member is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu projeye erisim yetkiniz yok")
    rows = service.list_project_members_with_user(db, project_id)[:limit]
    return [
        ProjectMemberOut(
            project_id=project_id,
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=pm.role,
            added_at=pm.added_at,
        )
        for pm, u in rows
    ]


@router.post("/projects/{project_id}/members", status_code=201)
def add_project_member_endpoint(
    project_id: str,
    body: ProjectMemberAdd,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _require_org_admin(user)
    _assert_project_in_tenant(db, project_id=project_id, user=user)
    target = db.get(User, body.user_id)
    if not target or target.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="Kullanici bu organizasyonda degil")
    service.add_project_member(
        db, project_id=project_id, user_id=body.user_id, role=body.role
    )
    db.commit()
    log_audit(db, actor_user_id=user.id, action="project.member.add", resource_type="project", resource_id=f"{project_id}:{body.user_id}", payload=None, ip=None)
    return {"ok": True}


@router.patch("/projects/{project_id}/members/{user_id}", response_model=ProjectMemberOut)
def update_project_member_role_endpoint(
    project_id: str,
    user_id: str,
    body: ProjectMemberRoleUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    from app.infra.models import ProjectMember
    # Allow org admins OR project admins/owners to change roles
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        requester_pm = db.get(ProjectMember, (project_id, user.id))
        if not requester_pm or requester_pm.role not in ("owner", "admin"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu işlem için Admin yetkisi gereklidir")
    else:
        # Org admins are not bound to a specific project; ensure the project
        # belongs to their tenant to prevent cross-tenant IDOR.
        _assert_project_in_tenant(
            db, project_id=project_id, user=user, require_existing=True
        )
    target_pm = db.get(ProjectMember, (project_id, user_id))
    if not target_pm:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Üye bu projede bulunamadı")
    old_role = target_pm.role
    target_pm.role = body.role
    db.commit()
    db.refresh(target_pm)
    target_user = db.get(type(user), user_id)
    log_audit(db, actor_user_id=user.id, action="project.member.role_changed", resource_type="project",
              resource_id=f"{project_id}:{user_id}",
              payload={"old_role": old_role, "new_role": body.role}, ip=None)
    return ProjectMemberOut(
        project_id=project_id,
        user_id=user_id,
        email=target_user.email if target_user else "",
        full_name=target_user.full_name if target_user else None,
        role=target_pm.role,
        added_at=target_pm.added_at,
    )


@router.delete("/projects/{project_id}/members/{user_id}")
def remove_project_member_endpoint(
    project_id: str,
    user_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _require_org_admin(user)
    _assert_project_in_tenant(
        db, project_id=project_id, user=user, require_existing=True
    )
    ok = service.remove_project_member(db, project_id=project_id, user_id=user_id)
    db.commit()
    log_audit(db, actor_user_id=user.id, action="project.member.remove", resource_type="project", resource_id=f"{project_id}:{user_id}", payload=None, ip=None)
    return {"ok": ok}
