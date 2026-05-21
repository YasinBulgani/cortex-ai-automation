"""
Pytest fixture'ları — SyntheticBankData test altyapısı.

Tüm test modüllerinde kullanılan ortak fixture'ları içerir:
  - Örnek DataFrame'ler (müşteri, hesap, işlem)
  - SchemaAnalyzer, ColumnClassifier, PIIDetector, RuleInferenceEngine örnekleri
  - Geçici dosya yardımcıları
  - FastAPI TestClient
  - Mock LLM Client
  - QA Engine yapılandırması
  - Mock Webhook sunucusu
  - Performans zamanlayıcı
  - Self-Learning Engine fixture'ları
"""

from __future__ import annotations

import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Generator

import numpy as np
import pandas as pd
import pytest

# ── Proje kökünü sys.path'e ekle ─────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


# ═══════════════════════════════════════════════════════════════════
# Örnek DataFrame Fixture'ları
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_customers_df() -> pd.DataFrame:
    """Örnek müşteri DataFrame'i (~10 satır, test amaçlı)."""
    return pd.DataFrame({
        "customer_id": [f"MUS{str(i).zfill(8)}" for i in range(1, 11)],
        "first_name": ["Ahmet", "Ayşe", "Mehmet", "Fatma", "Emre",
                        "Zeynep", "Burak", "Elif", "Serkan", "Merve"],
        "last_name": ["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin",
                       "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç"],
        "tckn": [
            "10000000146", "20000000084", "30000000124", "40000000062",
            "50000000108", "60000000046", "70000000086", "80000000024",
            "90000000064", "11000000088",
        ],
        "birth_date": [
            "1985-03-15", "1990-07-22", "1978-11-01", "1995-01-30",
            "1988-06-18", "1992-12-05", "1975-09-11", "2000-04-20",
            "1982-08-25", "1997-02-14",
        ],
        "gender": ["E", "K", "E", "K", "E", "K", "E", "K", "E", "K"],
        "email": [
            "ahmet.yilmaz@gmail.com", "ayse.kaya@hotmail.com",
            "mehmet.demir@gmail.com", "fatma.celik@yahoo.com",
            "emre.sahin@outlook.com", "zeynep.aydin@gmail.com",
            "burak.ozdemir@hotmail.com", "elif.arslan@gmail.com",
            "serkan.dogan@yahoo.com", "merve.kilic@outlook.com",
        ],
        "phone": [
            "+905301234567", "+905412345678", "+905523456789",
            "+905534567890", "+905345678901", "+905556789012",
            "+905467890123", "+905378901234", "+905489012345",
            "+905500123456",
        ],
        "city": ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya",
                  "İstanbul", "Ankara", "İzmir", "İstanbul", "Konya"],
        "segment": ["Bireysel", "Platinum", "KOBİ", "Bireysel", "VIP",
                      "Ticari", "Kurumsal", "Bireysel", "KOBİ", "Bireysel"],
        "credit_score": [750, 1450, 980, 620, 1680, 1100, 1350, 520, 890, 710],
    })


