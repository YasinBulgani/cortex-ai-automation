"""Extended health/status endpoint domain — UX-F3-304.

Frontend "green/yellow/red dot" bileşeni bu modülün ``/api/v1/health/extended``
endpoint'inden veri okur. Mevcut ``/health`` ve ``/ready`` endpoint'leri bozulmaz;
yeni endpoint ek ayrıntı sağlar (tüm bağımlılıkların per-servis durumu + en
kötü durumdaki bileşen "overall" olarak raporlanır).
"""

from app.domains.health.service import get_extended_health  # noqa: F401
from app.domains.health.schemas import (  # noqa: F401
    ComponentStatus,
    ExtendedHealth,
    HealthLevel,
)
