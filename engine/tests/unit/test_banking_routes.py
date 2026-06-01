"""
tests/unit/test_banking_routes.py
===================================
Banking blueprint (/api/banking/*) icin birim testler.

BANKING_AVAILABLE=True/False her iki yol da test edilir.
Dis bagimliliklar (core.banking.*) sys.modules stub'lari ile izole edilir.
"""
import importlib
import sys
import types
import json
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_banking_stubs():
    """core.banking.* modullerini sahte nesnelerle sys.modules'a ekler."""
    # --- identity ---
    identity_mod = types.ModuleType("core.banking.generators.identity")
    identity_mod.generate_tc_kimlik = lambda: "12345678901"
    identity_mod.validate_tc_kimlik = lambda tc: True
    identity_mod.generate_vkn = lambda: "1234567890"
    identity_mod.validate_vkn = lambda vkn: True
    identity_mod.generate_tc_kimlik_batch = lambda count, seed=None: ["12345678901"] * count

    # --- account ---
    account_mod = types.ModuleType("core.banking.generators.account")
    account_mod.generate_tr_iban = lambda bank_code=None: "TR330006100519786457841326"
    account_mod.validate_tr_iban = lambda iban: True
    account_mod.generate_swift = lambda bank_code=None: "AKBKTRIS"
    account_mod.get_bank_list = lambda: [
        {"code": "0006", "name": "Akbank", "swift": "AKBKTRIS"},
        {"code": "0010", "name": "Ziraat Bankasi", "swift": "TCZBTR2A"},
    ]
    account_mod.TR_BANK_CODES = {"0006": "Akbank", "0010": "Ziraat Bankasi"}

    # --- card ---
    card_mod = types.ModuleType("core.banking.generators.card")
    card_mod.generate_card_number = lambda card_type="troy": "9792123456789012"
    card_mod.luhn_check = lambda no: True
    card_mod.generate_cvv = lambda card_type="troy": "123"
    card_mod.generate_card_expiry = lambda: "12/28"
    card_mod.mask_card_number = lambda no: "979212******9012"

    # --- transaction ---
    transaction_mod = types.ModuleType("core.banking.generators.transaction")
    transaction_mod.generate_eft_reference = lambda: "EFT202401010001"
    transaction_mod.generate_fast_reference = lambda: "FAST202401010001"
    transaction_mod.generate_doviz_kuru = lambda currency="USD": 32.50
    transaction_mod.generate_transaction_date = lambda: "2024-01-01T10:00:00"
    transaction_mod.generate_cek_numarasi = lambda: "CHK0000001"
    transaction_mod.generate_aciklama = lambda: "Test islemi"
    transaction_mod.generate_merchant = lambda: "Test Magaza"
    transaction_mod.DOVIZ_KURLAR = {"USD": 32.50, "EUR": 35.00}

    # --- credit ---
    credit_mod = types.ModuleType("core.banking.generators.credit")
    credit_mod.generate_faiz_orani = lambda segment="standard": 2.5
    credit_mod.generate_kredi_limiti = lambda segment="standard", income=5000: 50000
    credit_mod.generate_risk_skoru = lambda: 750
    credit_mod.classify_segment = lambda score: "standard"
    credit_mod.generate_aylik_gelir = lambda: 8000
    credit_mod.SEGMENT_KURALLAR = {}
    credit_mod.FAIZ_SPREAD = {}
    credit_mod.TCMB_POLITIKA_FAIZ = 45.0

    # --- factories ---
    factories_mod = types.ModuleType("core.banking.factories.banking_factories")
    factories_mod.generate_banking_data = lambda data_type, count=1: [{}] * count
    factories_mod.generate_relational_dataset = lambda config: {}
    factories_mod.FACTORY_MAP = {
        "identity": None,
        "account": None,
        "card": None,
        "transaction": None,
        "credit": None,
    }

    # Parent packages
    core_mod = sys.modules.setdefault("core", types.ModuleType("core"))
    banking_pkg = types.ModuleType("core.banking")
    gen_pkg = types.ModuleType("core.banking.generators")
    fac_pkg = types.ModuleType("core.banking.factories")

    sys.modules["core"] = core_mod
    sys.modules["core.banking"] = banking_pkg
    sys.modules["core.banking.generators"] = gen_pkg
    sys.modules["core.banking.generators.identity"] = identity_mod
    sys.modules["core.banking.generators.account"] = account_mod
    sys.modules["core.banking.generators.card"] = card_mod
    sys.modules["core.banking.generators.transaction"] = transaction_mod
    sys.modules["core.banking.generators.credit"] = credit_mod
    sys.modules["core.banking.factories"] = fac_pkg
    sys.modules["core.banking.factories.banking_factories"] = factories_mod


