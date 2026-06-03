"""
Jira entegrasyonu routes — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/jira_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/jira.py — APIRouter, port 8000 (consolidated)

Endpoints:
  GET  /api/jira/config                     - Mevcut Jira ayarlarını getir
  POST /api/jira/config                     - Jira bağlantı ayarlarını kaydet
  POST /api/jira/test-connection            - Jira bağlantısını test et
  GET  /api/jira/projects                   - Jira projelerini listele
  POST /api/jira/bugs/{bug_id}/push         - Bug'ı Jira'ya aktar
  POST /api/jira/testcases/{tc_id}/link     - Test case'i Jira issue'ya bağla
  POST /api/jira/runs/{run_id}/sync         - Test run sonuçlarını Jira'ya sync et
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jira", tags=["engine", "jira"])

JIRA_CONFIG_PATH = Path("/tmp/jira_config.json")


# ─── Schemas ─────────────────────────────────────────────────────────────────

class JiraConfigSave(BaseModel):
    url: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    token: str = Field(..., min_length=1)
    project_key: str = ""


class BugPushBody(BaseModel):
    project_key: Optional[str] = None


class TestCaseLinkBody(BaseModel):
    jira_key: str = Field(..., min_length=1)


class RunSyncBody(BaseModel):
    jira_key: str = Field(..., min_length=1)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_jira_config() -> dict:
    if JIRA_CONFIG_PATH.exists():
        try:
            return json.loads(JIRA_CONFIG_PATH.read_text())
        except Exception:
            pass
    return {}


def save_jira_config(config: dict) -> None:
    JIRA_CONFIG_PATH.write_text(json.dumps(config, indent=2))


def get_jira_client():
    """Jira API istemcisi döndürür. jira kütüphanesi yoksa (None, hata_mesajı) döner."""
    config = load_jira_config()
    if not config.get("url") or not config.get("email") or not config.get("token"):
        return None, "Jira yapılandırması eksik"
    try:
        from jira import JIRA  # type: ignore[import]
        client = JIRA(
            server=config["url"],
            basic_auth=(config["email"], config["token"]),
        )
        return client, None
    except ImportError:
        return None, "jira kütüphanesi yüklü değil (pip install jira)"
    except Exception as exc:
        return None, str(exc)


# ─── In-memory store (placeholder) ───────────────────────────────────────────

class _BugStore:
    """Geçici in-memory store. Migration tamamlanınca SQLAlchemy repository kullanılacak."""

    def __init__(self):
        self._bugs: dict[int, dict] = {}
        self._next_id = 1

    def get_bugs(self) -> list[dict]:
        return list(self._bugs.values())

    def get_bug(self, bug_id: int) -> Optional[dict]:
        return self._bugs.get(bug_id)

    def update_jira_key(self, bug_id: int, jira_key: str) -> None:
        if bug_id in self._bugs:
            self._bugs[bug_id]["jira_key"] = jira_key


class _TestCaseStore:
    """Geçici in-memory store."""

    def __init__(self):
        self._cases: dict[int, dict] = {}
        self._next_id = 1

    def get_test_case(self, tc_id: int) -> Optional[dict]:
        return self._cases.get(tc_id)


class _RunStore:
    """Geçici in-memory store."""

    def __init__(self):
        self._results: dict[int, list[dict]] = {}

    def get_run_results(self, run_id: int) -> list[dict]:
        return self._results.get(run_id, [])


_bug_store = _BugStore()
_tc_store = _TestCaseStore()
_run_store = _RunStore()


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/config")
def jira_get_config():
    config = load_jira_config()
    # Token'ı maskele
    if config.get("token"):
        config["token"] = "***" + config["token"][-4:]
    return config


@router.post("/config", status_code=status.HTTP_200_OK)
def jira_save_config(body: JiraConfigSave):
    url = body.url.strip().rstrip("/")
    email = body.email.strip()
    token = body.token.strip()
    project_key = body.project_key.strip()

    save_jira_config({
        "url": url,
        "email": email,
        "token": token,
        "project_key": project_key,
    })
    return {"ok": True}


@router.post("/test-connection")
def jira_test_connection():
    client, err = get_jira_client()
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    try:
        me = client.myself()
        return {"ok": True, "user": me.get("displayName", me.get("name"))}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/projects")
def jira_list_projects():
    client, err = get_jira_client()
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    try:
        projects = client.projects()
        return [{"key": p.key, "name": p.name} for p in projects]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/bugs/{bug_id}/push")
def jira_push_bug(bug_id: int, body: BugPushBody):
    client, err = get_jira_client()
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    config = load_jira_config()
    project_key = (body.project_key or "").strip() or config.get("project_key", "")
    if not project_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Jira proje anahtarı gerekli")

    bug = _bug_store.get_bug(bug_id)
    if not bug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug bulunamadı")

    if bug.get("jira_key"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bu bug zaten Jira'ya aktarıldı: {bug['jira_key']}",
        )

    severity_priority_map = {
        "Critical": "Highest",
        "High": "High",
        "Medium": "Medium",
        "Low": "Low",
    }
    priority = severity_priority_map.get(bug.get("severity", "Medium"), "Medium")

    try:
        issue = client.create_issue(fields={
            "project": {"key": project_key},
            "summary": bug["title"],
            "description": bug.get("description", ""),
            "issuetype": {"name": "Bug"},
            "priority": {"name": priority},
        })
        _bug_store.update_jira_key(bug_id, issue.key)
        return {
            "ok": True,
            "jira_key": issue.key,
            "url": f"{config['url']}/browse/{issue.key}",
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/testcases/{tc_id}/link")
def jira_link_testcase(tc_id: int, body: TestCaseLinkBody):
    """Test case'i mevcut bir Jira issue'ya bağlar (comment olarak)."""
    client, err = get_jira_client()
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    tc = _tc_store.get_test_case(tc_id)
    if not tc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case bulunamadı")

    steps_text = "\n".join(
        [f"{i + 1}. {s['action']} → {s['expected']}" for i, s in enumerate(tc.get("steps", []))]
    )
    comment = (
        f"*Test Case Bağlandı:* {tc['title']}\n"
        f"*Öncelik:* {tc.get('priority', 'P2')}\n\n"
        f"*Adımlar:*\n{steps_text}"
    )

    try:
        client.add_comment(body.jira_key, comment)
        return {"ok": True, "jira_key": body.jira_key}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/runs/{run_id}/sync")
def jira_sync_run(run_id: int, body: RunSyncBody):
    """Test run sonuçlarını özet olarak Jira issue'ya yorum ekler."""
    client, err = get_jira_client()
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    results = _run_store.get_run_results(run_id)

    status_counts: dict[str, int] = {}
    for r in results:
        s = r.get("status", "Not Run")
        status_counts[s] = status_counts.get(s, 0) + 1

    summary_lines = [f"*Test Run #{run_id} Sonuçları:*"]
    for run_status, count in status_counts.items():
        summary_lines.append(f"- {run_status}: {count}")

    failed = [r for r in results if r.get("status") == "Fail"]
    if failed:
        summary_lines.append("\n*Başarısız Test Case'ler:*")
        for r in failed[:10]:
            note = f" — {r['notes']}" if r.get("notes") else ""
            summary_lines.append(f"- {r['title']}{note}")

    try:
        client.add_comment(body.jira_key, "\n".join(summary_lines))
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
