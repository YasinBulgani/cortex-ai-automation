"""FastAPI uygulaması için merkezi router kaydı.

Tüm domain router'ları burada tek noktadan toplanır. `main.py` yalnızca
`register_api_routers(app)` çağırmalıdır; router listesini başka bir yerde
tekrar tanımlamak kayıt kaymasına yol açar.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from fastapi import APIRouter, FastAPI

from app.domains.accessibility.router import router as accessibility_router
from app.domains.agents.router import router as agents_router
from app.domains.agents.v2.router import router as agents_v2_router
from app.domains.ai.router import router as ai_router
from app.domains.ai.workflows_router import router as ai_workflows_router
from app.domains.health.router import router as health_router
from app.domains.ai_synthetic_data.router import router as synthetic_router
from app.domains.ai_synthetic_data.platform_router import router as synthetic_platform_router
from app.domains.api_testing.router import router as api_testing_router
from app.domains.artifacts.router import router as artifacts_router
from app.domains.audit.router import router as audit_router
from app.domains.auth.router import router as auth_router
from app.domains.billing.router import router as billing_router
from app.domains.automation.router import router as automation_router
from app.domains.automation_suite.router import router as automation_suite_router
from app.domains.catalog.router import router as catalog_router
from app.domains.cicd.router import router as cicd_router
from app.domains.coverup.router import router as coverup_router
from app.domains.dsl.edit_router import router as dsl_edit_router
from app.domains.dsl.router import router as dsl_router
from app.domains.evals.router import router as evals_router
from app.domains.jobs.router import router as jobs_router
from app.domains.n8n.router import router as n8n_router
from app.domains.notifications.router import router as notifications_router
from app.domains.onboarding.router import router as onboarding_router
from app.domains.playwright_mcp.router import router as playwright_mcp_router
from app.domains.privacy.router import router as privacy_router
from app.domains.prompts.router import router as prompts_router
from app.domains.git_fetch.router import router as git_fetch_router
from app.domains.quality.router import router as quality_router
from app.domains.rules.router import router as rules_router
from app.domains.test_management.router import router as test_management_router
from app.domains.tspm.router import router as tspm_router
from app.domains.nexus_repo.router import router as nexus_repo_router
from app.domains.products.router import router as products_router

# qa/ git-native test management — yeni domain (PR 41)
try:
    from app.domains.qa.router import router as qa_router  # type: ignore
    _HAS_QA_ROUTER = True
except ImportError:
    qa_router = None  # type: ignore[assignment]
    _HAS_QA_ROUTER = False

# DDD bounded context routers (new architecture)
try:
    from app.contexts.projects.api import router as contexts_projects_router
    from app.contexts.scenarios.api import router as contexts_scenarios_router
    _HAS_CONTEXTS_ROUTERS = True
except ImportError:
    contexts_projects_router = None  # type: ignore[assignment]
    contexts_scenarios_router = None  # type: ignore[assignment]
    _HAS_CONTEXTS_ROUTERS = False

logger = logging.getLogger(__name__)

# Mobile modülü commit 77f5303'te geldi; kaynak dosyaları git'e add edilmiş
# olmayabilir. Defansif import — modül yoksa endpoint'ler kapalı, backend
# yine de ayağa kalkar.
try:
    from app.domains.mobile.router import router as mobile_router  # type: ignore
    _HAS_MOBILE_ROUTER = True
except ImportError:
    mobile_router = None  # type: ignore[assignment]
    _HAS_MOBILE_ROUTER = False

_PREFIXED_ROUTERS = [
    auth_router,
    catalog_router,
    rules_router,
    jobs_router,
    artifacts_router,
    test_management_router,
    tspm_router,
    notifications_router,
    automation_router,
    cicd_router,
    audit_router,
    billing_router,
    ai_router,
    ai_workflows_router,
    agents_router,
    agents_v2_router,
    synthetic_router,
    synthetic_platform_router,
    n8n_router,
    playwright_mcp_router,
    coverup_router,
    dsl_router,
    dsl_edit_router,
    evals_router,
    automation_suite_router,
    git_fetch_router,
    privacy_router,
    prompts_router,
    products_router,
    health_router,
    accessibility_router,
    quality_router,
    onboarding_router,
    nexus_repo_router,
]

if _HAS_QA_ROUTER and qa_router is not None:
    _PREFIXED_ROUTERS.append(qa_router)


# Routers that carry their own full path prefix (e.g. /api/v1/api-testing/…)
_UNPREFIXED_ROUTERS = [
    api_testing_router,
    health_router,
    onboarding_router,
    quality_router,
    accessibility_router,
    audit_router,
    artifacts_router,
    nexus_repo_router,
]


def register_api_routers(app: FastAPI) -> None:
    """Attach all domain routers using a single composition point.

    Mobile router opsiyoneldir; modül eksikse sessizce atlanır ve bir
    uyarı loglanır (bkz. defansif import bloğu yukarıda).
    """
    for router in _PREFIXED_ROUTERS:
        app.include_router(router, prefix="/api/v1")

    # api_testing ayrı prefix: ekibin kararıyla /api/v1 dışında
    app.include_router(api_testing_router)

    if _HAS_MOBILE_ROUTER and mobile_router is not None:
        app.include_router(mobile_router, prefix="/api/v1")
    else:
        logger.warning(
            "mobile_router yüklenemedi (app/domains/mobile/ modülü eksik); "
            "Mobile endpoint'leri devre dışı. Modül kaynak dosyalarının git "
            "add edildiğinden emin olun."
        )

    # DDD bounded context routers
    if _HAS_CONTEXTS_ROUTERS:
        app.include_router(contexts_projects_router, prefix="/api/v1")
        app.include_router(contexts_scenarios_router, prefix="/api/v1")
    else:
        logger.warning("DDD context router'ları yüklenemedi; endpoint'ler devre dışı.")
