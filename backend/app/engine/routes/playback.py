"""
Playback routes — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/playback_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/playback.py — APIRouter, port 8000 (consolidated)

Kaydedilmiş oturumları oynatma ve rapor endpoint'leri.
Geçici in-memory store yeterli — gerçek DB sonra.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/playback", tags=["engine", "playback"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ReplaySessionRequest(BaseModel):
    session_path: str = Field(..., min_length=1)
    headless: bool = True
    timeout: int = Field(10_000, ge=0)
    browser: str = Field("chromium", pattern="^(chromium|firefox|webkit)$")


class ReplayEventsRequest(BaseModel):
    events: list[dict] = Field(..., min_length=1)
    session_id: str = "inline"
    base_url: str = ""
    headless: bool = True
    timeout: int = Field(10_000, ge=0)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _reports_dir() -> Path:
    try:
        from app.config import settings as app_settings  # type: ignore[import]
        base = Path(app_settings.BASE_DIR)
    except Exception:
        base = Path(__file__).resolve().parents[4]
    reports = base / "reports" / "playback"
    reports.mkdir(parents=True, exist_ok=True)
    return reports


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/replay")
def replay_session(body: ReplaySessionRequest):
    """
    Kaydedilmiş oturumu Playwright ile oynatır.
    """
    p = Path(body.session_path)
    if not p.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum dosyası bulunamadı")

    try:
        from core.playback_engine import PlaybackEngine  # type: ignore[import]
        from playwright.sync_api import sync_playwright  # type: ignore[import]

        with sync_playwright() as pw:
            launcher = getattr(pw, body.browser, pw.chromium)
            browser = launcher.launch(headless=body.headless)
            page = browser.new_page()
            engine = PlaybackEngine(page, timeout=body.timeout)
            report = engine.replay_from_file(p)
            report_path = engine.save_report()
            browser.close()

        return {
            "ok": True,
            "report": report.to_dict(),
            "report_path": report_path,
            "summary": engine.summary(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/replay-events")
def replay_events(body: ReplayEventsRequest):
    """
    Doğrudan event listesi ile oynatma.
    """
    try:
        from core.playback_engine import PlaybackEngine  # type: ignore[import]
        from playwright.sync_api import sync_playwright  # type: ignore[import]

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=body.headless)
            page = browser.new_page()
            if body.base_url:
                page.goto(body.base_url, wait_until="domcontentloaded")
            engine = PlaybackEngine(page, timeout=body.timeout)
            report = engine.replay(body.events, session_id=body.session_id)
            report_path = engine.save_report()
            browser.close()

        return {
            "ok": True,
            "report": report.to_dict(),
            "report_path": report_path,
            "summary": engine.summary(),
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/reports")
def list_reports():
    """Playback raporlarını listeler."""
    try:
        reports_dir = _reports_dir()
        reports = []
        for f in sorted(reports_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                reports.append({
                    "file": f.name,
                    "path": str(f),
                    "session_id": data.get("session_id", ""),
                    "total": data.get("total", 0),
                    "passed": data.get("passed", 0),
                    "failed": data.get("failed", 0),
                    "healed": data.get("healed", 0),
                    "pass_rate": data.get("pass_rate", 0),
                    "started_at": data.get("started_at", ""),
                })
            except Exception:
                continue
        return {"ok": True, "reports": reports, "count": len(reports)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/reports/{filename:path}")
def get_report(filename: str):
    """Belirli bir playback raporunu döner."""
    try:
        reports_dir = _reports_dir()
        target = (reports_dir / filename).resolve()
        if not str(target).startswith(str(reports_dir.resolve())):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Geçersiz dosya yolu")
        if not target.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rapor bulunamadı")
        data = json.loads(target.read_text(encoding="utf-8"))
        return {"ok": True, "report": data}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
