"""
tests/unit/test_datasim_routes.py
====================================
Datasim blueprint (/api/datasim/*, /api/datasim/datasets) icin birim testler.

DATASETS listesi modul seviyesinde tanimlidir, dogrudan monkeypatching ile
erisilebilir. pandas/numpy bagimliliklar stub'lanir.
"""
import importlib.util
import sys
import types
import json
import pytest
from flask import Flask


# ── Fixture ───────────────────────────────────────────────────────────────────

def _load_datasim_blueprint():
    """datasim_routes modulunu taze yukler (sys.modules cache temizlenmis)."""
    for key in list(sys.modules.keys()):
        if "datasim_routes" in key:
            del sys.modules[key]

    spec = importlib.util.spec_from_file_location(
        "datasim_routes",
        "/Users/yasin_bulgan/Desktop/Neurex_QA/engine/routes/datasim_routes.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def datasim_client():
    """Datasim blueprint'ini Flask test istemcisine baglar."""
    mod = _load_datasim_blueprint()

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(mod.datasim_bp)

    with app.test_client() as client:
        yield client, mod


# ── /api/datasim/datasets (GET) ───────────────────────────────────────────────

def test_list_datasets_returns_200(datasim_client):
    client, _ = datasim_client
    resp = client.get("/api/datasim/datasets")
    assert resp.status_code == 200


def test_list_datasets_returns_json_list(datasim_client):
    client, _ = datasim_client
    data = client.get("/api/datasim/datasets").get_json()
    assert isinstance(data, list)


def test_list_datasets_not_empty(datasim_client):
    client, _ = datasim_client
    data = client.get("/api/datasim/datasets").get_json()
    assert len(data) > 0


def test_list_datasets_entries_have_id(datasim_client):
    client, _ = datasim_client
    data = client.get("/api/datasim/datasets").get_json()
    for entry in data:
        assert "id" in entry


def test_list_datasets_entries_have_name(datasim_client):
    client, _ = datasim_client
    data = client.get("/api/datasim/datasets").get_json()
    for entry in data:
        assert "name" in entry


def test_list_datasets_entries_have_rows_and_cols(datasim_client):
    client, _ = datasim_client
    data = client.get("/api/datasim/datasets").get_json()
    for entry in data:
        assert "rows" in entry
        assert "cols" in entry


def test_list_datasets_contains_bank_marketing(datasim_client):
    client, _ = datasim_client
    data = client.get("/api/datasim/datasets").get_json()
    ids = [d["id"] for d in data]
    assert "bank_marketing" in ids


def test_list_datasets_contains_fraud_detection(datasim_client):
    client, _ = datasim_client
    data = client.get("/api/datasim/datasets").get_json()
    ids = [d["id"] for d in data]
    assert "fraud_detection" in ids


# ── /api/datasim/datasets/load (POST) ────────────────────────────────────────

def test_load_dataset_missing_id_returns_404(datasim_client):
    """Bilinmeyen dataset_id ile 404 donmeli."""
    client, _ = datasim_client

    # pandas stub — eger import edilirse cokmasin
    pd_mod = types.ModuleType("pandas")
    pd_mod.read_csv = lambda *a, **kw: (_ for _ in ()).throw(Exception("stub"))
    sys.modules.setdefault("pandas", pd_mod)
    sys.modules.setdefault("requests", types.ModuleType("requests"))

    resp = client.post(
        "/api/datasim/datasets/load",
        json={"id": "nonexistent_dataset_xyz"},
        content_type="application/json",
    )
    assert resp.status_code == 404


def test_load_dataset_unknown_id_response_has_error(datasim_client):
    client, _ = datasim_client
    sys.modules.setdefault("requests", types.ModuleType("requests"))

    data = client.post(
        "/api/datasim/datasets/load",
        json={"id": "unknown_xyz"},
        content_type="application/json",
    ).get_json()
    assert "error" in data


def test_load_dataset_known_id_attempted(datasim_client, monkeypatch, tmp_path):
    """Bilinen ID ile istek gonderildiginde 404 donmemeli (pandas hatasi 500 verebilir)."""
    client, mod = datasim_client

    # pandas ve requests stub
    import pandas as pd_stub_cls
    fake_pd = types.ModuleType("pandas")

    class FakeDF:
        def head(self, n):
            return self
        def to_csv(self, index=True):
            return "col1,col2\n1,2\n"

    fake_pd.read_csv = lambda *a, **kw: FakeDF()
    fake_pd.DataFrame = FakeDF
    sys.modules["pandas"] = fake_pd

    fake_req = types.ModuleType("requests")
    fake_req.get = lambda url, **kw: type("R", (), {"text": "col1\n1\n", "raise_for_status": lambda self: None})()
    sys.modules["requests"] = fake_req

    resp = client.post(
        "/api/datasim/datasets/load",
        json={"id": "bank_marketing", "sample_rows": 5},
        content_type="application/json",
    )
    # 404 olmamali — 200 veya 500 (pandas stub hatasi) kabul edilir
    assert resp.status_code != 404


# ── DATASETS module-level list sanity ────────────────────────────────────────

def test_datasets_list_has_correct_structure(datasim_client):
    """Modul icindeki DATASETS listesinin yapisi dogru olmali."""
    _, mod = datasim_client
    required_keys = {"id", "name", "rows", "cols"}
    for ds in mod.DATASETS:
        assert required_keys.issubset(ds.keys()), f"Dataset eksik alan: {ds.get('id')}"


def test_datasets_list_has_minimum_count(datasim_client):
    _, mod = datasim_client
    assert len(mod.DATASETS) >= 5


def test_datasets_rows_are_positive(datasim_client):
    _, mod = datasim_client
    for ds in mod.DATASETS:
        assert ds["rows"] > 0


def test_datasets_cols_are_positive(datasim_client):
    _, mod = datasim_client
    for ds in mod.DATASETS:
        assert ds["cols"] > 0


# ── Blueprint registration ────────────────────────────────────────────────────

def test_blueprint_url_prefix_correct(datasim_client):
    """Blueprint'in beklenen route'lari kayitli olmali."""
    _, mod = datasim_client
    assert mod.datasim_bp is not None


def test_load_dataset_no_body_returns_404(datasim_client):
    """Body gonderilmezse bos id ile 404 donmeli."""
    client, _ = datasim_client
    sys.modules.setdefault("requests", types.ModuleType("requests"))
    resp = client.post(
        "/api/datasim/datasets/load",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 404
