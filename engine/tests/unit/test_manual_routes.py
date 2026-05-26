"""
tests/unit/test_manual_routes.py
=================================
manual_bp blueprint (/api/manual-tests, /api/manual-test-steps) için birim
testler.

Dış bağımlılıklar (core.db CRUD fonksiyonları) monkeypatching ile izole
edilir.
"""
import importlib
import sys
import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def engine_client(monkeypatch, tmp_path):
    """Test Flask istemcisi — DB stub'lanır."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-engine-internal")

    monkeypatch.setattr("config.settings.settings.BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr("config.settings.settings.BASE_URL", "http://localhost", raising=False)

    # utility route bağımlılıkları
    monkeypatch.setattr("core.db.get_run_stats", lambda: {"total": 0, "passed": 0, "failed": 0}, raising=False)
    monkeypatch.setattr("core.db.get_run_history", lambda: [], raising=False)
    monkeypatch.setattr("core.db.get_comprehensive_reports", lambda: [], raising=False)

    # manual route bağımlılıkları
    monkeypatch.setattr("core.db.get_manual_tests", lambda: [
        {"id": 1, "title": "Login Test", "status": "pending", "steps": []},
        {"id": 2, "title": "Logout Test", "status": "passed", "steps": []},
    ], raising=False)
    monkeypatch.setattr("core.db.create_manual_test", lambda title: 42, raising=False)
    monkeypatch.setattr("core.db.delete_manual_test", lambda test_id: None, raising=False)
    monkeypatch.setattr("core.db.update_manual_test_status", lambda test_id, status: None, raising=False)
    monkeypatch.setattr("core.db.add_manual_step", lambda test_id, action, expected: None, raising=False)
    monkeypatch.setattr("core.db.delete_manual_step", lambda step_id: None, raising=False)
    monkeypatch.setattr("core.db.update_manual_step_status", lambda step_id, status: None, raising=False)

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client


@pytest.fixture
def authed_client(engine_client):
    with engine_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["email"] = "test@example.com"
    return engine_client


# ── GET /api/manual-tests ─────────────────────────────────────────────────────

def test_get_manual_tests_returns_200(authed_client):
    """GET /api/manual-tests 200 dönmeli."""
    resp = authed_client.get("/api/manual-tests")
    assert resp.status_code == 200


def test_get_manual_tests_returns_list(authed_client):
    """GET /api/manual-tests liste dönmeli."""
    resp = authed_client.get("/api/manual-tests")
    data = resp.get_json()
    assert isinstance(data, list)


def test_get_manual_tests_returns_correct_count(authed_client):
    """GET /api/manual-tests stub'daki 2 öğeyi dönmeli."""
    resp = authed_client.get("/api/manual-tests")
    data = resp.get_json()
    assert len(data) == 2


def test_get_manual_tests_items_have_title(authed_client):
    """Her test öğesi title alanı içermeli."""
    resp = authed_client.get("/api/manual-tests")
    data = resp.get_json()
    for item in data:
        assert "title" in item


# ── POST /api/manual-tests ────────────────────────────────────────────────────

