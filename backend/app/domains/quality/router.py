"""Quality metrics endpoint.

Yol: ``GET /api/v1/quality/metrics``
Kullanıcı: dashboard "Platform Sağlığı" widget'ı (UX-F2-201).
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.domains.quality.service import (
    QualityMetrics,
    get_quality_metrics,
    get_quality_score,
)
from app.infra.database import get_db
from app.infra.models import User

CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get(
    "/metrics",
    response_model=QualityMetrics,
    summary="Dashboard için platform kalite metrikleri",
)
def metrics(
    user: Annotated[User, Depends(get_current_user)],
    history_limit: int = Query(10, ge=1, le=50, description="Geçmiş rapor sayısı"),
) -> QualityMetrics:
    """Latest eval raporu + son N koşumun özeti.

    - ``latest_eval.available=false`` → henüz bir koşum yok ya da dosya
      erişilemiyor. Frontend "Henüz veri yok" durumunu render etmeli.
    - ``latest_eval.mapping_accuracy_pct`` gibi alanlar None olabilir
      (parse edilememişse). Frontend "—" gösterebilir.
    """
    return get_quality_metrics(history_limit=history_limit)


@router.get(
    "/score",
    summary="Genel kalite skoru — project_id opsiyonel",
)
def get_quality_score_endpoint(
    user: Annotated[User, Depends(get_current_user)],
    db: DB,
    project_id: Optional[str] = Query(default=None, description="Proje ID (opsiyonel, global skor için boş bırakın)"),
) -> dict:
    """Genel kalite skoru — gerçek test_management verilerinden hesaplanır.

    Döndürdüğü metrikler (``available=False`` ise hepsi ``None``):
    - overall_score: 0-100 arası genel skor (kapsama+pass-rate+otomasyon ağırlıklı)
    - test_coverage: Gereksinim kapsama yüzdesi
    - defect_density: Kritik defect / TC oranı
    - test_effectiveness: Pass-rate yüzdesi
    - automation_rate: Otomatik TC oranı
    - trend: improving | stable | declining | unknown
    - available: Gerçek veri bulundu mu

    project_id verilmezse veya proje yoksa ``available=False`` döner.
    """
    return get_quality_score(db, project_id)
