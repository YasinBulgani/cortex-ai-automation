"""
Visual Regression route'ları — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/visual_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/visual.py — APIRouter, port 8000 (consolidated)

Endpoint'ler:
  GET    /api/visual/baselines                         — Tüm baseline'ları listele
  GET    /api/visual/baselines/{domain}/{test_name}    — Baseline meta verisi
  DELETE /api/visual/baselines/{domain}/{test_name}    — Baseline sil
  POST   /api/visual/baselines/upload                  — Baseline yükle (multipart)
  POST   /api/visual/compare                           — Görsel karşılaştırma
  POST   /api/visual/compare/upload                    — Yüklenen dosyayla karşılaştırma
  POST   /api/visual/batch                             — Toplu karşılaştırma
  POST   /api/visual/diff-image                        — Diff görüntüsü üret (binary response)
"""
import json
import logging
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/visual", tags=["engine", "visual"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_config() -> dict:
    """config/visual_config.json dosyasını okur."""
    try:
        from app.config import settings  # type: ignore[import]
        cfg_path = Path(settings.BASE_DIR) / "config" / "visual_config.json"
    except (ImportError, AttributeError):
        cfg_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "config" / "visual_config.json"

    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _get_screenshots_upload_dir() -> Path:
    """Geçici upload dizinini döndürür."""
    try:
        from app.config import settings  # type: ignore[import]
        base = Path(settings.SCREENSHOTS_DIR)
    except (ImportError, AttributeError):
        base = Path(__file__).resolve().parent.parent.parent.parent.parent / "screenshots"
    upload_dir = base / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _make_tester(domain: str = "default"):
    """VisualRegressionTester örneği oluşturur."""
    try:
        from core.visual_regression import create_visual_tester  # type: ignore[import]
        cfg = _get_config()
        domain_cfg = cfg.get("domains", {}).get(domain, cfg)
        return create_visual_tester(domain=domain, config=domain_cfg)
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Visual regression modülü yüklenemedi: {exc}",
        )


def _get_baseline_manager():
    """BaselineManager örneği oluşturur."""
    try:
        from core.visual_regression import BaselineManager  # type: ignore[import]
        cfg = _get_config()
        return BaselineManager(cfg.get("baselines_dir"))
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Visual regression modülü yüklenemedi: {exc}",
        )


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    test_name: str = Field(..., min_length=1, description="Test adı")
    domain: str = Field("default", description="Domain adı")
    url: Optional[str] = Field(None, description="Screenshot alınacak URL (Playwright gerekir)")
    update_baseline: bool = Field(False, description="True ise sonucu baseline olarak kaydeder")
    threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="SSIM eşiği (0-1)")
    ignore_regions: list[dict] = Field(default_factory=list, description="Maskelenecek bölgeler [{x,y,w,h},...]")


class BatchTestCase(BaseModel):
    test_name: str
    url: Optional[str] = None


class BatchCompareRequest(BaseModel):
    domain: str = Field("default", description="Domain adı")
    test_cases: list[BatchTestCase] = Field(..., min_length=1, description="Test case listesi")
    threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="SSIM eşiği")


# ─── Routes — Baseline Yönetimi ───────────────────────────────────────────────

@router.get("/baselines")
def list_baselines(domain: Optional[str] = Query(None, description="Filtre için domain adı")) -> dict:
    """Tüm baseline'ları veya belirli domain'e ait olanları listeler."""
    try:
        mgr = _get_baseline_manager()
        baselines = mgr.list_baselines(domain=domain)
        return {"ok": True, "baselines": baselines, "count": len(baselines)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/baselines/{domain}/{test_name:path}")
def get_baseline(domain: str, test_name: str) -> dict:
    """Belirli bir baseline'ın meta verisini döner."""
    try:
        mgr = _get_baseline_manager()
        entry = mgr.get_baseline(domain, test_name)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Baseline bulunamadı",
            )
        return {"ok": True, "baseline": entry}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.delete("/baselines/{domain}/{test_name:path}", status_code=status.HTTP_200_OK)
