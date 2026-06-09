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
  POST /api/jira/webhook/jira-incoming      - Jira'dan gelen webhook event'lerini işle
"""

from __future__ import annotations

import hmac
import ipaddress
import logging
import os
import socket
from typing import Annotated, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_current_user, get_optional_user
from app.infra.database import get_db
from app.infra.models import User

from .models import JiraIntegration

JIRA_WEBHOOK_SECRET = os.environ.get("JIRA_WEBHOOK_SECRET", "")


def _is_ssrf_blocked(url: str) -> bool:
    """RFC-1918, link-local ve loopback adresleri engelle (SSRF koruması)."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return True
        try:
            addr = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(addr)
            return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified
        except Exception:
            return False
    except Exception:
        return True

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jira", tags=["jira"])

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]


# ─── Schemas ─────────────────────────────────────────────────────────────────

class JiraConfigSave(BaseModel):
    url: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    token: str = Field(default="")  # Boş bırakılırsa mevcut token korunur
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


def create_jira_issue(
    config: dict,
    title: str,
    description: str = "",
    issue_type: str = "Bug",
    priority: str = "Medium",
) -> Optional[str]:
    """Jira'da issue oluştur, başarılıysa issue_key döndür; hata olursa None.

    Args:
        config: base_url, email, token, project_key anahtarlarını içeren dict.
        title: Issue özeti (255 karakterle sınırlandırılır).
        description: İsteğe bağlı açıklama metni (2000 karakterle sınırlandırılır).
        issue_type: Jira issue türü (varsayılan: "Bug").
        priority: Jira öncelik seviyesi (varsayılan: "Medium").

    Returns:
        Oluşturulan issue'nun key'i (örn. "PROJ-123") veya None.
    """
    import httpx  # noqa: PLC0415 — geç import, httpx isteğe bağlı bağımlılık

    try:
        r = httpx.post(
            f"{config['base_url'].rstrip('/')}/rest/api/3/issue",
            auth=(config["email"], config["token"]),
            json={
                "fields": {
                    "project": {"key": config["project_key"]},
                    "summary": title[:255],
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": description[:2000]}],
                            }
                        ],
                    },
                    "issuetype": {"name": issue_type},
                    "priority": {"name": priority},
                }
            },
            timeout=10.0,
        )
        if r.is_success:
            return r.json().get("key")
        logger.warning(
            "Jira issue oluşturulamadı: HTTP %s — %s",
            r.status_code,
            r.text[:200],
        )
    except Exception as exc:
        logger.warning("Jira issue oluşturulamadı: %s", exc)
    return None


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
def jira_get_config(db: DB, user: Annotated[User, Depends(get_current_user)]):
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
def jira_save_config(body: JiraConfigSave, db: DB, user: Annotated[User, Depends(get_current_user)]):
    """Jira bağlantı ayarlarını DB'ye kaydeder (upsert)."""
    url = body.url.strip().rstrip("/")
    if not url.lower().startswith(("http://", "https://")):
        raise HTTPException(400, "Jira URL'i http:// veya https:// ile başlamalı")
    if _is_ssrf_blocked(url):
        raise HTTPException(400, "Geçersiz Jira URL'i — iç ağ adresleri kullanılamaz")
    intg = _get_integration(db, user.tenant_id)
    new_token = body.token.strip()
    if intg:
        intg.jira_url = url
        intg.email = body.email.strip()
        if new_token:  # Boş token → mevcut token koru
            intg.api_token = new_token
        intg.default_project_key = body.project_key.strip() or None
    else:
        intg = JiraIntegration(
            tenant_id=user.tenant_id,
            jira_url=url,
            email=body.email.strip(),
            api_token=new_token,
            default_project_key=body.project_key.strip() or None,
        )
        db.add(intg)
    db.commit()
    return {"ok": True}


@router.delete("/config", status_code=status.HTTP_200_OK)
def jira_delete_config(db: DB, user: Annotated[User, Depends(get_current_user)]):
    """Jira bağlantısını devre dışı bırakır (soft delete)."""
    intg = _get_integration(db, user.tenant_id)
    if intg:
        intg.is_active = False
        db.commit()
    return {"ok": True}


@router.post("/test-connection")
def jira_test_connection(db: DB, user: Annotated[User, Depends(get_current_user)]):
    client, err = _get_jira_client(db, user.tenant_id)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    try:
        me = client.myself()
        return {"ok": True, "user": me.get("displayName", me.get("name", ""))}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/projects")
def jira_list_projects(db: DB, user: Annotated[User, Depends(get_current_user)]):
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
    user: Annotated[User, Depends(get_current_user)],
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
def jira_get_issue(issue_key: str, db: DB, user: Annotated[User, Depends(get_current_user)]):
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


