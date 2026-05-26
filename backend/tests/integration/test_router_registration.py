"""router_registry üzerinden tüm domain router'larının gerçekten
FastAPI uygulamasına bağlandığını doğrulayan entegrasyon testleri.

Amaç: n8n, cicd gibi router'ların `main.py`'de unutulması durumunda CI'da
erken yakalamak. "Router tanımlı ama uygulamaya kayıtlı değil" regresyonunu
engeller.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "path_prefix",
    [
        # Core auth & config
        "/api/v1/auth",
        # Data & catalog
        "/api/v1/datasets",
        # Workflow & automation
        "/api/v1/n8n",
        "/api/v1/automation",
        "/api/v1/automation-suite",
        # CI/CD & jobs
        "/api/v1/cicd",
        "/api/v1/jobs",
        # AI & agents
        "/api/v1/ai",
        "/api/v1/ai/workflows",
        "/api/v1/agents",
        "/api/v1/agents/v2",
        "/api/v1/synthetic",
        "/api/v1/synthetic-platform",
        # Test management
        "/api/v1/tspm",
        "/api/v1/evals",
        "/api/v1/playwright-mcp",
        # DSL
        "/api/v1/dsl",
        # Knowledge & rules
        "/api/v1/rules",
        "/api/v1/kb",
        "/api/v1/prompts",
        # Quality & coverage
        "/api/v1/coverup",
        "/api/v1/quality",
        # Artifacts & git
        "/api/v1/artifacts",
        "/api/v1/git-fetch",
        "/api/v1/nexus-repo",
        # Products & commerce
        "/api/v1/products",
        "/api/v1/admin/billing",
        # Events & marketplace
        "/api/v1/events",
        "/api/v1/marketplace",
        # Visual & pilot
        "/api/v1/visual",
        "/api/v1/pilot",
        # Defects & ingestion
        "/api/v1/defects",
        "/api/v1/ingestion",
        # Compliance & privacy
        "/api/v1/compliance",
        "/api/v1/privacy",
        # Infrastructure & observability
        "/api/v1/audit",
        "/api/v1/notifications",
        "/api/v1/health",
        "/api/v1/accessibility",
        "/api/v1/onboarding",
        # Wave 12 routers
        "/api/v1/rbac",
        "/api/v1/navigation",
        "/api/v1/email",
        "/api/v1/pr-bot",
    ],
)
def test_critical_router_prefix_present(path_prefix: str) -> None:
    """Kritik router prefix'leri OpenAPI içinde bulunmalı — 404 regresyonu önler."""
    from app.main import app

    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    paths = list(spec.get("paths", {}).keys())
    assert any(p.startswith(path_prefix) for p in paths), (
        f"{path_prefix} prefix'i hiçbir endpoint'e sahip değil. "
        f"Bu genellikle app/core/router_registry.py içindeki _PREFIXED_ROUTERS "
        f"listesinden atlandığı anlamına gelir."
    )


def test_all_registered_routers_have_at_least_one_route() -> None:
    """Registry'deki her router en az bir endpoint tanımlamış olmalı."""
    from app.core.router_registry import _PREFIXED_ROUTERS, _UNPREFIXED_ROUTERS

    empty: list[str] = []
    for router in (*_PREFIXED_ROUTERS, *_UNPREFIXED_ROUTERS):
        if not router.routes:
            empty.append(router.prefix or "<no-prefix>")
    assert not empty, f"Boş router'lar: {empty}"
