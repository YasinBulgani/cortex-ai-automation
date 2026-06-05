"""Business logic for organizations, teams, invitations."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone as _tz
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infra.models import (
    Invitation,
    Organization,
    ProjectMember,
    Team,
    TeamMember,
    User,
)

_INVITE_TOKEN_TTL = timedelta(days=7)


def _now() -> datetime:
    return datetime.now(_tz.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_invite_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). Raw token is e-mailed; only hash stored."""
    raw = secrets.token_urlsafe(32)
    return raw, _hash_token(raw)


# ── Organizations ────────────────────────────────────────────────
def get_organization(db: Session, org_id: str) -> Optional[Organization]:
    return db.scalar(select(Organization).where(Organization.id == org_id))


def list_user_teams(db: Session, user_id: str) -> list[Team]:
    stmt = (
        select(Team)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == user_id)
    )
    return list(db.scalars(stmt).all())


# ── Teams ────────────────────────────────────────────────────────
def create_team(
    db: Session, organization_id: str, *, name: str, slug: str, description: Optional[str] = None
) -> Team:
    team = Team(
        organization_id=organization_id,
        name=name,
        slug=slug,
        description=description,
    )
    db.add(team)
    db.flush()
    return team


def list_teams(db: Session, organization_id: str) -> list[Team]:
    return list(
        db.scalars(
            select(Team).where(Team.organization_id == organization_id).order_by(Team.name)
        ).all()
    )


def add_team_member(
    db: Session, *, team_id: str, user_id: str, role: str = "member"
) -> TeamMember:
    existing = db.get(TeamMember, (team_id, user_id))
    if existing:
        existing.role = role
        return existing
    tm = TeamMember(team_id=team_id, user_id=user_id, role=role)
    db.add(tm)
    db.flush()
    return tm


def remove_team_member(db: Session, *, team_id: str, user_id: str) -> bool:
    tm = db.get(TeamMember, (team_id, user_id))
    if not tm:
        return False
    db.delete(tm)
    return True


def list_team_members_with_user(db: Session, team_id: str) -> list[tuple[TeamMember, User]]:
    stmt = (
        select(TeamMember, User)
        .join(User, User.id == TeamMember.user_id)
        .where(TeamMember.team_id == team_id)
    )
    return [(tm, u) for tm, u in db.execute(stmt).all()]


# ── Project members ──────────────────────────────────────────────
def add_project_member(
    db: Session, *, project_id: str, user_id: str, role: str = "viewer"
) -> ProjectMember:
    existing = db.get(ProjectMember, (project_id, user_id))
    if existing:
        existing.role = role
        return existing
    pm = ProjectMember(project_id=project_id, user_id=user_id, role=role)
    db.add(pm)
    db.flush()
    return pm


def remove_project_member(db: Session, *, project_id: str, user_id: str) -> bool:
    pm = db.get(ProjectMember, (project_id, user_id))
    if not pm:
        return False
    db.delete(pm)
    return True


def list_project_members_with_user(
    db: Session, project_id: str
) -> list[tuple[ProjectMember, User]]:
    stmt = (
        select(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
    )
    return [(pm, u) for pm, u in db.execute(stmt).all()]


def get_project_role(db: Session, *, project_id: str, user_id: str) -> Optional[str]:
    pm = db.get(ProjectMember, (project_id, user_id))
    return pm.role if pm else None


# ── Invitations ──────────────────────────────────────────────────
def create_invitation(
    db: Session,
    *,
    organization_id: str,
    email: str,
    role: str,
    team_id: Optional[str],
    invited_by: Optional[str],
) -> tuple[Invitation, str]:
    raw_token, token_hash = issue_invite_token()
    inv = Invitation(
        organization_id=organization_id,
        team_id=team_id,
        email=email.lower().strip(),
        role=role,
        token_hash=token_hash,
        invited_by=invited_by,
        expires_at=_now() + _INVITE_TOKEN_TTL,
    )
    db.add(inv)
    db.flush()
    return inv, raw_token


def list_pending_invitations(db: Session, organization_id: str) -> list[Invitation]:
    stmt = (
        select(Invitation)
        .where(
            Invitation.organization_id == organization_id,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
        )
        .order_by(Invitation.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def revoke_invitation(db: Session, *, invitation_id: str) -> bool:
    inv = db.get(Invitation, invitation_id)
    if not inv or inv.revoked_at or inv.accepted_at:
        return False
    inv.revoked_at = _now()
    return True


def find_invitation_by_token(db: Session, raw_token: str) -> Optional[Invitation]:
    token_hash = _hash_token(raw_token)
    inv = db.scalar(select(Invitation).where(Invitation.token_hash == token_hash))
    if not inv:
        return None
    if inv.revoked_at or inv.accepted_at:
        return None
    if inv.expires_at < _now():
        return None
    return inv


def mark_invitation_accepted(db: Session, *, invitation_id: str) -> None:
    inv = db.get(Invitation, invitation_id)
    if inv:
        inv.accepted_at = _now()
