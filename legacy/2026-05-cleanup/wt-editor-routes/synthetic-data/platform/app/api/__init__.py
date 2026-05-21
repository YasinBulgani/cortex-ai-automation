"""
API endpoint tanımları.

FastAPI router'ını ve tüm REST API endpointlerini içerir.
Router, app/main.py içinde include edilir.

Kullanım:
    from app.api import router
    app.include_router(router)
"""

from app.api.routes import router

__all__ = ["router"]
