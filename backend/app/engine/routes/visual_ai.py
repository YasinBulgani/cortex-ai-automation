"""
Visual AI routes — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/visual_ai_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/visual_ai.py — APIRouter, port 8000 (consolidated)

Endpoints:
  GET  /api/visual-ai/health            - Servis sağlık kontrolü
  POST /api/visual-ai/analyze           - Görsel fark analizi
  POST /api/visual-ai/smart-update      - Akıllı baseline güncelleme
  POST /api/visual-ai/report            - Analiz raporu oluştur
  GET  /api/visual-ai/baseline-status   - Baseline durumunu getir
  GET  /api/visual-ai/statistics        - Servis istatistikleri
  GET  /api/visual-ai/config            - Servis yapılandırması
"""

import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/visual-ai", tags=["engine", "visual-ai"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    current_image: str = Field(..., min_length=1, description="Path to current screenshot")
    baseline_name: str = "unknown"
    baseline_image: Optional[str] = None


class SmartUpdateRequest(BaseModel):
    baseline_name: str = Field(..., min_length=1)
    current_image: str = Field(..., min_length=1)
    baseline_image: Optional[str] = None
    force: bool = False


class ReportRequest(BaseModel):
    analysis: dict[str, Any] = Field(..., description="Analysis object returned by /analyze")
    baseline_name: str = "unknown"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _resolve_baseline_path(baseline_image: Optional[str], baseline_name: str) -> str:
    if baseline_image:
        return baseline_image
    baselines_dir = os.path.join(os.getcwd(), "data", "visual-baselines")
    return os.path.join(baselines_dir, f"{baseline_name}.png")


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/health")
def health():
    """Health check for visual AI service."""
    return {"status": "healthy", "service": "visual_ai", "version": "1.0.0"}


@router.post("/analyze")
def analyze_visual_difference(body: AnalyzeRequest):
    """
    Analyze visual difference between current and baseline images.
    """
    try:
        from core.visual_ai import get_visual_ai_analyzer  # type: ignore[import]

        baseline_path = _resolve_baseline_path(body.baseline_image, body.baseline_name)
        analyzer = get_visual_ai_analyzer()
        analysis = analyzer.analyze_visual_difference(
            body.current_image,
            baseline_path,
            body.baseline_name,
        )

        anomalies_data = [
            {
                "type": a.type,
                "location": a.location,
                "severity": a.severity,
                "confidence": a.confidence,
                "description": a.description,
            }
            for a in analysis.anomalies
        ]

        return {
            "success": True,
            "baseline_name": body.baseline_name,
            "similarity": float(analysis.similarity),
            "anomalies": anomalies_data,
            "has_anomalies": analysis.has_anomalies,
            "recommendations": analysis.recommendations,
            "should_update_baseline": analysis.should_update_baseline,
        }

    except Exception as exc:
        logger.error(f"Visual analysis failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/smart-update")
def smart_baseline_update(body: SmartUpdateRequest):
    """
    Intelligently decide whether to update baseline.
    """
    try:
        from core.visual_ai import SmartBaselineManager  # type: ignore[import]

        baseline_path = _resolve_baseline_path(body.baseline_image, body.baseline_name)
        baselines_dir = os.path.dirname(baseline_path)
        manager = SmartBaselineManager(baselines_dir)
        result = manager.smart_update_baseline(
            body.baseline_name,
            body.current_image,
            baseline_path,
            body.force,
        )

        return {"success": True, **result}

    except Exception as exc:
        logger.error(f"Smart baseline update failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/report")
def generate_report(body: ReportRequest):
    """
    Generate visual analysis report from a previously obtained analysis object.
    """
    try:
        from core.visual_ai import get_visual_ai_analyzer  # type: ignore[import]

        analyzer = get_visual_ai_analyzer()

        # Reconstruct a lightweight analysis object from the dict payload
        class _AnalysisReport:
            def __init__(self, data: dict):
                self.similarity = data.get("similarity", 0)
                self.anomalies = [
                    type("Anomaly", (), {
                        "type": a["type"],
                        "severity": a["severity"],
                        "description": a["description"],
                    })()
                    for a in data.get("anomalies", [])
                ]
                self.recommendations = data.get("recommendations", [])

        analysis_obj = _AnalysisReport(body.analysis)
        report = analyzer.generate_analysis_report(analysis_obj, body.baseline_name)

        return {"success": True, "baseline_name": body.baseline_name, "report": report}

    except Exception as exc:
        logger.error(f"Report generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/baseline-status")
def get_baseline_status(
    baseline_name: str,
    baselines_dir: Optional[str] = None,
):
    """
    Get status of a named baseline.

    Query parameters:
    - baseline_name: Name of the baseline (required)
    - baselines_dir: Optional directory (default: data/visual-baselines)
    """
    try:
        from core.visual_ai import SmartBaselineManager  # type: ignore[import]

        resolved_dir = baselines_dir or os.path.join(os.getcwd(), "data", "visual-baselines")
        manager = SmartBaselineManager(resolved_dir)
        baseline_status = manager.get_baseline_status(baseline_name)

        return {"success": True, "baseline_name": baseline_name, **baseline_status}

    except Exception as exc:
        logger.error(f"Failed to get baseline status: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/statistics")
def get_statistics():
    """Get visual AI service statistics."""
    try:
        from core.visual_ai import get_visual_ai_analyzer  # type: ignore[import]

        analyzer = get_visual_ai_analyzer()
        return {
            "success": True,
            "service": "visual_ai",
            "analyzer": {
                "anomaly_detection_threshold": analyzer.anomaly_detection_threshold,
                "color_shift_threshold": analyzer.color_shift_threshold,
                "layout_change_threshold": analyzer.layout_change_threshold,
            },
        }

    except Exception as exc:
        logger.error(f"Failed to get statistics: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/config")
def get_config():
    """Get visual AI configuration."""
    return {
        "success": True,
        "config": {
            "service": "visual_ai",
            "features": [
                "perceptual_similarity",
                "anomaly_detection",
                "color_shift_detection",
                "layout_change_detection",
                "element_visibility_detection",
                "smart_baseline_management",
                "analysis_reporting",
            ],
            "thresholds": {
                "anomaly_detection": 0.80,
                "color_shift": 30,
                "layout_change": 0.15,
            },
        },
    }
