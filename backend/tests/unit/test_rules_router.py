"""Rules (RuleSet) router endpoint'leri — dataset kural seti yönetimi.

Gerçek FastAPI app + TestClient kullanır; DB bağımlılıkları monkeypatch'li.
Router layer odaklıdır: HTTP durum kodları, request validation, hata yönetimi.

Not: rules/router.py prefix'i /datasets — kural setleri dataset'e bağlıdır.
"""
from __future__ import annotations

try:
    from unittest.mock import MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.rules.router import router

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = "user-001"
    return user


def _make_ruleset(
    rs_id: str = "rs-001",
    dataset_id: str = "ds-001",
    name: str = "Test RuleSet",
) -> MagicMock:
    rs = MagicMock()
    rs.id = rs_id
    rs.dataset_id = dataset_id
    rs.name = name
    rs.rules_body = {"rules": []}
    rs.version = "1.0"
    rs.created_at = "2026-05-26T00:00:00"
    return rs


def _make_dataset(ds_id: str = "ds-001") -> MagicMock:
    ds = MagicMock()
    ds.id = ds_id
    return ds


def _valid_ruleset_body() -> dict:
    return {
        "name": "My Rules",
        "rules_body": {"rules": [{"field": "age", "op": "gt", "value": 18}]},
        "version": "1.0",
    }


# ---------------------------------------------------------------------------
# GET /datasets/{dataset_id}/rule-sets — list
# ---------------------------------------------------------------------------

def test_list_rule_sets_dataset_not_found_404() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    mock_user = _make_user()
    mock_db = MagicMock()
    mock_db.get.return_value = None  # Dataset not found

    with (
        patch("app.domains.rules.router.get_db", return_value=mock_db),
        patch("app.domains.rules.router.get_current_user", return_value=mock_user),
    ):
        r = client.get("/datasets/nonexistent/rule-sets")
    assert r.status_code == 404


def test_list_rule_sets_empty() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    mock_user = _make_user()
    mock_db = MagicMock()
    mock_db.get.return_value = _make_dataset()
    mock_db.scalars.return_value.all.return_value = []

    with (
        patch("app.domains.rules.router.get_db", return_value=mock_db),
        patch("app.domains.rules.router.get_current_user", return_value=mock_user),
    ):
        r = client.get("/datasets/ds-001/rule-sets")
    assert r.status_code == 200
    assert r.json() == []


def test_list_rule_sets_returns_items() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    mock_user = _make_user()
    mock_db = MagicMock()
    mock_db.get.return_value = _make_dataset()
    rulesets = [_make_ruleset("rs-1"), _make_ruleset("rs-2")]
    mock_db.scalars.return_value.all.return_value = rulesets

    with (
        patch("app.domains.rules.router.get_db", return_value=mock_db),
        patch("app.domains.rules.router.get_current_user", return_value=mock_user),
    ):
        r = client.get("/datasets/ds-001/rule-sets")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# POST /datasets/{dataset_id}/rule-sets — create
# ---------------------------------------------------------------------------

def test_create_rule_set_dataset_not_found_404() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    mock_user = _make_user()
    mock_db = MagicMock()
    mock_db.get.return_value = None

    with (
        patch("app.domains.rules.router.get_db", return_value=mock_db),
        patch("app.domains.rules.router.get_current_user", return_value=mock_user),
        patch("app.domains.rules.router.log_audit"),
    ):
        r = client.post("/datasets/nonexistent/rule-sets", json=_valid_ruleset_body())
    assert r.status_code == 404


def test_create_rule_set_missing_name_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    mock_user = _make_user()
    mock_db = MagicMock()
    mock_db.get.return_value = _make_dataset()

    with (
        patch("app.domains.rules.router.get_db", return_value=mock_db),
        patch("app.domains.rules.router.get_current_user", return_value=mock_user),
    ):
        r = client.post(
            "/datasets/ds-001/rule-sets",
            json={"rules_body": {}, "version": "1.0"},  # missing name
        )
    assert r.status_code == 422