@pytest.fixture
def sample_accounts_df() -> pd.DataFrame:
    """Örnek hesap DataFrame'i (~15 satır, müşteri ilişkili)."""
    return pd.DataFrame({
        "account_id": [f"HSP{str(i).zfill(10)}" for i in range(1, 16)],
        "customer_id": [
            "MUS00000001", "MUS00000001", "MUS00000002", "MUS00000003",
            "MUS00000003", "MUS00000004", "MUS00000005", "MUS00000005",
            "MUS00000006", "MUS00000007", "MUS00000008", "MUS00000008",
            "MUS00000009", "MUS00000010", "MUS00000010",
        ],
        "iban": [
            "TR330006100519786457841326", "TR720010009640028532918463",
            "TR180004600149753812463920", "TR540001200387461590273841",
            "TR890032000562148937206485", "TR210046001823697450182734",
            "TR650062003746182059341627", "TR410064005198273604518293",
            "TR570099007634518290726183", "TR830103002871649305827194",
            "TR290001004956382710649528", "TR160004003287561894037265",
            "TR740006500712893546180274", "TR520010006439275180362941",
            "TR380015008521634097285316",
        ],
        "account_type": [
            "Vadesiz", "Vadeli", "Vadesiz", "Cari", "Yatırım",
            "Tasarruf", "Vadesiz", "Kredi", "Vadeli", "Vadesiz",
            "Tasarruf", "Vadeli", "Vadesiz", "Cari", "Vadesiz",
        ],
        "currency": [
            "TRY", "TRY", "TRY", "TRY", "USD",
            "TRY", "EUR", "TRY", "TRY", "TRY",
            "TRY", "USD", "TRY", "TRY", "EUR",
        ],
        "balance": [
            15230.50, 125000.00, 8750.25, 45620.80, 12500.00,
            32100.75, 5600.30, -45000.00, 250000.00, 1890.40,
            67500.00, 8900.00, 22340.15, 78900.60, 3200.00,
        ],
        "opening_date": [
            "2020-01-15", "2021-06-20", "2019-03-10", "2022-08-05",
            "2023-01-12", "2020-11-30", "2021-04-18", "2022-02-22",
            "2019-07-14", "2023-09-01", "2020-05-25", "2021-12-08",
            "2022-06-30", "2019-10-20", "2023-03-15",
        ],
        "status": [
            "Aktif", "Aktif", "Aktif", "Aktif", "Aktif",
            "Aktif", "Pasif", "Aktif", "Aktif", "Aktif",
            "Aktif", "Kapalı", "Aktif", "Aktif", "Dondurulmuş",
        ],
        "branch_code": [
            "1001", "1001", "2034", "3156", "3156",
            "4210", "5078", "5078", "6123", "7045",
            "8090", "8090", "1001", "2034", "2034",
        ],
        "interest_rate": [
            0.0, 42.50, 0.0, 0.0, 0.0,
            18.75, 0.0, 2.89, 38.00, 0.0,
            22.10, 35.00, 0.0, 0.0, 0.0,
        ],
    })


@pytest.fixture
def sample_transactions_df() -> pd.DataFrame:
    """Örnek işlem DataFrame'i (~20 satır, hesap ilişkili)."""
    return pd.DataFrame({
        "transaction_id": [f"TXN{str(i).zfill(10)}" for i in range(1, 21)],
        "account_id": [
            "HSP0000000001", "HSP0000000001", "HSP0000000002",
            "HSP0000000003", "HSP0000000004", "HSP0000000005",
            "HSP0000000006", "HSP0000000007", "HSP0000000008",
            "HSP0000000009", "HSP0000000010", "HSP0000000001",
            "HSP0000000003", "HSP0000000005", "HSP0000000007",
            "HSP0000000009", "HSP0000000002", "HSP0000000004",
            "HSP0000000006", "HSP0000000008",
        ],
        "transaction_date": [
            "2025-06-15", "2025-07-01", "2025-06-20", "2025-08-10",
            "2025-09-05", "2025-10-12", "2025-11-03", "2025-12-18",
            "2026-01-07", "2026-02-14", "2025-06-25", "2025-07-30",
            "2025-08-22", "2025-09-15", "2025-10-28", "2025-11-11",
            "2025-12-05", "2026-01-20", "2026-02-08", "2026-03-01",
        ],
        "transaction_type": [
            "Havale", "EFT", "Maaş", "POS Harcama", "Virman",
            "ATM Çekim", "Fatura", "Kredi Taksit", "Yatırım", "Havale",
            "EFT", "Maaş", "POS Harcama", "Fatura", "ATM Çekim",
            "Virman", "Yatırım", "Havale", "EFT", "Maaş",
        ],
        "amount": [
            2500.00, 15000.50, 28500.00, 1250.75, 5000.00,
            2000.00, 450.30, 3200.00, 10000.00, 7500.25,
            18000.00, 32000.00, 890.50, 1100.00, 1000.00,
            3500.00, 25000.00, 4200.00, 9800.75, 35000.00,
        ],
        "currency": [
            "TRY", "TRY", "TRY", "TRY", "TRY",
            "TRY", "TRY", "TRY", "USD", "TRY",
            "TRY", "TRY", "TRY", "TRY", "TRY",
            "TRY", "USD", "TRY", "TRY", "TRY",
        ],
        "description": [
            "Kira ödemesi", "Tedarikçi ödemesi", "Aylık maaş",
            "Market alışverişi", "Hesaplar arası transfer",
            "Nakit çekim", "Elektrik faturası", "Konut kredisi taksit",
            "Hisse alım", "Borç ödeme", "Personel maaşı",
            "Aylık maaş", "Online alışveriş", "İnternet faturası",
            "Hızlı para çekme", "Tasarruf hesabına", "Fon alım",
            "Aidat transferi", "Fatura ödemesi", "Prim ödemesi",
        ],
        "channel": [
            "Mobil", "Internet", "Şube", "POS", "Mobil",
            "ATM", "Internet", "Şube", "Internet", "Mobil",
            "Internet", "Şube", "POS", "Internet", "ATM",
            "Mobil", "Internet", "Mobil", "Internet", "Şube",
        ],
        "reference_no": [f"REF{str(i).zfill(8)}XY" for i in range(1, 21)],
        "status": [
            "Başarılı", "Başarılı", "Başarılı", "Başarılı", "Başarılı",
            "Başarılı", "Başarılı", "Başarılı", "Başarılı", "Başarılı",
            "Başarılı", "Başarılı", "Başarılı", "Beklemede", "Başarılı",
            "Başarılı", "Başarılı", "İptal", "Başarılı", "Başarılı",
        ],
    })