# ─── Webhook (Jira → Neurex) ──────────────────────────────────────────────────

def _sync_defect_link_status(issue_key: str, new_status: str) -> None:
    """BackgroundTask: DefectLink kaydını Jira'dan gelen yeni status ile güncelle."""
    try:
        from app.infra.database import SessionLocal  # noqa: PLC0415

        db: Session = SessionLocal()
        try:
            # DefectLink modeli test_management domain'inde tanımlanmış olabilir;
            # import hatası durumunda sessizce atla.
            from app.domains.test_management.models import DefectLink  # noqa: PLC0415

            links = (
                db.query(DefectLink)
                .filter(DefectLink.external_key == issue_key, DefectLink.external_source == "jira")
                .all()
            )
            for link in links:
                link.status = new_status
            if links:
                db.commit()
                logger.info(
                    "DefectLink status güncellendi: issue=%s yeni_durum=%s kayıt_sayısı=%d",
                    issue_key,
                    new_status,
                    len(links),
                )
        except ImportError:
            logger.debug("DefectLink modeli bulunamadı — status sync atlandı.")
        finally:
            db.close()
    except Exception as exc:
        logger.warning("DefectLink status sync hatası (issue=%s): %s", issue_key, exc)


def _delete_defect_links(issue_key: str) -> None:
    """BackgroundTask: Silinen Jira issue'ya bağlı DefectLink kayıtlarını kaldır."""
    try:
        from app.infra.database import SessionLocal  # noqa: PLC0415

        db: Session = SessionLocal()
        try:
            from app.domains.test_management.models import DefectLink  # noqa: PLC0415

            deleted = (
                db.query(DefectLink)
                .filter(DefectLink.external_key == issue_key, DefectLink.external_source == "jira")
                .delete(synchronize_session=False)
            )
            if deleted:
                db.commit()
                logger.info(
                    "DefectLink silindi: issue=%s kayıt_sayısı=%d",
                    issue_key,
                    deleted,
                )
        except ImportError:
            logger.debug("DefectLink modeli bulunamadı — delete sync atlandı.")
        finally:
            db.close()
    except Exception as exc:
        logger.warning("DefectLink delete sync hatası (issue=%s): %s", issue_key, exc)


def _webhook_secret_required() -> bool:
    forced = os.environ.get("JIRA_REQUIRE_WEBHOOK_SECRET", "").lower() in {"1", "true", "yes"}
    return forced or settings.is_production_like


@router.post("/webhook/jira-incoming", include_in_schema=True)
async def jira_incoming_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_atlassian_token: Optional[str] = Header(None, alias="x-atlassian-token"),
) -> dict:
    """Jira'dan gelen webhook event'lerini işle.

    Desteklenen event'ler:
    - jira:issue_updated  → DefectLink.status güncelleme (background task)
    - jira:issue_deleted  → DefectLink kaydının silinmesi (background task)

    Atlassian, webhook isteğinin ürettiği herhangi bir HTTP 200 yanıtını başarı
    sayar; bu nedenle her zaman ``{"received": True}`` döner ve ağır işler
    background task'a devredilir.
    """
    if _webhook_secret_required() and not JIRA_WEBHOOK_SECRET:
        raise HTTPException(503, "JIRA_WEBHOOK_SECRET ayarı zorunlu ama yapılandırılmamış")
    if JIRA_WEBHOOK_SECRET:
        provided = x_atlassian_token or ""
        if not hmac.compare_digest(provided, JIRA_WEBHOOK_SECRET):
            raise HTTPException(401, "Geçersiz Jira webhook token")

    try:
        payload = await request.json()
    except Exception:
        logger.warning("Jira webhook: geçersiz JSON gövdesi")
        return {"received": False, "error": "invalid_json"}

    event_type: str = payload.get("webhookEvent", "")
    issue: dict = payload.get("issue", {})
    issue_key: str = issue.get("key", "")

    if event_type == "jira:issue_updated":
        new_status: str = (
            issue.get("fields", {}).get("status", {}).get("name", "")
        )
        logger.info("Jira webhook: issue güncellendi — %s → %s", issue_key, new_status)
        if issue_key and new_status:
            background_tasks.add_task(_sync_defect_link_status, issue_key, new_status)

    elif event_type == "jira:issue_deleted":
        logger.info("Jira webhook: issue silindi — %s", issue_key)
        if issue_key:
            background_tasks.add_task(_delete_defect_links, issue_key)

    else:
        logger.debug("Jira webhook: bilinmeyen event — %s", event_type)

    return {"received": True, "event": event_type}