def test_post_manual_test_missing_title_returns_400(authed_client):
    """title eksikse 400 dönmeli."""
    resp = authed_client.post(
        "/api/manual-tests",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_post_manual_test_empty_title_returns_400(authed_client):
    """title None-falsy ise 400 dönmeli."""
    resp = authed_client.post(
        "/api/manual-tests",
        json={"title": None},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_post_manual_test_success_returns_ok(authed_client):
    """Geçerli title → ok:True dönmeli."""
    resp = authed_client.post(
        "/api/manual-tests",
        json={"title": "New Smoke Test"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("ok") is True


def test_post_manual_test_success_returns_id(authed_client):
    """Başarılı yanıt id alanı içermeli."""
    resp = authed_client.post(
        "/api/manual-tests",
        json={"title": "Registration Flow"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "id" in data
    assert data["id"] == 42


def test_post_manual_test_returns_json(authed_client):
    """Yanıt JSON formatında olmalı."""
    resp = authed_client.post(
        "/api/manual-tests",
        json={"title": "Checkout Test"},
        content_type="application/json",
    )
    assert resp.get_json() is not None


# ── DELETE /api/manual-tests/<id> ────────────────────────────────────────────

def test_delete_manual_test_returns_ok(authed_client):
    """DELETE /api/manual-tests/<id> → ok:True dönmeli."""
    resp = authed_client.delete("/api/manual-tests/1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("ok") is True


def test_delete_manual_test_with_nonexistent_id(authed_client):
    """Var olmayan id ile DELETE → yine ok dönmeli (DB stub silindiğini varsayar)."""
    resp = authed_client.delete("/api/manual-tests/9999")
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True


# ── PUT /api/manual-tests/<id> ───────────────────────────────────────────────

def test_put_manual_test_status_returns_ok(authed_client):
    """PUT /api/manual-tests/<id> durum güncellemesi → ok:True dönmeli."""
    resp = authed_client.put(
        "/api/manual-tests/1",
        json={"status": "passed"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True


def test_put_manual_test_status_with_failed(authed_client):
    """status=failed ile PUT → ok dönmeli."""
    resp = authed_client.put(
        "/api/manual-tests/2",
        json={"status": "failed"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True


# ── POST /api/manual-tests/<id>/steps ────────────────────────────────────────

def test_post_step_missing_action_returns_400(authed_client):
    """action eksikse 400 dönmeli."""
    resp = authed_client.post(
        "/api/manual-tests/1/steps",
        json={"expected": "Should see dashboard"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_post_step_missing_expected_returns_400(authed_client):
    """expected eksikse 400 dönmeli."""
    resp = authed_client.post(
        "/api/manual-tests/1/steps",
        json={"action": "Click login"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_post_step_missing_both_returns_400(authed_client):
    """Her ikisi de eksikse 400 dönmeli."""
    resp = authed_client.post(
        "/api/manual-tests/1/steps",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_post_step_success_returns_ok(authed_client):
    """Geçerli action + expected → ok:True dönmeli."""
    resp = authed_client.post(
        "/api/manual-tests/1/steps",
        json={"action": "Click login button", "expected": "Redirect to dashboard"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True


def test_post_step_with_different_test_id(authed_client):
    """Farklı test_id ile step ekleme çalışmalı."""
    resp = authed_client.post(
        "/api/manual-tests/99/steps",
        json={"action": "Fill username", "expected": "Field shows text"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True


# ── DELETE /api/manual-test-steps/<id> ───────────────────────────────────────

def test_delete_step_returns_ok(authed_client):
    """DELETE /api/manual-test-steps/<id> → ok:True dönmeli."""
    resp = authed_client.delete("/api/manual-test-steps/5")
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True


def test_delete_step_with_any_id(authed_client):
    """Herhangi bir step_id ile silme ok dönmeli."""
    resp = authed_client.delete("/api/manual-test-steps/100")
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True


# ── PUT /api/manual-test-steps/<id> ──────────────────────────────────────────

def test_put_step_status_returns_ok(authed_client):
    """PUT /api/manual-test-steps/<id> durum güncellemesi → ok:True dönmeli."""
    resp = authed_client.put(
        "/api/manual-test-steps/3",
        json={"status": "passed"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True


def test_put_step_status_with_failed(authed_client):
    """status=failed ile step PUT → ok dönmeli."""
    resp = authed_client.put(
        "/api/manual-test-steps/7",
        json={"status": "failed"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True


def test_put_step_returns_json(authed_client):
    """PUT step yanıtı JSON olmalı."""
    resp = authed_client.put(
        "/api/manual-test-steps/1",
        json={"status": "skipped"},
        content_type="application/json",
    )
    assert resp.get_json() is not None