@pytest.fixture
def sample_customers_csv(sample_customers_df: pd.DataFrame, tmp_path: Path) -> Path:
    """Müşteri DataFrame'ini geçici CSV dosyasına yazar."""
    csv_path = tmp_path / "test_customers.csv"
    sample_customers_df.to_csv(csv_path, index=False, encoding="utf-8")
    return csv_path


@pytest.fixture
def sample_accounts_csv(sample_accounts_df: pd.DataFrame, tmp_path: Path) -> Path:
    """Hesap DataFrame'ini geçici CSV dosyasına yazar."""
    csv_path = tmp_path / "test_accounts.csv"
    sample_accounts_df.to_csv(csv_path, index=False, encoding="utf-8")
    return csv_path


@pytest.fixture
def sample_transactions_csv(sample_transactions_df: pd.DataFrame, tmp_path: Path) -> Path:
    """İşlem DataFrame'ini geçici CSV dosyasına yazar."""
    csv_path = tmp_path / "test_transactions.csv"
    sample_transactions_df.to_csv(csv_path, index=False, encoding="utf-8")
    return csv_path


# ═══════════════════════════════════════════════════════════════════
# Servis Fixture'ları
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def schema_analyzer():
    """SchemaAnalyzer örneği."""
    from app.services.schema_analyzer import SchemaAnalyzer
    return SchemaAnalyzer()


@pytest.fixture
def column_classifier():
    """ColumnClassifier örneği."""
    from app.services.column_classifier import ColumnClassifier
    return ColumnClassifier()


@pytest.fixture
def pii_detector():
    """PIIDetector örneği."""
    from app.services.pii_detector import PIIDetector
    return PIIDetector()


@pytest.fixture
def rule_engine():
    """RuleInferenceEngine örneği."""
    from app.services.rule_engine import RuleInferenceEngine
    return RuleInferenceEngine()


@pytest.fixture
def synthetic_generator():
    """SyntheticDataGenerator örneği."""
    from app.services.synthetic_generator import SyntheticDataGenerator
    return SyntheticDataGenerator()


@pytest.fixture
def scenario_generator():
    """ScenarioGenerator örneği."""
    from app.services.scenario_generator import ScenarioGenerator
    return ScenarioGenerator()


# ═══════════════════════════════════════════════════════════════════
# FastAPI TestClient Fixture
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def test_client():
    """FastAPI TestClient — veritabanı bağımlılığı mock'lanmış."""
    from unittest.mock import MagicMock, patch

    from fastapi.testclient import TestClient

    # Veritabanı bağlantısını mock'la
    mock_db = MagicMock()
    mock_db.__enter__ = MagicMock(return_value=mock_db)
    mock_db.__exit__ = MagicMock(return_value=False)

    with patch("app.models.database.get_db", return_value=mock_db):
        from app.main import app
        client = TestClient(app)
        yield client


@pytest.fixture
def real_data_dir() -> Path:
    """Gerçek örnek veri klasörü yolu."""
    return DATA_DIR