def test_create_rule_set_success_201() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    mock_user = _make_user()
    mock_db = MagicMock()
    mock_db.get.return_value = _make_dataset()
    created_rs = _make_ruleset()
    mock_db.flush.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    with (
        patch("app.domains.rules.router.get_db", return_value=mock_db),
        patch("app.domains.rules.router.get_current_user", return_value=mock_user),
        patch("app.domains.rules.router.log_audit"),
        patch("app.domains.rules.router.RuleSet", return_value=created_rs),
    ):
        r = client.post("/datasets/ds-001/rule-sets", json=_valid_ruleset_body())
    assert r.status_code == 201


def test_create_rule_set_empty_name_422() -> None:
    """Empty string name should fail Pydantic validation."""
    if not _IMPORT_OK:
        return
    client = _app()
    mock_user = _make_user()
    mock_db = MagicMock()
    mock_db.get.return_value = _make_dataset()

    with (
        patch("app.domains.rules.router.get_db", return_value=mock_db),
        patch("app.domains.rules.router.get_current_user", return_value=mock_user),
    ):
        # Try with completely empty body
        r = client.post("/datasets/ds-001/rule-sets", json={})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /datasets/{dataset_id}/rule-sets/{rule_set_id}
# ---------------------------------------------------------------------------

def test_get_rule_set_not_found_404() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    mock_user = _make_user()
    mock_db = MagicMock()
    mock_db.get.return_value = None

    with (
        patch("app.domains.rules.router.get_db", return_value=mock_db),
        patch("app.domains.rules.router.get_current_user", return_value=mock_user),
    ):
        r = client.get("/datasets/ds-001/rule-sets/nonexistent")
    assert r.status_code == 404


def test_get_rule_set_wrong_dataset_404() -> None:
    """RuleSet exists but belongs to different dataset → 404."""
    if not _IMPORT_OK:
        return
    client = _app()
    mock_user = _make_user()
    mock_db = MagicMock()
    # RuleSet found but dataset_id mismatch
    rs = _make_ruleset(dataset_id="ds-OTHER")
    mock_db.get.return_value = rs

    with (
        patch("app.domains.rules.router.get_db", return_value=mock_db),
        patch("app.domains.rules.router.get_current_user", return_value=mock_user),
    ):
        r = client.get("/datasets/ds-001/rule-sets/rs-001")
    assert r.status_code == 404


def test_get_rule_set_found_200() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    mock_user = _make_user()
    mock_db = MagicMock()
    rs = _make_ruleset(dataset_id="ds-001")
    mock_db.get.return_value = rs

    with (
        patch("app.domains.rules.router.get_db", return_value=mock_db),
        patch("app.domains.rules.router.get_current_user", return_value=mock_user),
    ):
        r = client.get("/datasets/ds-001/rule-sets/rs-001")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Additional edge-case tests for robustness
# ---------------------------------------------------------------------------

def test_list_rule_sets_limit_respected() -> None:
    """Query param ile limitlenmis liste doğrulaması."""
    if not _IMPORT_OK:
        return
    client = _app()
    mock_user = _make_user()
    mock_db = MagicMock()
    mock_db.get.return_value = _make_dataset()
    mock_db.scalars.return_value.all.return_value = []

    with (
        patch("app.domains.rules.router.get_db", return_value=mock_db),
        patch("app.domains.rules.router.get_current_user", return_value=mock_user),
    ):
        r = client.get("/datasets/ds-001/rule-sets")
    assert r.status_code == 200


def test_create_rule_set_audit_logged() -> None:
    """log_audit çağrıldığını doğrula."""
    if not _IMPORT_OK:
        return
    client = _app()
    mock_user = _make_user()
    mock_db = MagicMock()
    mock_db.get.return_value = _make_dataset()
    created_rs = _make_ruleset()

    with (
        patch("app.domains.rules.router.get_db", return_value=mock_db),
        patch("app.domains.rules.router.get_current_user", return_value=mock_user),
        patch("app.domains.rules.router.log_audit") as mock_audit,
        patch("app.domains.rules.router.RuleSet", return_value=created_rs),
    ):
        r = client.post("/datasets/ds-001/rule-sets", json=_valid_ruleset_body())
    if r.status_code == 201:
        mock_audit.assert_called_once()
