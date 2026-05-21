"""
Engine routes — FastAPI port of legacy Flask engine.

Mount via:
    from app.engine.routes import register_engine_routers
    register_engine_routers(app)
"""

from fastapi import FastAPI

from .regression import router as regression_router

# Migration progress:
# ✅ regression       → port edildi
# ⏳ webhook          → TODO
# ⏳ lifecycle        → TODO
# ⏳ auth             → TODO (auth zaten /api/v1/auth altında consolidate edilebilir)
# ⏳ ai_generation    → TODO
# ⏳ manual           → TODO
# ⏳ datasim          → TODO
# ⏳ banking          → TODO
# ⏳ mobile           → TODO
# ⏳ device_manager   → TODO
# ⏳ monkey           → TODO
# ⏳ wizard           → TODO
# ⏳ editor           → TODO
# ⏳ runner           → TODO
# ⏳ datasim_banking  → TODO
# ⏳ ... (37 total)


def register_engine_routers(app: FastAPI) -> None:
    """Tüm engine route'larını main FastAPI app'e mount eder."""
    app.include_router(regression_router)
    # app.include_router(webhook_router)
    # ...
