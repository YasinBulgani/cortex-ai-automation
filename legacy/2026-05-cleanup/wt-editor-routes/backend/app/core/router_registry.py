"""Central router registration for the FastAPI app."""

from __future__ import annotations

from fastapi import FastAPI

from app.domains.agents.router import router as agents_router
from app.domains.ai.router import router as ai_router
from app.domains.ai_synthetic_data.router import router as synthetic_router
from app.domains.api_testing.router import router as api_testing_router
from app.domains.artifacts.router import router as artifacts_router
from app.domains.audit.router import router as audit_router
from app.domains.auth.router import router as auth_router
from app.domains.automation.router import router as automation_router
from app.domains.catalog.router import router as catalog_router
from app.domains.cicd.router import router as cicd_router
from app.domains.coverup.router import router as coverup_router
from app.domains.dsl.router import router as dsl_router
from app.domains.dsl.edit_router import router as dsl_edit_router
from app.domains.automation_suite.router import router as automation_suite_router
from app.domains.jobs.router import router as jobs_router
from app.domains.n8n.router import router as n8n_router
from app.domains.notifications.router import router as notifications_router
from app.domains.playwright_mcp.router import router as playwright_mcp_router
from app.domains.rules.router import router as rules_router
from app.domains.tspm.router import router as tspm_router


def register_api_routers(app: FastAPI) -> None:
    """Attach all domain routers using a single composition point."""
    prefixed_routers = [
        auth_router,
        catalog_router,
        rules_router,
        jobs_router,
        artifacts_router,
        tspm_router,
        notifications_router,
        automation_router,
        cicd_router,
        audit_router,
        ai_router,
        agents_router,
        synthetic_router,
        n8n_router,
        playwright_mcp_router,
        coverup_router,
        dsl_router,
        dsl_edit_router,
        automation_suite_router,
    ]

    for router in prefixed_routers:
        app.include_router(router, prefix="/api/v1")

    app.include_router(api_testing_router)
