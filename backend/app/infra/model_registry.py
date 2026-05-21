"""Central SQLAlchemy model imports for metadata registration.

Alembic autogenerate and any metadata-based tooling should import this module
instead of manually curating domain model imports in multiple places.
"""

from __future__ import annotations

from app.domains.api_testing import models as api_testing_models  # noqa: F401
from app.domains.billing import models as billing_models  # noqa: F401
from app.domains.coverup import models as coverup_models  # noqa: F401
from app.domains.notifications import models as notifications_models  # noqa: F401
from app.domains.tspm import models as tspm_models  # noqa: F401
from app.infra import models as core_models  # noqa: F401

# DDD bounded contexts
from app.contexts.identity.infrastructure.sql_repository import UserRow  # noqa: F401
from app.contexts.projects.infrastructure.sql_repository import ProjectRow  # noqa: F401
from app.contexts.scenarios.infrastructure.sql_repository import ScenarioRow  # noqa: F401