def delete_baseline(domain: str, test_name: str) -> dict:
    """Bir baseline'ı siler."""
    try:
        mgr = _get_baseline_manager()
        deleted = mgr.delete_baseline(domain, test_name)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Baseline bulunamadı",
            )
        return {"ok": True, "message": "Baseline silindi"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/baselines/upload", status_code=status.HTTP_201_CREATED)
async def upload_baseline(
    file: Annotated[UploadFile, File(description="PNG/JPEG dosyası")],
    domain: Annotated[str, Form()] = "default",
    test_name: Annotated[str, Form()] = "",
) -> dict:
    """Screenshot dosyasını baseline olarak yükler."""
    if not test_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="test_name gerekli",
        )
    try:
        tmp_dir = _get_screenshots_upload_dir()
        tmp_path = tmp_dir / f"upload_{domain}_{test_name}.png"
        tmp_path.write_bytes(await file.read())

        mgr = _get_baseline_manager()
        entry = mgr.save_baseline(tmp_path, domain, test_name)
        tmp_path.unlink(missing_ok=True)

        return {"ok": True, "baseline": entry}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# ─── Routes — Karşılaştırma ───────────────────────────────────────────────────

@router.post("/compare")
def compare_visual(body: CompareRequest) -> dict:
    """
    Görsel karşılaştırma yapar.

    url veya update_baseline=True gereklidir (Playwright tabanlı screenshot için url zorunlu).
    """
    if not body.url and not body.update_baseline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="url gerekli (Playwright gerekir)",
        )

    try:
        cfg = _get_config()
        if body.threshold is not None:
            cfg["threshold"] = body.threshold

        tester = _make_tester(body.domain)
        result = tester.compare(
            test_name=body.test_name,
            url=body.url,
            update_baseline=body.update_baseline,
            ignore_regions=body.ignore_regions,
        )
        return {"ok": True, "result": result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/compare/upload")
async def compare_with_upload(
    file: Annotated[UploadFile, File(description="PNG dosyası")],
    test_name: Annotated[str, Form()] = "",
    domain: Annotated[str, Form()] = "default",
    threshold: Annotated[float, Form()] = 0.95,
) -> dict:
    """Yüklenen screenshot ile baseline karşılaştırır."""
    if not test_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="test_name gerekli",
        )

    try:
        tmp_dir = _get_screenshots_upload_dir()
        tmp_path = tmp_dir / f"cmp_{domain}_{test_name}.png"
        tmp_path.write_bytes(await file.read())

        tester = _make_tester(domain)
        tester.threshold = threshold
        result = tester.compare(test_name=test_name, screenshot_path=tmp_path)
        tmp_path.unlink(missing_ok=True)

        return {"ok": True, "result": result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/batch")
def batch_compare(body: BatchCompareRequest) -> dict:
    """Toplu görsel karşılaştırma."""
    try:
        cfg = _get_config()
        if body.threshold is not None:
            cfg["threshold"] = body.threshold

        tester = _make_tester(body.domain)
        test_cases = [tc.model_dump() for tc in body.test_cases]
        batch_result = tester.batch_test(test_cases)

        report_path = tester.generate_report(batch_result)
        batch_result["report_path"] = report_path

        return {"ok": True, "result": batch_result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# ─── Routes — Diff Görüntüsü ──────────────────────────────────────────────────

@router.post("/diff-image")
async def create_diff_image(
    baseline: Annotated[UploadFile, File(description="Baseline PNG dosyası")],
    current: Annotated[UploadFile, File(description="Güncel PNG dosyası")],
) -> FileResponse:
    """İki yüklenen görüntü arasındaki fark görüntüsünü PNG olarak döner."""
    try:
        from core.visual_regression import PixelDiffVisualizer  # type: ignore[import]
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Visual regression modülü yüklenemedi: {exc}",
        )

    try:
        tmp_dir = _get_screenshots_upload_dir()
        bl_path  = tmp_dir / "diff_baseline.png"
        cur_path = tmp_dir / "diff_current.png"
        out_path = tmp_dir / "diff_output.png"

        bl_path.write_bytes(await baseline.read())
        cur_path.write_bytes(await current.read())

        PixelDiffVisualizer.create_diff_image(bl_path, cur_path, out_path)

        if not out_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Diff görüntüsü üretilemedi",
            )
        return FileResponse(
            path=str(out_path),
            media_type="image/png",
            filename="diff.png",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
