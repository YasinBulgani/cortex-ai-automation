# Engine routes — toplam 37 FastAPI router (Flask engine'den port edildi)
"""
Engine routes — FastAPI port of legacy Flask engine.

Mount via:
    from app.engine.routes import register_engine_routers
    register_engine_routers(app)
"""

from fastapi import FastAPI

from .ai_generation import router as ai_generation_router
from .ai_healing import router as ai_healing_router
from .auth import router as auth_router
from .lifecycle import router as lifecycle_router
from .manual import router as manual_router
from .regression import router as regression_router
from .runner import router as runner_router
from .scheduler import router as scheduler_router
from .visual import router as visual_router
from .webhook import router as webhook_router

try:
    from .mobile import router as mobile_router
    _HAS_MOBILE = True
except Exception:
    from fastapi import APIRouter as _APIRouter
    mobile_router = _APIRouter()
    _HAS_MOBILE = False
from .accessibility import router as accessibility_router
from .ai_analysis import router as ai_analysis_router
from .ai_intelligence import router as ai_intelligence_router
from .ai_openapi import router as ai_openapi_router
from .ai_routes import router as ai_routes_router
from .analytics import router as analytics_router
from .banking import router as banking_router
from .datasim import router as datasim_router
from .datasim_banking import router as datasim_banking_router
from .device_manager import router as device_manager_router
from .editor import router as editor_router
from .feature import router as feature_router
from .jira import router as jira_router
from .llm_agent import router as llm_agent_router
from .locators import router as locators_router
from .magic_test import router as magic_test_router
from .metrics import router as metrics_router
from .monkey import router as monkey_router
from .pipeline import router as pipeline_router
from .playback import router as playback_router
from .project import router as project_router
from .recorder import router as recorder_router
from .registry import router as registry_router
from .reporting import router as reporting_router
from .tm import router as tm_router
from .utility import router as utility_router
from .visual_ai import router as visual_ai_router
from .wizard import router as wizard_router

# Migration progress:
# ✅ regression            → port edildi
# ✅ ai_generation         → port edildi
# ✅ ai_healing            → port edildi
# ✅ visual                → port edildi
# ✅ webhook               → port edildi
# ✅ lifecycle             → port edildi
# ✅ auth                  → port edildi (in-memory store; Wave-25'te JWT/OAuth'a taşınacak)
# ✅ runner                → port edildi
# ✅ scheduler             → port edildi
# ✅ manual                → port edildi
# ✅ mobile                → port edildi
# ✅ device_manager        → port edildi
# ✅ analytics             → port edildi
# ✅ datasim               → port edildi
# ✅ banking               → port edildi
# ✅ pipeline              → port edildi
# ✅ recorder              → port edildi
# ✅ wizard                → port edildi
# ✅ editor                → port edildi
# ✅ monkey                → port edildi
# ✅ reporting             → port edildi
# ✅ metrics               → port edildi
# ✅ project               → port edildi
# ✅ jira                  → port edildi
# ✅ tm                    → port edildi
# ✅ visual_ai             → port edildi
# ✅ llm_agent             → port edildi (Playwright worker pool, 13 endpoint)
# ✅ datasim_banking       → port edildi (BDDK/KVKK veri üretimi, 19 endpoint)
# ✅ accessibility         → port edildi
# ✅ ai_analysis           → port edildi
# ✅ ai_intelligence       → port edildi
# ✅ feature               → port edildi
# ✅ locators              → port edildi
# ✅ magic_test            → port edildi
# ✅ playback              → port edildi
# ✅ registry              → port edildi
# ✅ utility               → port edildi
# ✅ ai_routes             → port edildi (23 endpoint: generate, analyze, heal, nl-test, impact vb.)
# ✅ ai_openapi            → port edildi (GET /api/ai/openapi.json)
# (39 routes total, 39 done)


def register_engine_routers(app: FastAPI) -> None:
    """Tüm engine route'larını main FastAPI app'e mount eder."""
    app.include_router(regression_router)
    app.include_router(ai_generation_router)
    app.include_router(ai_healing_router)
    app.include_router(visual_router)
    app.include_router(webhook_router)
    app.include_router(lifecycle_router)
    app.include_router(auth_router)
    app.include_router(runner_router)
    app.include_router(scheduler_router)
    app.include_router(manual_router)
    app.include_router(mobile_router)
    app.include_router(device_manager_router)
    app.include_router(analytics_router)
    app.include_router(datasim_router)
    app.include_router(banking_router)
    app.include_router(pipeline_router)
    app.include_router(recorder_router)
    app.include_router(wizard_router)
    app.include_router(editor_router)
    app.include_router(monkey_router)
    app.include_router(reporting_router)
    app.include_router(metrics_router)
    app.include_router(project_router)
    app.include_router(jira_router)
    app.include_router(tm_router)
    app.include_router(visual_ai_router)
    app.include_router(llm_agent_router)
    app.include_router(datasim_banking_router)
    app.include_router(accessibility_router)
    app.include_router(ai_analysis_router)
    app.include_router(ai_intelligence_router)
    app.include_router(feature_router)
    app.include_router(locators_router)
    app.include_router(magic_test_router)
    app.include_router(playback_router)
    app.include_router(registry_router)
    app.include_router(utility_router)
    app.include_router(ai_routes_router)
    app.include_router(ai_openapi_router)
