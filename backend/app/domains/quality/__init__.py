"""Quality metrics domain — UX-F2-201 dashboard backend kaynağı.

Frontend "Platform Sağlığı" widget'ı (info sayfası / admin dashboard)
bu modülün ``/api/v1/quality/metrics`` endpoint'inden veri okur.
"""

from app.domains.quality.service import (  # noqa: F401
    EvalSnapshot,
    QualityMetrics,
    get_quality_metrics,
)
