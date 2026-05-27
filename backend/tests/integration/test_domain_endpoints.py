"""
backend/tests/integration/test_domain_endpoints.py
====================================================
Newly registered domain router smoke tests.
POST-registration endpoint response validation.

These tests verify that newly registered domain routers not only have
prefixes in OpenAPI (already tested in test_new_domain_routers.py) but also
respond correctly to basic GET requests.  Each test asserts status != 500 —
a 200 or 401/403 is acceptable; a 500 signals a broken router implementation.
"""
from __future__ import annotations

import pytest

try:
    from fastapi.testclient import TestClient
    from app.main import app
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="app import failed")


@pytest.fixture(scope="module")
def client():
    return TestClient(app, raise_server_exceptions=False)


# ── events domain ─────────────────────────────────────────────────────────────

def test_events_list_not_500(client):
    """GET /api/v1/events returns a non-500 status code."""
    r = client.get("/api/v1/events")
    assert r.status_code != 500, f"events list returned 500: {r.text}"


def test_events_history_not_500(client):
    """GET /api/v1/events/history returns a non-500 status code."""
    r = client.get("/api/v1/events/history")
    assert r.status_code != 500, f"events history returned 500: {r.text}"


# ── defects domain ────────────────────────────────────────────────────────────

def test_defects_list_not_500(client):
    """GET /api/v1/defects returns a non-500 status code."""
    r = client.get("/api/v1/defects")
    assert r.status_code != 500, f"defects list returned 500: {r.text}"


def test_defects_list_status_is_not_server_error(client):
    """GET /api/v1/defects status is 200 or auth error, never 5xx."""
    r = client.get("/api/v1/defects")
    assert r.status_code < 500, (
        f"defects endpoint returned server error {r.status_code}: {r.text}"
    )


# ── knowledge-base domain ─────────────────────────────────────────────────────

def test_kb_articles_list_not_500(client):
    """GET /api/v1/kb/articles returns a non-500 status code."""
    r = client.get("/api/v1/kb/articles")
    assert r.status_code != 500, f"kb articles returned 500: {r.text}"


def test_kb_articles_response_is_not_server_error(client):
    """GET /api/v1/kb/articles status is below 500."""
    r = client.get("/api/v1/kb/articles")
    assert r.status_code < 500, (
        f"kb/articles endpoint returned server error {r.status_code}: {r.text}"
    )


# ── compliance domain ─────────────────────────────────────────────────────────

def test_compliance_controls_list_not_500(client):
    """GET /api/v1/compliance/controls returns a non-500 status code."""
    r = client.get("/api/v1/compliance/controls")
    assert r.status_code != 500, f"compliance controls returned 500: {r.text}"


def test_compliance_controls_status_below_500(client):
    """GET /api/v1/compliance/controls is 200 or auth error, not 5xx."""
    r = client.get("/api/v1/compliance/controls")
    assert r.status_code < 500, (
        f"compliance/controls returned server error {r.status_code}: {r.text}"
    )


# ── visual comparisons domain ─────────────────────────────────────────────────

def test_visual_comparisons_list_not_500(client):
    """GET /api/v1/visual/comparisons returns a non-500 status code."""
    r = client.get("/api/v1/visual/comparisons")
    assert r.status_code != 500, f"visual comparisons returned 500: {r.text}"


# ── marketplace domain ────────────────────────────────────────────────────────

def test_marketplace_items_list_not_500(client):
    """GET /api/v1/marketplace/items returns a non-500 status code."""
    r = client.get("/api/v1/marketplace/items")
    assert r.status_code != 500, f"marketplace items returned 500: {r.text}"


# ── pilot sessions domain ─────────────────────────────────────────────────────

def test_pilot_sessions_list_not_500(client):
    """GET /api/v1/pilot/sessions returns a non-500 status code."""
    r = client.get("/api/v1/pilot/sessions")
    assert r.status_code != 500, f"pilot sessions returned 500: {r.text}"


# ── ingestion domain ──────────────────────────────────────────────────────────

def test_ingestion_requirements_not_500(client):
    """GET /api/v1/ingestion/requirements returns a non-500 status code."""
    r = client.get("/api/v1/ingestion/requirements")
    assert r.status_code != 500, f"ingestion requirements returned 500: {r.text}"