# ═══════════════════════════════════════════════════════════════════
# Mock LLM Client Fixture
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_llm_client():
    """
    Mock LLM istemcisi — OpenAI/Anthropic/Ollama API çağrılarını simüle eder.

    Tüm LLM bağımlılığı olan testlerde kullanılır. Gerçek API çağrısı yapmaz.
    Önceden tanımlı yanıtlar döndürür.
    """
    from unittest.mock import MagicMock, patch

    mock_client = MagicMock()

    # OpenAI mock yanıtı
    mock_openai_response = MagicMock()
    mock_openai_response.choices = [MagicMock()]
    mock_openai_response.choices[0].message.content = '{"senaryo": "bireysel", "musteri_sayisi": 1000}'
    mock_client.openai_response = mock_openai_response

    # Anthropic mock yanıtı
    mock_anthropic_response = MagicMock()
    mock_anthropic_response.content = [MagicMock()]
    mock_anthropic_response.content[0].text = '{"senaryo": "premium", "musteri_sayisi": 500}'
    mock_client.anthropic_response = mock_anthropic_response

    # Ollama mock yanıtı
    mock_ollama_response = MagicMock()
    mock_ollama_response.status_code = 200
    mock_ollama_response.json.return_value = {
        "response": '{"senaryo": "maas", "musteri_sayisi": 2000}'
    }
    mock_client.ollama_response = mock_ollama_response

    # Fallback NLP yanıtları
    mock_client.fallback_parse = {
        "senaryo": "bireysel",
        "musteri_sayisi": 1000,
        "min_bakiye": None,
        "max_bakiye": None,
        "kredi_skoru_min": None,
        "kredi_skoru_max": None,
        "segment": None,
        "yas_min": None,
        "yas_max": None,
        "ozel_kurallar": {},
    }

    return mock_client


# ═══════════════════════════════════════════════════════════════════
# QA Engine Yapılandırma Fixture'ları
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_qa_config() -> dict:
    """
    QA Engine test yapılandırması.

    Monkey tester, proje scaffolder ve test çalıştırıcı için
    varsayılan yapılandırma değerlerini sağlar.
    """
    return {
        "target_url": "http://localhost:8000",
        "browser": "chromium",
        "headless": True,
        "timeout": 30000,
        "monkey_test": {
            "click_count": 50,
            "form_fuzz_count": 20,
            "navigation_depth": 3,
            "rapid_action_count": 100,
            "timeout_per_action": 5000,
        },
        "scaffolder": {
            "project_name": "test_qa_project",
            "base_url": "http://localhost:8000",
            "browser": "chromium",
            "headless": True,
            "output_dir": "/tmp/qa_projects",
            "environments": ["dev", "staging", "prod"],
        },
        "test_runner": {
            "parallel": True,
            "max_workers": 4,
            "retry_count": 2,
            "screenshot_on_failure": True,
        },
    }


@pytest.fixture
def mock_playwright_page():
    """
    Mock Playwright Page nesnesi.

    Asenkron tarayıcı işlemlerini simüle eder. Gerçek tarayıcı
    başlatmadan QA Engine testleri için kullanılır.
    """
    from unittest.mock import AsyncMock, MagicMock

    page = AsyncMock()
    page.url = "http://localhost:8000"
    page.title = AsyncMock(return_value="SyntheticBankData — Ana Sayfa")

    # Sayfa analizi mock'ları
    page.query_selector_all = AsyncMock(return_value=[])
    page.evaluate = AsyncMock(return_value={
        "forms": 2,
        "links": 15,
        "inputs": 8,
        "buttons": 5,
    })
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
    page.content = AsyncMock(return_value="<html><body>Test</body></html>")
    page.close = AsyncMock()

    return page


# ═══════════════════════════════════════════════════════════════════
# Mock Webhook Sunucusu Fixture
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_webhook_server():
    """
    Mock webhook sunucusu.

    Webhook teslim testleri için sahte HTTP endpoint simüle eder.
    Gelen istekleri kaydeder ve yapılandırılabilir yanıtlar döndürür.
    """
    from unittest.mock import MagicMock

    server = MagicMock()
    server.url = "https://webhook.test/callback"
    server.secret = "test_webhook_secret_key_123"
    server.received_payloads = []
    server.response_status = 200
    server.response_delay = 0.0
    server.call_count = 0

    def receive_webhook(payload, headers=None):
        """Gelen webhook'u kaydet."""
        server.received_payloads.append({
            "payload": payload,
            "headers": headers or {},
        })
        server.call_count += 1
        return MagicMock(status_code=server.response_status)

    server.receive = receive_webhook
    return server


