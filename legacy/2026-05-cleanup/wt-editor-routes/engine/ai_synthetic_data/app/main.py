import sys
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.database import init_db
from app.config import get_settings
from app.api.routes import router as data_router

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("Database tables created successfully!")
    yield
    print("Shutting down...")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI destekli sentetik veri uretim platformu — KDE, Copula, CTGAN/TVAE, iliskisel uretim, gizlilik ve kalite metrikleri.",
    lifespan=lifespan,
)

app.include_router(data_router)

@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "TestwrightAI Synthetic Data Platform is running.",
        "version": settings.app_version,
        "docs": "/docs",
    }
