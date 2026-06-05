"""
Jira entegrasyon domain router.

Endpoints:
  GET  /api/jira/status                     - Bağlantı durumu
  GET  /api/jira/config                     - Mevcut Jira ayarlarını getir (token maskelenir)
  POST /api/jira/config                     - Jira bağlantı ayarlarını DB'ye kaydet
  DELETE /api/jira/config                   - Jira bağlantısını sil
  POST /api/jira/test-connection            - Bağlantıyı test et
  GET  /api/jira/projects                   - Jira projelerini listele
  GET  /api/jira/projects/{key}/issues      - Issue'ları listele (JQL + filtre)
  GET  /api/jira/issues/{issue_key}         - Tek issue detayı (yorumlar dahil)
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_optional_user
from app.infra.database import get_db
from app.infra.models import User

from .models import JiraIntegration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jira", tags=["jira"])

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]


# ─── Schemas ─────────────────────────────────────────────────────────────────

class JiraConfigSave(BaseModel):
    url: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    token: str = Field(..., min_length=1)
    project_key: str = ""


class JiraConfigOut(BaseModel):
    configured: bool
    url: str
    email: str
    project_key: str
    token_hint: str = ""          # Son 4 karakter + ***


class IssueTypeFilter(BaseModel):
    issue_type: str = ""
    status_filter: str = ""


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_integration(db: Session, tenant_id: str) -> Optional[JiraIntegration]:
    return (
        db.query(JiraIntegration)
        .filter(JiraIntegration.tenant_id == tenant_id, JiraIntegration.is_active == True)
        .first()
    )


def _get_jira_client(db: Session, tenant_id: str):
    """Jira API istemcisi döndürür. Sorun varsa (None, hata_mesajı) döner."""
    intg = _get_integration(db, tenant_id)
    if not intg:
        return None, "Jira yapılandırması eksik. Lütfen Settings > Integrations sayfasından bağlantı kurun."
    try:
        from jira import JIRA  # type: ignore[import]
        client = JIRA(
            server=intg.jira_url,
            basic_auth=(intg.email, intg.api_token),
        )
        return client, None
    except ImportError:
        return None, "jira kütüphanesi yüklü değil"
    except Exception as exc:
        return None, str(exc)


def _extract_adf_text(node: object) -> str:
    """Atlassian Document Format (ADF) JSON'ından düz metin çıkarır."""
    if not isinstance(node, dict):
        return str(node) if node else ""
    parts: list[str] = []
    if node.get("type") == "text":
        parts.append(node.get("text", ""))
    for child in node.get("content", []) or []:
        parts.append(_extract_adf_text(child))
    return " ".join(p for p in parts if p).strip()


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/status")
def jira_connection_status(db: DB, user: OptionalUser):
    """Jira bağlantısının yapılandırılıp yapılandırılmadığını kontrol eder."""
    tenant_id = user.tenant_id if user else "00000000-0000-0000-0000-000000000001"
    intg = _get_integration(db, tenant_id)
    if not intg:
        return {"configured": False, "url": "", "email": "", "project_key": ""}
    return {
        "configured": True,
        "url": intg.jira_url,
        "email": intg.email,
        "project_key": intg.default_project_key or "",
    }


@router.get("/config", response_model=JiraConfigOut)
def jira_get_config(db: DB, user: CurrentUser):
    intg = _get_integration(db, user.tenant_id)
    if not intg:
        return JiraConfigOut(configured=False, url="", email="", project_key="")
    token_hint = "***" + intg.api_token[-4:] if intg.api_token else ""
    return JiraConfigOut(
        configured=True,
        url=intg.jira_url,
        email=intg.email,
        project_key=intg.default_project_key or "",
        token_hint=token_hint,
    )


@router.post("/config", status_code=status.HTTP_200_OK)
def jira_save_config(body: JiraConfigSave, db: DB, user: CurrentUser):
    """Jira bağlantı ayarlarını DB'ye kaydeder (upsert)."""
    intg = _get_integration(db, user.tenant_id)
    if intg:
        intg.jira_url = body.url.strip().rstrip("/")
        intg.email = body.email.strip()
        intg.api_token = body.token.strip()
        intg.default_project_key = body.project_key.strip() or None
    else:
        intg = JiraIntegration(
            tenant_id=user.tenant_id,
            jira_url=body.url.strip().rstrip("/"),
            email=body.email.strip(),
            api_token=body.token.strip(),
            default_project_key=body.project_key.strip() or None,
        )
        db.add(intg)
    db.commit()
    return {"ok": True}


