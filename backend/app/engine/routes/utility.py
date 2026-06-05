from __future__ import annotations

"""
Utility routes — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/utility_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/utility.py — APIRouter, port 8000 (consolidated)

GET  /api/settings               — Mevcut ayarları oku (.env)
POST /api/settings               — Ayarları .env'e kaydet
GET  /api/stats                  — Çalışma geçmişi ve istatistikler
GET  /api/reports/comprehensive  — Kapsamlı raporlar
GET  /api/health                 — Servis sağlık kontrolü
POST /api/request                — HTTP proxy
GET  /api/export                 — Feature dosyalarını ZIP olarak indir
"""

import io
import time
import zipfile

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["engine", "utility"])


# ─── Schemas ─────────────────────────────────────────────────────────────

class SettingsOut(BaseModel):
    BASE_URL: str
    BROWSER: str
    HEADLESS: str
    OPENAI_MODEL: str
    OPENAI_API_BASE: str
    has_api_key: bool


class SettingsSaveRequest(BaseModel):
    BASE_URL: str | None = None
    BROWSER: str | None = None
    HEADLESS: str | None = None
    OPENAI_MODEL: str | None = None
    OPENAI_API_KEY: str | None = None
    OPENAI_API_BASE: str | None = None


class HeaderItem(BaseModel):
    key: str
    value: str


class ProxyRequest(BaseModel):
    url: str = Field(..., min_length=1, description="Hedef URL")
    method: str = "GET"
    headers: list[HeaderItem] = []
    body: str = ""


# ─── Routes ──────────────────────────────────────────────────────────────

@router.get("/api/settings", response_model=SettingsOut)
def get_settings():
    """Mevcut .env ayarlarını okur."""
    try:
        from config.settings import BASE_DIR, settings  # type: ignore[import]
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))

    env_file = BASE_DIR / ".env"
    env_data: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env_data[k.strip()] = v.strip()

    return {
        "BASE_URL": env_data.get("BASE_URL", settings.BASE_URL),
        "BROWSER": env_data.get("BROWSER", settings.BROWSER),
        "HEADLESS": env_data.get("HEADLESS", str(settings.HEADLESS).lower()),
        "OPENAI_MODEL": env_data.get("OPENAI_MODEL", settings.OPENAI_MODEL),
        "OPENAI_API_BASE": env_data.get("OPENAI_API_BASE", settings.OPENAI_BASE_URL),
        "has_api_key": bool(env_data.get("OPENAI_API_KEY", "")),
    }


@router.post("/api/settings")
def save_settings(body: SettingsSaveRequest):
    """Ayarları .env dosyasına yazar."""
    try:
        from config.settings import BASE_DIR  # type: ignore[import]
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))

    env_file = BASE_DIR / ".env"
    existing: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()

    mapping = {
        "BASE_URL": "BASE_URL",
        "BROWSER": "BROWSER",
        "HEADLESS": "HEADLESS",
        "OPENAI_MODEL": "OPENAI_MODEL",
        "OPENAI_API_KEY": "OPENAI_API_KEY",
        "OPENAI_API_BASE": "OPENAI_API_BASE",
    }
    data = body.model_dump(exclude_none=True)
    for key, env_key in mapping.items():
        if key in data:
            existing[env_key] = str(data[key])

    content = "\n".join(f"{k}={v}" for k, v in existing.items())
    env_file.write_text(content, encoding="utf-8")
    return {"ok": True}


@router.get("/api/stats")
def stats():
    """Çalışma istatistikleri ve geçmişi döndürür."""
    try:
        from core.db import get_run_history, get_run_stats  # type: ignore[import]
        return {"totals": get_run_stats(), "history": get_run_history()}
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/api/reports/comprehensive")
def reports_comprehensive():
    """Kapsamlı raporları döndürür."""
    try:
        from core.db import get_comprehensive_reports  # type: ignore[import]
        return get_comprehensive_reports()
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/api/health")
def health():
    """Servis sağlık kontrolü."""
    return {"status": "ok", "timestamp": time.time()}


@router.post("/api/request")
def proxy_request(body: ProxyRequest):
    """Verilen URL'e HTTP isteği gönderir ve yanıtı döndürür (proxy)."""
    import requests as req  # type: ignore[import]

    url = body.url
    if not url.startswith("http"):
        url = "http://" + url

    req_headers = {
        h.key: h.value
        for h in body.headers
        if h.key and h.value
    }

    try:
        start = time.time()
        response = req.request(
            body.method.upper(),
            url,
            headers=req_headers,
            data=body.body.encode("utf-8") if body.body else None,
            timeout=30,
        )
        duration = (time.time() - start) * 1000
        return {
            "status": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "time": duration,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/api/export")
def export_data():
    """Feature dosyalarını ZIP arşivi olarak indirir."""
    try:
        from config.settings import settings  # type: ignore[import]
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        if settings.FEATURES_DIR.exists():
            for f in settings.FEATURES_DIR.rglob("*.feature"):
                rel_path = f.relative_to(settings.FEATURES_DIR)
                zf.write(f, arcname=f"features/{rel_path}")
    memory_file.seek(0)

    filename = f"test_automation_export_{int(time.time())}.zip"
    return StreamingResponse(
        memory_file,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
