"""
Engine routes entegrasyon testleri — tüm portlanmış route'ların temel çalışır durumda olduğunu doğrular.
"""
import importlib
import pytest

ENGINE_ROUTES = [
    "backend.app.engine.routes.regression",
    "backend.app.engine.routes.webhook",
    "backend.app.engine.routes.lifecycle",
    "backend.app.engine.routes.auth",
    "backend.app.engine.routes.runner",
    "backend.app.engine.routes.scheduler",
    "backend.app.engine.routes.manual",
    "backend.app.engine.routes.mobile",
    "backend.app.engine.routes.device_manager",
    "backend.app.engine.routes.analytics",
    "backend.app.engine.routes.recorder",
    "backend.app.engine.routes.wizard",
    "backend.app.engine.routes.editor",
    "backend.app.engine.routes.monkey",
    "backend.app.engine.routes.ai_generation",
    "backend.app.engine.routes.ai_healing",
    "backend.app.engine.routes.visual",
    "backend.app.engine.routes.datasim",
    "backend.app.engine.routes.banking",
    "backend.app.engine.routes.pipeline",
    "backend.app.engine.routes.reporting",
    "backend.app.engine.routes.metrics",
    "backend.app.engine.routes.project",
    "backend.app.engine.routes.llm_agent",
    "backend.app.engine.routes.datasim_banking",
    "backend.app.engine.routes.accessibility",
    "backend.app.engine.routes.locators",
    "backend.app.engine.routes.playback",
    "backend.app.engine.routes.ai_analysis",
    "backend.app.engine.routes.ai_intelligence",
    "backend.app.engine.routes.utility",
    "backend.app.engine.routes.feature",
    "backend.app.engine.routes.registry",
    "backend.app.engine.routes.magic_test",
    "backend.app.engine.routes.jira",
    "backend.app.engine.routes.tm",
    "backend.app.engine.routes.visual_ai",
    "backend.app.engine.routes.ai_routes",
    "backend.app.engine.routes.ai_openapi",
]

@pytest.mark.parametrize("module_path", ENGINE_ROUTES)
def test_engine_route_importable(module_path: str) -> None:
    """Her engine route modülü import edilebilir olmalı."""
    mod = importlib.import_module(module_path)
    assert hasattr(mod, "router"), f"{module_path} 'router' attribute'u yok"

@pytest.mark.parametrize("module_path", ENGINE_ROUTES)
def test_engine_route_has_endpoints(module_path: str) -> None:
    """Her engine route en az 1 endpoint içermeli."""
    mod = importlib.import_module(module_path)
    assert len(mod.router.routes) > 0, f"{module_path} hiç endpoint yok"