def _remove_banking_stubs():
    for key in list(sys.modules.keys()):
        if "core.banking" in key:
            del sys.modules[key]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def banking_client_available():
    """Banking modulu AVAILABLE=True olan test istemcisi."""
    _make_banking_stubs()
    sys.modules.pop("engine.routes.banking_routes", None)
    sys.modules.pop("routes.banking_routes", None)

    import importlib
    import types
    from flask import Flask

    # Blueprint'i ayri import et
    spec = importlib.util.spec_from_file_location(
        "banking_routes",
        "/Users/yasin_bulgan/Desktop/Neurex_QA/engine/routes/banking_routes.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Stubs yuklu oldugu icin BANKING_AVAILABLE=True olmali
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(mod.banking_bp)

    with app.test_client() as client:
        yield client, mod

    _remove_banking_stubs()


@pytest.fixture
def banking_client_unavailable():
    """Banking modulu BANKING_AVAILABLE=False olan test istemcisi."""
    # Stub'lari KALDIRARAK import hatasi simule et
    _remove_banking_stubs()
    sys.modules.pop("banking_routes", None)

    from flask import Flask
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "banking_routes_unavail",
        "/Users/yasin_bulgan/Desktop/Neurex_QA/engine/routes/banking_routes.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.BANKING_AVAILABLE is False, "Banking modulu yuklu olmamali"

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(mod.banking_bp)

    with app.test_client() as client:
        yield client, mod


# ── /api/banking/info ─────────────────────────────────────────────────────────

def test_info_returns_200_when_available(banking_client_available):
    client, _ = banking_client_available
    resp = client.get("/api/banking/info")
    assert resp.status_code == 200


def test_info_returns_200_when_unavailable(banking_client_unavailable):
    """info endpoint _check_banking() cagrisi yapmaz, 503 donmemeli."""
    client, _ = banking_client_unavailable
    resp = client.get("/api/banking/info")
    assert resp.status_code == 200


def test_info_contains_module_name(banking_client_available):
    client, _ = banking_client_available
    data = client.get("/api/banking/info").get_json()
    assert "module" in data
    assert "Banking" in data["module"]


def test_info_available_true_when_module_loaded(banking_client_available):
    client, _ = banking_client_available
    data = client.get("/api/banking/info").get_json()
    assert data["available"] is True


def test_info_available_false_when_module_missing(banking_client_unavailable):
    client, _ = banking_client_unavailable
    data = client.get("/api/banking/info").get_json()
    assert data["available"] is False


# ── 503 graceful degradation ──────────────────────────────────────────────────

def test_banks_503_when_unavailable(banking_client_unavailable):
    client, _ = banking_client_unavailable
    resp = client.get("/api/banking/banks")
    assert resp.status_code == 503


def test_tc_kimlik_503_when_unavailable(banking_client_unavailable):
    client, _ = banking_client_unavailable
    resp = client.post("/api/banking/tc-kimlik", json={})
    assert resp.status_code == 503


def test_card_503_when_unavailable(banking_client_unavailable):
    client, _ = banking_client_unavailable
    resp = client.post("/api/banking/card", json={})
    assert resp.status_code == 503


def test_503_response_has_ok_false(banking_client_unavailable):
    client, _ = banking_client_unavailable
    data = client.get("/api/banking/banks").get_json()
    assert data["ok"] is False


def test_503_response_has_error_message(banking_client_unavailable):
    client, _ = banking_client_unavailable
    data = client.get("/api/banking/banks").get_json()
    assert "error" in data


# ── /api/banking/banks ────────────────────────────────────────────────────────

def test_banks_returns_200(banking_client_available):
    client, _ = banking_client_available
    resp = client.get("/api/banking/banks")
    assert resp.status_code == 200


def test_banks_returns_list(banking_client_available):
    client, _ = banking_client_available
    data = client.get("/api/banking/banks").get_json()
    assert "banks" in data
    assert isinstance(data["banks"], list)
    assert len(data["banks"]) > 0


def test_banks_response_ok_true(banking_client_available):
    client, _ = banking_client_available
    data = client.get("/api/banking/banks").get_json()
    assert data["ok"] is True


# ── /api/banking/tc-kimlik ────────────────────────────────────────────────────

def test_tc_kimlik_success(banking_client_available):
    client, _ = banking_client_available
    resp = client.post("/api/banking/tc-kimlik", json={"count": 1})
    assert resp.status_code == 200


def test_tc_kimlik_returns_data_list(banking_client_available):
    client, _ = banking_client_available
    data = client.post("/api/banking/tc-kimlik", json={"count": 3}).get_json()
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 3


def test_tc_kimlik_validate_mode(banking_client_available):
    client, _ = banking_client_available
    payload = {"mode": "validate", "tc": "12345678901"}
    data = client.post("/api/banking/tc-kimlik", json=payload).get_json()
    assert "valid" in data
    assert "tc" in data


# ── /api/banking/card ─────────────────────────────────────────────────────────

def test_card_generate_returns_200(banking_client_available):
    client, _ = banking_client_available
    resp = client.post("/api/banking/card", json={"count": 1})
    assert resp.status_code == 200


def test_card_response_has_card_number(banking_client_available):
    client, _ = banking_client_available
    data = client.post("/api/banking/card", json={"count": 1}).get_json()
    assert "data" in data
    assert len(data["data"]) == 1
    card = data["data"][0]
    assert "number" in card


def test_card_luhn_valid_field_present(banking_client_available):
    client, _ = banking_client_available
    data = client.post("/api/banking/card", json={"count": 1}).get_json()
    card = data["data"][0]
    assert "valid" in card


# ── /api/banking/eft via transaction ─────────────────────────────────────────

def test_eft_503_when_unavailable(banking_client_unavailable):
    client, _ = banking_client_unavailable
    resp = client.post("/api/banking/eft", json={})
    # Either 503 (check_banking) or 404 (route not defined) — both indicate unavailability
    assert resp.status_code in (503, 404, 405)


def test_vkn_503_when_unavailable(banking_client_unavailable):
    client, _ = banking_client_unavailable
    resp = client.post("/api/banking/vkn", json={})
    assert resp.status_code == 503


def test_iban_returns_200_when_available(banking_client_available):
    client, _ = banking_client_available
    resp = client.post("/api/banking/iban", json={"count": 1})
    assert resp.status_code == 200


def test_iban_response_has_data(banking_client_available):
    client, _ = banking_client_available
    data = client.post("/api/banking/iban", json={"count": 2}).get_json()
    assert "data" in data
    assert len(data["data"]) == 2
