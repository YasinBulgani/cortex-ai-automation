"""Central SQLAlchemy model imports for metadata registration.

Alembic autogenerate and any metadata-based tooling should import this module
instead of manually curating domain model imports in multiple places.
"""

from __future__ import annotations

from app.domains.api_testing import models as api_testing_models  # noqa: F401
from app.domains.coverup import models as coverup_models  # noqa: F401
from app.domains.notifications import models as notifications_models  # noqa: F401
from app.domains.tspm import models as tspm_models  # noqa: F401
from app.infra import models as core_models  # noqa: F401
