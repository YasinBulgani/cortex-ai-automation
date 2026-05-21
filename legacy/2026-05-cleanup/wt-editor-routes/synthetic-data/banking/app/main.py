from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.models.db_session import init_models

app = FastAPI(
    title="🏦 Banking Synthetic Data Generator",
    description="""
    **Bankacılık Sentetik Test Verisi Üretim API'si**

    Bu API, gerçek müşteri verisine dokunmadan tamamen sentetik ve gerçekçi bankacılık verileri üretir.

    ### Yetenekler:
    - 👤 Müşteri profili üretimi (Faker Türkçe yerelleştirme)
    - 🏦 Bağlı banka hesapları (Vadesiz / Vadeli)
    - 💳 Gerçekçi işlem geçmişi (maaş, market, fatura vb.)
    - ⚙️ YAML tabanlı kural motoru
    - 📊 Toplu (batch) veri üretimi

    ### Kullanım Senaryosu:
    > "1995 doğumlu, çalışan ve 2 adet bağlı banka hesabı olan kadın bir müşteri oluştur"
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1", tags=["Synthetic Data Generation"])

@app.on_event("startup")
async def on_startup():
    await init_models()

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "🏦 Banking Synthetic Data Generator API",
        "docs": "/docs",
        "health": "/api/v1/health"
    }
