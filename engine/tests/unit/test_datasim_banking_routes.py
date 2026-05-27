"""
tests/unit/test_datasim_banking_routes.py
==========================================
Banking DataSim blueprint (/api/banking/*) icin birim testler.
BANKING_AVAILABLE=True/False her iki yol da test edilir.
Dis bagimliliklar (banking.*) sys.modules stub'lari ile izole edilir.
"""
from __future__ import annotations

import importlib
import io
import json
import sys
import types
import pytest


# ── Stubs ─────────────────────────────────────────────────────────────────────

def _make_banking_stubs():
    """banking.* modüllerini sahte nesnelerle sys.modules'a ekler."""
    root_mod = types.ModuleType("banking")
    sys.modules.setdefault("banking", root_mod)

    # --- generators ---
    gen_mod = types.ModuleType("banking.generators")
    sys.modules.setdefault("banking.generators", gen_mod)

    identity_mod = types.ModuleType("banking.generators.identity")
    identity_mod.generate_tc_kimlik = lambda: "12345678901"
    identity_mod.validate_tc_kimlik = lambda tc: True
    identity_mod.generate_vkn = lambda: "1234567890"
    identity_mod.validate_vkn = lambda vkn: True
    identity_mod.generate_tc_kimlik_batch = lambda count, seed=None: ["12345678901"] * count
    sys.modules["banking.generators.identity"] = identity_mod

    account_mod = types.ModuleType("banking.generators.account")
    account_mod.generate_tr_iban = lambda bank_code=None: "TR330006100519786457841326"
    account_mod.validate_tr_iban = lambda iban: True
    account_mod.generate_swift = lambda bank_code=None: "AKBKTRIS"
    account_mod.get_bank_list = lambda: [
        {"code": "0006", "name": "Akbank", "swift": "AKBKTRIS"},
        {"code": "0010", "name": "Ziraat Bankasi", "swift": "TCZBTR2A"},
    ]
    account_mod.TR_BANK_CODES = {"0006": "Akbank", "0010": "Ziraat Bankasi"}
    sys.modules["banking.generators.account"] = account_mod

    card_mod = types.ModuleType("banking.generators.card")
    card_mod.generate_card_number = lambda card_type="troy": "9792123456789012"
    card_mod.luhn_check = lambda no: True
    card_mod.generate_cvv = lambda card_type="troy": "123"
    card_mod.generate_card_expiry = lambda: "12/28"
    card_mod.mask_card_number = lambda no: "979212******9012"
    sys.modules["banking.generators.card"] = card_mod

    transaction_mod = types.ModuleType("banking.generators.transaction")
    transaction_mod.generate_eft_reference = lambda: "EFT202401010001"
    transaction_mod.generate_fast_reference = lambda: "FAST202401010001"
    transaction_mod.generate_doviz_kuru = lambda currency="USD": 32.50
    transaction_mod.generate_transaction_date = lambda: "2024-01-01T10:00:00"
    transaction_mod.generate_cek_numarasi = lambda: "CHK0000001"
    transaction_mod.generate_aciklama = lambda turu=None: "Test islemi"
    transaction_mod.generate_merchant = lambda: "Test Magaza"
    transaction_mod.DOVIZ_KURLAR = {"USD": 32.50, "EUR": 35.00}
    sys.modules["banking.generators.transaction"] = transaction_mod

    credit_mod = types.ModuleType("banking.generators.credit")
    credit_mod.generate_faiz_orani = lambda kredi_turu="ihtiyac_kredisi": 2.5
    credit_mod.generate_kredi_limiti = lambda gelir, segment, yas, risk: 50000.0
    credit_mod.generate_risk_skoru = lambda segment="standard": 650
    credit_mod.classify_segment = lambda gelir: "standard"
    credit_mod.generate_aylik_gelir = lambda: 15000.0
    credit_mod.SEGMENT_KURALLAR = {"standard": {}, "premium": {}}
    credit_mod.FAIZ_SPREAD = 2.0
    credit_mod.TCMB_POLITIKA_FAIZ = 40.0
    sys.modules["banking.generators.credit"] = credit_mod

    # --- factories ---
    factories_mod = types.ModuleType("banking.factories")
    sys.modules.setdefault("banking.factories", factories_mod)

    bf_mod = types.ModuleType("banking.factories.banking_factories")
    _FACTORY_TYPES = ["musteri", "hesap", "islem", "kredi", "kart"]
    bf_mod.FACTORY_MAP = {t: None for t in _FACTORY_TYPES}
    bf_mod.generate_banking_data = lambda entity_type, count, seed=None: [
        {"id": i, "entity": entity_type, "value": "stub"} for i in range(count)
    ]
    bf_mod.generate_relational_dataset = lambda **kwargs: {
        "meta": {"musteri_count": kwargs.get("musteri_count", 1)},
        "musteri": [{"musteri_id": "M001"}],
        "hesap": [{"hesap_id": "H001", "musteri_id": "M001"}],
        "islem": [{"islem_id": "I001", "hesap_id": "H001"}],
        "kredi": [{"kredi_id": "K001", "musteri_id": "M001"}],
    }
    sys.modules["banking.factories.banking_factories"] = bf_mod

    return bf_mod.FACTORY_MAP


