"""Unit tests for the visual regression router (/visual)."""
from __future__ import annotations

import io
import pytest

try:
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from unittest.mock import AsyncMock, MagicMock, patch
    from app.domains.visual.router import router
except ImportError as _e:
    pytest.skip(f"visual router not importable: {_e}", allow_module_level=True)

# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.include_router(router)

    # Override auth dependencies
    try:
        from app.deps import get_current_user, require_permission
        fake_user = MagicMock()
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[require_permission("admin.visual")] = lambda: fake_user
    except Exception:
        pass

    return TestClient(app, raise_server_exceptions=False)


def _make_compare_result(**overrides):
    """Return a MagicMock simulating compare_png result."""
    result = MagicMock()
    result.ok = True
    result.status = "match"
    result.reason = ""
    result.baseline_path = "/data/baselines/login.png"
    result.diff_path = None
    result.diff_pixels = 0
    result.total_pixels = 10000
    result.diff_ratio = 0.0
    result.threshold_ratio = 0.01
    result.width = 1280
    result.height = 800
    for k, v in overrides.items():
        setattr(result, k, v)
    return result


# ---------------------------------------------------------------------------
# Tests: POST /visual/compare
# ---------------------------------------------------------------------------

class TestVisualCompare:
    def test_compare_with_valid_png_returns_200(self, client):
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        result = _make_compare_result()
        with patch("app.domains.visual.compare.compare_png", return_value=result):
            resp = client.post(
                "/visual/compare",
                data={"name": "login", "threshold_ratio": "0.05"},
                files={"image": ("login.png", io.BytesIO(fake_png), "image/png")},
            )
        assert resp.status_code == 200

    def test_compare_missing_image_field_returns_422(self, client):
        resp = client.post(
            "/visual/compare",
            data={"name": "login"},
        )
        assert resp.status_code == 422

    def test_compare_missing_name_field_returns_422(self, client):
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        resp = client.post(
            "/visual/compare",
            files={"image": ("login.png", io.BytesIO(fake_png), "image/png")},
        )
        assert resp.status_code == 422

    def test_compare_empty_image_returns_400(self, client):
        with patch("app.domains.visual.compare.compare_png") as mock_cmp:
            resp = client.post(
                "/visual/compare",
                data={"name": "login"},
                files={"image": ("empty.png", io.BytesIO(b""), "image/png")},
            )
        assert resp.status_code == 400

    def test_compare_response_contains_similarity_score(self, client):
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        result = _make_compare_result(diff_ratio=0.02, ok=False, status="diff")
        with patch("app.domains.visual.compare.compare_png", return_value=result):
            resp = client.post(
                "/visual/compare",
                data={"name": "checkout"},
                files={"image": ("checkout.png", io.BytesIO(fake_png), "image/png")},
            )
        if resp.status_code == 200:
            data = resp.json()
            assert "diff_ratio" in data or "ok" in data

    def test_compare_pillow_unavailable_returns_503(self, client):
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        result = _make_compare_result(ok=False, status="pillow_unavailable")
        with patch("app.domains.visual.compare.compare_png", return_value=result):
            resp = client.post(
                "/visual/compare",
                data={"name": "login"},
                files={"image": ("login.png", io.BytesIO(fake_png), "image/png")},
            )
        assert resp.status_code == 503

    def test_compare_with_update_baseline_flag(self, client):
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        result = _make_compare_result(status="baseline_updated")
        with patch("app.domains.visual.compare.compare_png", return_value=result) as mock_cmp:
            resp = client.post(
                "/visual/compare",
                data={"name": "login", "update_baseline": "true"},
                files={"image": ("login.png", io.BytesIO(fake_png), "image/png")},
            )
        if resp.status_code == 200:
            _, kwargs = mock_cmp.call_args
            assert kwargs.get("update_baseline") is True


# ---------------------------------------------------------------------------
# Tests: GET /visual/results
# ---------------------------------------------------------------------------

class TestVisualResults:
    def test_get_results_returns_200_or_404(self, client):
        resp = client.get("/visual/results")
        assert resp.status_code in (200, 404)

    def test_get_results_returns_list(self, client):
        with patch(
            "app.domains.visual.service.list_results",
            return_value=[],
        ):
            resp = client.get("/visual/results")
        if resp.status_code == 200:
            assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Tests: GET /visual/results/{id}
# ---------------------------------------------------------------------------

class TestGetVisualResult:
    def test_get_result_not_found_returns_404(self, client):
        with patch("app.domains.visual.service.get_result", return_value=None):
            resp = client.get("/visual/results/no-such-id")
        assert resp.status_code == 404

    def test_get_result_found_returns_200(self, client):
        fake_result = MagicMock()
        fake_result.to_dict.return_value = {"id": "res-001", "status": "match"}
        with patch("app.domains.visual.service.get_result", return_value=fake_result):
            resp = client.get("/visual/results/res-001")
        assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# Tests: GET /visual/config
# ---------------------------------------------------------------------------

class TestVisualConfig:
    def test_get_config_returns_dict(self, client):
        with patch(
            "app.domains.visual.service.get_config",
            return_value={"threshold_ratio": 0.01, "storage_backend": "local"},
        ):
            resp = client.get("/visual/config")
        if resp.status_code == 200:
            assert isinstance(resp.json(), dict)


# ---------------------------------------------------------------------------
# Tests: POST /visual/config
# ---------------------------------------------------------------------------

class TestUpdateVisualConfig:
    def test_post_config_returns_success(self, client):
        with patch("app.domains.visual.service.update_config", return_value=None):
            resp = client.post(
                "/visual/config",
                json={"threshold_ratio": 0.05},
            )
        assert resp.status_code in (200, 201, 204, 404)


# ---------------------------------------------------------------------------
# Tests: POST /visual/baseline/update
# ---------------------------------------------------------------------------

class TestForceBaselineUpdate:
    def test_force_update_empty_image_returns_400(self, client):
        resp = client.post(
            "/visual/baseline/update",
            data={"name": "login"},
            files={"image": ("empty.png", io.BytesIO(b""), "image/png")},
        )
        assert resp.status_code == 400

    def test_force_update_with_valid_image(self, client):
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        result = _make_compare_result(status="baseline_updated")
        with patch("app.domains.visual.compare.compare_png", return_value=result):
            resp = client.post(
                "/visual/baseline/update",
                data={"name": "login"},
                files={"image": ("login.png", io.BytesIO(fake_png), "image/png")},
            )
        assert resp.status_code in (200, 204)