@router.delete("/config", status_code=status.HTTP_200_OK)
def jira_delete_config(db: DB, user: CurrentUser):
    """Jira bağlantısını devre dışı bırakır (soft delete)."""
    intg = _get_integration(db, user.tenant_id)
    if intg:
        intg.is_active = False
        db.commit()
    return {"ok": True}


@router.post("/test-connection")
def jira_test_connection(db: DB, user: CurrentUser):
    client, err = _get_jira_client(db, user.tenant_id)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    try:
        me = client.myself()
        return {"ok": True, "user": me.get("displayName", me.get("name", ""))}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/projects")
def jira_list_projects(db: DB, user: CurrentUser):
    client, err = _get_jira_client(db, user.tenant_id)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    try:
        projects = client.projects()
        return [{"key": p.key, "name": p.name} for p in projects]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/projects/{project_key}/issues")
def jira_list_issues(
    project_key: str,
    db: DB,
    user: CurrentUser,
    search: str = "",
    issue_type: str = "",
    status_filter: str = "",
    max_results: int = 50,
):
    """Bir Jira projesinin issue'larını listeler. JQL ile arama + issue_type/status filtresi."""
    client, err = _get_jira_client(db, user.tenant_id)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    jql_parts = [f'project = "{project_key}"']
    if search.strip():
        safe = search.replace('"', '\\"')
        jql_parts.append(f'(summary ~ "{safe}" OR description ~ "{safe}" OR text ~ "{safe}")')
    if issue_type.strip():
        jql_parts.append(f'issuetype = "{issue_type}"')
    if status_filter.strip():
        jql_parts.append(f'status = "{status_filter}"')
    jql_parts.append("ORDER BY updated DESC")
    jql = " AND ".join(jql_parts)

    try:
        issues = client.search_issues(
            jql,
            maxResults=min(max_results, 100),
            fields=["summary", "description", "issuetype", "status", "priority", "assignee", "labels"],
        )
        intg = _get_integration(db, user.tenant_id)
        base_url = intg.jira_url if intg else ""
        result = []
        for issue in issues:
            f = issue.fields
            desc_raw = getattr(f, "description", None) or ""
            desc_text = _extract_adf_text(desc_raw) if isinstance(desc_raw, dict) else str(desc_raw)
            result.append({
                "key": issue.key,
                "summary": f.summary or "",
                "description": desc_text[:1000],
                "issue_type": getattr(getattr(f, "issuetype", None), "name", ""),
                "status": getattr(getattr(f, "status", None), "name", ""),
                "priority": getattr(getattr(f, "priority", None), "name", ""),
                "assignee": getattr(getattr(f, "assignee", None), "displayName", None),
                "labels": list(getattr(f, "labels", []) or []),
                "url": f"{base_url}/browse/{issue.key}",
            })
        return result
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/issues/{issue_key}")
def jira_get_issue(issue_key: str, db: DB, user: CurrentUser):
    """Tek bir Jira issue'nun tüm detaylarını döner."""
    client, err = _get_jira_client(db, user.tenant_id)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    try:
        issue = client.issue(issue_key, fields=[
            "summary", "description", "issuetype", "status", "priority",
            "assignee", "labels", "comment",
        ])
        f = issue.fields
        desc_raw = getattr(f, "description", None) or ""
        desc_text = _extract_adf_text(desc_raw) if isinstance(desc_raw, dict) else str(desc_raw)

        comments = []
        comment_obj = getattr(f, "comment", None)
        if comment_obj:
            for c in (getattr(comment_obj, "comments", []) or [])[:10]:
                body_raw = getattr(c, "body", "") or ""
                body_text = _extract_adf_text(body_raw) if isinstance(body_raw, dict) else str(body_raw)
                comments.append({
                    "author": getattr(getattr(c, "author", None), "displayName", ""),
                    "body": body_text[:500],
                })

        intg = _get_integration(db, user.tenant_id)
        base_url = intg.jira_url if intg else ""
        return {
            "key": issue.key,
            "summary": f.summary or "",
            "description": desc_text,
            "issue_type": getattr(getattr(f, "issuetype", None), "name", ""),
            "status": getattr(getattr(f, "status", None), "name", ""),
            "priority": getattr(getattr(f, "priority", None), "name", ""),
            "assignee": getattr(getattr(f, "assignee", None), "displayName", None),
            "labels": list(getattr(f, "labels", []) or []),
            "comments": comments,
            "url": f"{base_url}/browse/{issue.key}",
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