def _clear_banking_stubs():
    """banking stub modüllerini sys.modules'dan temizle."""
    keys_to_remove = [k for k in sys.modules if k.startswith("banking")]
    for k in keys_to_remove:
        sys.modules.pop(k, None)


# ── Fixture — banking mevcut ──────────────────────────────────────────────────

@pytest.fixture
def banking_client(monkeypatch):
    """Banking modülleri mevcut simüle edilmiş Flask istemcisi."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")

    _clear_banking_stubs()
    _make_banking_stubs()

    # Rota modülünü yeniden yükle
    for mod_name in list(sys.modules.keys()):
        if "datasim_banking" in mod_name or mod_name == "app":
            sys.modules.pop(mod_name, None)

    monkeypatch.setattr("core.db.get_run_stats", lambda: {"total": 0, "passed": 0, "failed": 0}, raising=False)
    monkeypatch.setattr("core.db.get_run_history", lambda: [], raising=False)
    monkeypatch.setattr("core.db.get_comprehensive_reports", lambda: [], raising=False)

    app_module = importlib.import_module("app")
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        yield client

    _clear_banking_stubs()


# ── Fixture — banking mevcut degil ───────────────────────────────────────────

@pytest.fixture
def banking_client_unavailable(monkeypatch):
    """Banking modülleri yüklü degil simüle edilmiş Flask istemcisi."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")

    _clear_banking_stubs()

    # import hatasi tetikleyelim
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name.startswith("banking"):
            raise ImportError(f"Banking module not available: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    for mod_name in list(sys.modules.keys()):
        if "datasim_banking" in mod_name or mod_name == "app":
            sys.modules.pop(mod_name, None)

    monkeypatch.setattr("core.db.get_run_stats", lambda: {"total": 0, "passed": 0, "failed": 0}, raising=False)
    monkeypatch.setattr("core.db.get_run_history", lambda: [], raising=False)
    monkeypatch.setattr("core.db.get_comprehensive_reports", lambda: [], raising=False)

    try:
        app_module = importlib.import_module("app")
        app_module.app.config["TESTING"] = True
        with app_module.app.test_client() as client:
            yield client
    except Exception:
        # Modül yuklenemezse basit bir stub client ver
        yield None

    _clear_banking_stubs()


# ══════════════════════════════════════════════════════════════════════════════
# INFO endpoint
# ══════════════════════════════════════════════════════════════════════════════

def test_banking_info_returns_200(banking_client):
    """/api/banking/info 200 dönmeli."""
    response = banking_client.get("/api/banking/info")
    assert response.status_code == 200


def test_banking_info_returns_json(banking_client):
    """/api/banking/info JSON yaniti olmali."""
    data = banking_client.get("/api/banking/info").get_json()
    assert data is not None


def test_banking_info_contains_ok(banking_client):
    """/api/banking/info yaniti ok:True icermeli."""
    data = banking_client.get("/api/banking/info").get_json()
    assert data.get("ok") is True


def test_banking_info_contains_module_name(banking_client):
    """/api/banking/info modül adini icermeli."""
    data = banking_client.get("/api/banking/info").get_json()
    assert "module" in data


def test_banking_info_contains_endpoints(banking_client):
    """/api/banking/info endpoint listesini icermeli."""
    data = banking_client.get("/api/banking/info").get_json()
    assert "endpoints" in data
    assert isinstance(data["endpoints"], dict)


def test_banking_info_bddk_compliant(banking_client):
    """/api/banking/info bddk_compliant:True icermeli."""
    data = banking_client.get("/api/banking/info").get_json()
    assert data.get("bddk_compliant") is True


# ══════════════════════════════════════════════════════════════════════════════
# BANKS endpoint
# ══════════════════════════════════════════════════════════════════════════════

def test_banking_banks_returns_200(banking_client):
    """/api/banking/banks 200 dönmeli."""
    response = banking_client.get("/api/banking/banks")
    assert response.status_code == 200


def test_banking_banks_contains_banks_list(banking_client):
    """/api/banking/banks banka listesi icermeli."""
    data = banking_client.get("/api/banking/banks").get_json()
    assert "banks" in data
    assert isinstance(data["banks"], list)


def test_banking_banks_has_count(banking_client):
    """/api/banking/banks count bilgisi icermeli."""
    data = banking_client.get("/api/banking/banks").get_json()
    assert "count" in data
    assert data["count"] > 0


# ══════════════════════════════════════════════════════════════════════════════
# TC KIMLIK generation
# ══════════════════════════════════════════════════════════════════════════════

def test_tc_kimlik_generation_returns_200(banking_client):
    """/api/banking/tc-kimlik POST 200 dönmeli."""
    response = banking_client.post(
        "/api/banking/tc-kimlik",
        json={"count": 3},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_tc_kimlik_generation_returns_data(banking_client):
    """/api/banking/tc-kimlik verisi dönmeli."""
    data = banking_client.post(
        "/api/banking/tc-kimlik",
        json={"count": 3},
        content_type="application/json",
    ).get_json()
    assert data.get("ok") is True
    assert "data" in data
    assert len(data["data"]) == 3


def test_tc_kimlik_validate_mode(banking_client):
    """TC Kimlik dogrulama modu calismalı."""
    data = banking_client.post(
        "/api/banking/tc-kimlik",
        json={"mode": "validate", "tc": "12345678901"},
        content_type="application/json",
    ).get_json()
    assert data.get("ok") is True
    assert "valid" in data


# ══════════════════════════════════════════════════════════════════════════════
# IBAN generation
# ══════════════════════════════════════════════════════════════════════════════

def test_iban_generation_returns_200(banking_client):
    """/api/banking/iban POST 200 dönmeli."""
    response = banking_client.post(
        "/api/banking/iban",
        json={"count": 2},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_iban_generation_has_data(banking_client):
    """/api/banking/iban data listesi dönmeli."""
    data = banking_client.post(
        "/api/banking/iban",
        json={"count": 2},
        content_type="application/json",
    ).get_json()
    assert data.get("ok") is True
    assert len(data["data"]) == 2


def test_iban_validate_mode(banking_client):
    """IBAN dogrulama modu calismalı."""
    data = banking_client.post(
        "/api/banking/iban",
        json={"mode": "validate", "iban": "TR330006100519786457841326"},
        content_type="application/json",
    ).get_json()
    assert data.get("ok") is True
    assert "valid" in data


# ══════════════════════════════════════════════════════════════════════════════
# CARD generation
# ══════════════════════════════════════════════════════════════════════════════

def test_card_generation_returns_200(banking_client):
    """/api/banking/card POST 200 dönmeli."""
    response = banking_client.post(
        "/api/banking/card",
        json={"count": 1, "card_type": "troy"},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_card_has_luhn_field(banking_client):
    """Kart verisi valid (Luhn) alanini icermeli."""
    data = banking_client.post(
        "/api/banking/card",
        json={"count": 1},
        content_type="application/json",
    ).get_json()
    assert data.get("ok") is True
    assert "valid" in data["data"][0]


def test_card_masked_option(banking_client):
    """masked=True ile kart numarasi maskelenmeli."""
    data = banking_client.post(
        "/api/banking/card",
        json={"count": 1, "masked": True},
        content_type="application/json",
    ).get_json()
    card_number = data["data"][0]["number"]
    # Maskelenmis numara * icermeli
    assert "*" in card_number


# ══════════════════════════════════════════════════════════════════════════════
# GENERATE endpoint
# ══════════════════════════════════════════════════════════════════════════════

def test_banking_generate_musteri_returns_200(banking_client):
    """/api/banking/generate musteri tipiyle 200 dönmeli."""
    response = banking_client.post(
        "/api/banking/generate",
        json={"entity_type": "musteri", "count": 5},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_banking_generate_returns_data(banking_client):
    """/api/banking/generate veri listesi dönmeli."""
    data = banking_client.post(
        "/api/banking/generate",
        json={"entity_type": "musteri", "count": 3},
        content_type="application/json",
    ).get_json()
    assert data.get("ok") is True
    assert data.get("count") == 3


def test_banking_generate_invalid_type_returns_400(banking_client):
    """Gecersiz entity_type → 400 dönmeli."""
    response = banking_client.post(
        "/api/banking/generate",
        json={"entity_type": "invalid_type", "count": 1},
        content_type="application/json",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


# ══════════════════════════════════════════════════════════════════════════════
# BANKING_AVAILABLE=False → 503
# ══════════════════════════════════════════════════════════════════════════════

def test_generation_503_when_banking_unavailable(banking_client, monkeypatch):
    """Banking modülü yoksa üretim endpoint'leri 503 dönmeli."""
    # datasim_banking_routes modülünü bul ve BANKING_AVAILABLE=False yap
    dm_mod = None
    for key in sys.modules:
        if "datasim_banking" in key:
            dm_mod = sys.modules[key]
            break

    if dm_mod is None:
        pytest.skip("datasim_banking_routes not loaded")

    monkeypatch.setattr(dm_mod, "BANKING_AVAILABLE", False)
    monkeypatch.setattr(dm_mod, "_IMPORT_ERROR", "banking module not found", raising=False)

    response = banking_client.post(
        "/api/banking/tc-kimlik",
        json={"count": 1},
        content_type="application/json",
    )
    assert response.status_code == 503


def test_503_response_has_error_message(banking_client, monkeypatch):
    """503 yaniti hata mesajini icermeli."""
    dm_mod = None
    for key in sys.modules:
        if "datasim_banking" in key:
            dm_mod = sys.modules[key]
            break

    if dm_mod is None:
        pytest.skip("datasim_banking_routes not loaded")

    monkeypatch.setattr(dm_mod, "BANKING_AVAILABLE", False)
    monkeypatch.setattr(dm_mod, "_IMPORT_ERROR", "no banking", raising=False)

    data = banking_client.post(
        "/api/banking/iban",
        json={"count": 1},
        content_type="application/json",
    ).get_json()
    assert "error" in data


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATE endpoint
# ══════════════════════════════════════════════════════════════════════════════

def test_validate_auto_returns_200(banking_client):
    """/api/banking/validate auto mod 200 dönmeli."""
    response = banking_client.post(
        "/api/banking/validate",
        json={"value": "12345678901", "type": "auto"},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_validate_contains_results(banking_client):
    """/api/banking/validate results dict icermeli."""
    data = banking_client.post(
        "/api/banking/validate",
        json={"value": "TR330006100519786457841326"},
        content_type="application/json",
    ).get_json()
    assert data.get("ok") is True
    assert "results" in data


# ══════════════════════════════════════════════════════════════════════════════
# TRANSACTION endpoint
# ══════════════════════════════════════════════════════════════════════════════

def test_transaction_returns_200(banking_client):
    """/api/banking/transaction POST 200 dönmeli."""
    response = banking_client.post(
        "/api/banking/transaction",
        json={"count": 3},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_transaction_returns_data(banking_client):
    """/api/banking/transaction veri listesi dönmeli."""
    data = banking_client.post(
        "/api/banking/transaction",
        json={"count": 5},
        content_type="application/json",
    ).get_json()
    assert data.get("ok") is True
    assert len(data["data"]) == 5


# ══════════════════════════════════════════════════════════════════════════════
# CREDIT endpoint
# ══════════════════════════════════════════════════════════════════════════════

def test_credit_returns_200(banking_client):
    """/api/banking/credit POST 200 dönmeli."""
    response = banking_client.post(
        "/api/banking/credit",
        json={"count": 2, "kredi_turu": "ihtiyac_kredisi"},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_credit_has_kredi_no(banking_client):
    """Kredi verisi kredi_no icermeli."""
    data = banking_client.post(
        "/api/banking/credit",
        json={"count": 1},
        content_type="application/json",
    ).get_json()
    assert data.get("ok") is True
    assert "kredi_no" in data["data"][0]


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-TABLE relational endpoint
# ══════════════════════════════════════════════════════════════════════════════

def test_multi_table_returns_200(banking_client):
    """/api/banking/multi-table 200 dönmeli."""
    response = banking_client.post(
        "/api/banking/multi-table",
        json={"musteri_count": 2, "hesap_per_musteri": 1, "islem_per_hesap": 2},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_multi_table_has_fk_integrity(banking_client):
    """Multi-table yaniti fk_integrity:True icermeli."""
    data = banking_client.post(
        "/api/banking/multi-table",
        json={"musteri_count": 1},
        content_type="application/json",
    ).get_json()
    assert data.get("ok") is True
    assert data.get("fk_integrity") is True