# ═══════════════════════════════════════════════════════════════════
# Performans Zamanlayıcı Fixture
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def performance_timer():
    """
    Performans ölçüm yardımcısı.

    Test fonksiyonlarının yürütme süresini ve bellek kullanımını
    ölçmek için context manager sağlar.
    """
    import time
    import tracemalloc

    class PerformanceTimer:
        """Performans ölçüm sınıfı."""

        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.elapsed_seconds = 0.0
            self.peak_memory_mb = 0.0
            self._tracemalloc_started = False

        def start(self):
            """Zamanlayıcıyı başlat."""
            self.start_time = time.time()
            try:
                tracemalloc.start()
                self._tracemalloc_started = True
            except RuntimeError:
                self._tracemalloc_started = False
            return self

        def stop(self):
            """Zamanlayıcıyı durdur ve metrikleri hesapla."""
            self.end_time = time.time()
            self.elapsed_seconds = self.end_time - self.start_time

            if self._tracemalloc_started:
                _, peak = tracemalloc.get_traced_memory()
                self.peak_memory_mb = peak / (1024 * 1024)
                tracemalloc.stop()
                self._tracemalloc_started = False

            return self

        def assert_under(self, max_seconds: float, message: str = ""):
            """Sürenin belirtilen limitin altında olduğunu doğrula."""
            assert self.elapsed_seconds < max_seconds, (
                f"Performans limiti aşıldı: {self.elapsed_seconds:.2f}s > "
                f"{max_seconds}s. {message}"
            )

        def assert_memory_under(self, max_mb: float, message: str = ""):
            """Bellek kullanımının limitin altında olduğunu doğrula."""
            assert self.peak_memory_mb < max_mb, (
                f"Bellek limiti aşıldı: {self.peak_memory_mb:.2f}MB > "
                f"{max_mb}MB. {message}"
            )

    return PerformanceTimer()


# ═══════════════════════════════════════════════════════════════════
# Self-Learning Engine Fixture'ları
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_db_session():
    """
    Mock veritabanı oturumu — tüm DB bağımlı testlerde kullanılır.

    SQLAlchemy Session'ı simüle eder. add, commit, query, flush
    işlemlerini mock'lar.
    """
    from unittest.mock import MagicMock

    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.flush = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.refresh = MagicMock()

    # Query mock — zincirleme çağrılar için
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.filter_by.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.all.return_value = []
    mock_query.first.return_value = None
    mock_query.count.return_value = 0
    mock_query.scalar.return_value = 0
    session.query.return_value = mock_query

    return session


@pytest.fixture
def learning_engine():
    """
    SelfLearningEngine örneği — öğrenme testleri için.

    Veritabanı bağımlılığı olmadan çalışabilen bir örnek oluşturur.
    """
    from app.services.self_learning import SelfLearningEngine
    return SelfLearningEngine()


@pytest.fixture
def sample_generation_params() -> dict:
    """Örnek üretim parametreleri — öğrenme testleri için."""
    return {
        "scenario_type": "bireysel",
        "row_count": 1000,
        "column_count": 10,
        "batch_size": 500,
        "columns": {
            "customer_id": {"generator": "sequential_id", "prefix": "MUS"},
            "first_name": {"generator": "turkish_first_name"},
            "last_name": {"generator": "turkish_last_name"},
            "tckn": {"generator": "tckn"},
            "email": {"generator": "email"},
            "phone": {"generator": "turkish_phone"},
            "city": {"generator": "turkish_city"},
            "balance": {"generator": "float_range", "min": 0, "max": 1000000},
            "credit_score": {"generator": "int_range", "min": 300, "max": 1900},
            "segment": {"generator": "enum", "values": ["Bireysel", "Premium", "KOBİ"]},
        },
        "rules": [
            {"column": "balance", "type": "range", "min": 0, "max": 1000000},
            {"column": "credit_score", "type": "range", "min": 300, "max": 1900},
        ],
    }


@pytest.fixture
def sample_quality_scores() -> dict:
    """Örnek kalite skorları — optimizasyon testleri için."""
    return {
        "overall": 85.5,
        "completeness": 98.0,
        "uniqueness": 72.3,
        "consistency": 91.0,
        "accuracy": 80.5,
    }


# ═══════════════════════════════════════════════════════════════════
# LLM Service Fixture'ları
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def llm_service_fallback():
    """Fallback modunda LLM servisi — regex/keyword tabanlı."""
    from app.services.llm_service import LLMService
    return LLMService(provider="fallback")
