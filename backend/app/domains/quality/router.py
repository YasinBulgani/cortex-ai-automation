"""Quality metrics endpoint.

Yol: ``GET /api/v1/quality/metrics``
Kullanıcı: dashboard "Platform Sağlığı" widget'ı (UX-F2-201).
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.domains.quality.service import QualityMetrics, get_quality_metrics

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get(
    "/metrics",
    response_model=QualityMetrics,
    summary="Dashboard için platform kalite metrikleri",
)
def metrics(
    history_limit: int = Query(10, ge=1, le=50, description="Geçmiş rapor sayısı"),
) -> QualityMetrics:
    """Latest eval raporu + son N koşumun özeti.

    - ``latest_eval.available=false`` → henüz bir koşum yok ya da dosya
      erişilemiyor. Frontend "Henüz veri yok" durumunu render etmeli.
    - ``latest_eval.mapping_accuracy_pct`` gibi alanlar None olabilir
      (parse edilememişse). Frontend "—" gösterebilir.
    """
    return get_quality_metrics(history_limit=history_limit)
