"""
Accessibility routes — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/accessibility_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/accessibility.py — APIRouter, port 8000 (consolidated)

WCAG 2.1 testleri için REST endpoint'leri.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/a11y", tags=["engine", "accessibility"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class TestUrlRequest(BaseModel):
    url: str = Field(..., min_length=1)
    wcag_level: str = Field("AA", pattern="^(AA|AAA)$")
    ignore_rules: list[str] = Field(default_factory=list)
    use_axe: bool = False
    wait_for: str | None = None
    wait_ms: int = Field(1000, ge=0)


class TestBatchRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1)
    wcag_level: str = Field("AA", pattern="^(AA|AAA)$")
    ignore_rules: list[str] = Field(default_factory=list)


class GenerateReportRequest(BaseModel):
    url: str = Field(..., min_length=1)
    wcag_level: str = Field("AA", pattern="^(AA|AAA)$")
    include_warnings: bool = True


class UpdateConfigRequest(BaseModel):
    wcag_level: str | None = None
    browser_type: str | None = None
    headless: bool | None = None
    ignore_rules: list[str] | None = None
    timeout: int | None = None
    use_axe: bool | None = None


# ─── Config helpers ──────────────────────────────────────────────────────────

_CONFIG_PATH: Path | None = None


def _resolve_config_path() -> Path:
    """Backend BASE_DIR altındaki a11y_config.json yolunu döner."""
    try:
        from app.config import settings as app_settings  # type: ignore[import]
        base = Path(app_settings.BASE_DIR)
    except Exception:
        base = Path(__file__).resolve().parents[4]
    return base / "config" / "a11y_config.json"


def _get_config() -> dict:
    """config/a11y_config.json dosyasını okur."""
    cfg_path = _resolve_config_path()
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeError) as exc:
            logger.debug("a11y_config.json okunamadı: %s", exc)
    return {}


def _make_tester(config: dict | None = None):
    """AccessibilityTester örneği oluşturur."""
    from core.accessibility_tester import AccessibilityTester  # type: ignore[import]

    cfg = config or _get_config()
    return AccessibilityTester(
        wcag_level=cfg.get("wcag_level", "AA"),
        browser_type=cfg.get("browser_type", "chromium"),
        headless=cfg.get("headless", True),
        ignore_rules=cfg.get("ignore_rules", []),
        timeout=cfg.get("timeout", 30_000),
        use_axe=cfg.get("use_axe", False),
    )


# ─── Test Endpoints ──────────────────────────────────────────────────────────

@router.post("/test")
def test_url(body: TestUrlRequest):
    """
    Bir URL'yi erişilebilirlik açısından test eder.
    """
    try:
        tester = _make_tester({
            "wcag_level": body.wcag_level.upper(),
            "ignore_rules": body.ignore_rules,
            "use_axe": body.use_axe,
        })
        result = tester.test_url(body.url.strip(), wait_for=body.wait_for, wait_ms=body.wait_ms)
        if result.error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"ok": False, "error": result.error, "result": tester.to_dict(result)},
            )
        return {"ok": True, "result": tester.to_dict(result)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/test/batch")
def test_batch(body: TestBatchRequest):
    """
    Birden fazla URL'yi erişilebilirlik açısından test eder.
    """
    try:
        tester = _make_tester({"wcag_level": body.wcag_level.upper(), "ignore_rules": body.ignore_rules})
        results = [tester.to_dict(tester.test_url(url.strip())) for url in body.urls]
        avg_score = sum(r["score"] for r in results) / len(results) if results else 0
        total_violations = sum(r["violation_count"] for r in results)
        return {
            "ok": True,
            "summary": {
                "tested": len(results),
                "avg_score": round(avg_score, 2),
                "total_violations": total_violations,
            },
            "results": results,
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ─── Rapor Endpoints ─────────────────────────────────────────────────────────

@router.post("/report")
def generate_report(body: GenerateReportRequest):
    """
    Bir URL için erişilebilirlik testi yapar ve HTML rapor üretir.
    """
    try:
        tester = _make_tester({"wcag_level": body.wcag_level.upper()})
        result = tester.test_url(body.url.strip())
        report_path = tester.generate_report(result, include_warnings=body.include_warnings)
        return {"ok": True, "report_path": report_path, "result": tester.to_dict(result)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/report/download")
def download_report(path: str = ""):
    """
    Önceden oluşturulmuş raporu indirir.

    Query params:
      path — Rapor dosyasının mutlak yolu
    """
    if not path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="path parametresi gerekli")

    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rapor dosyası bulunamadı")

    # Güvenlik: sadece proje BASE_DIR altındaki dosyalara izin ver
    try:
        try:
            from app.config import settings as app_settings  # type: ignore[import]
            base = Path(app_settings.BASE_DIR)
        except Exception:
            base = Path(__file__).resolve().parents[4]
        p.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Geçersiz dosya yolu")

    return FileResponse(str(p), media_type="text/html", filename=p.name)


# ─── Kural Bilgisi ───────────────────────────────────────────────────────────

@router.get("/rules")
def list_rules():
    """Desteklenen WCAG kurallarını listeler."""
    try:
        from core.accessibility_tester import WCAG_RULES  # type: ignore[import]

        rules = [
            {
                "id": rule_id,
                "description": info["description"],
                "wcag_criteria": info["wcag"],
                "severity": info["severity"],
                "weight": info["weight"],
                "help_url": info["help_url"],
            }
            for rule_id, info in WCAG_RULES.items()
        ]
        return {"ok": True, "rules": rules, "count": len(rules)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/config")
def get_config():
    """Mevcut erişilebilirlik konfigürasyonunu döner."""
    return {"ok": True, "config": _get_config()}


@router.put("/config")
def update_config(body: UpdateConfigRequest):
    """
    Erişilebilirlik konfigürasyonunu günceller.
    """
    try:
        cfg_path = _resolve_config_path()
        cfg_path.parent.mkdir(exist_ok=True)

        current = _get_config()
        patch = body.model_dump(exclude_none=True)
        current.update(patch)
        cfg_path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"ok": True, "config": current}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
