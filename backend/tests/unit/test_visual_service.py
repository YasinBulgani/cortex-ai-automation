"""Unit tests for the visual regression service facade.

Covers:
    - start_comparison raises ValueError for empty bytes
    - start_comparison (mocked compare_png) returns dict with ok and result_id
    - start_comparison raises ValueError when Pillow unavailable
    - get_result raises KeyError for unknown result_id
    - get_result returns entry for a known result_id
    - list_results returns a list
    - list_results with name_filter narrows results
"""
from __future__ import annotations

try:
    from app.domains.visual import service as visual_svc  # noqa: F401
    _import_ok = True
except ImportError:
    _import_ok = False

import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.skipif(
    not _import_ok,
    reason="app.domains.visual not importable — skipping visual service tests",
)


# ── Helpers / fixtures ───────────────────────────────────────────────────


def _make_compare_result(
    *,
    ok: bool = True,
    status: str = "new_baseline",
    reason: str = "baseline yazıldı",
) -> MagicMock:
    """Build a minimal CompareResult-like mock."""
    r = MagicMock()
    r.ok = ok
    r.status = status
    r.reason = reason
    r.baseline_path = "/fake/baseline.png"
    r.diff_path = None
    r.diff_pixels = 0
    r.total_pixels = 100
    r.diff_ratio = 0.0
    r.threshold_ratio = 0.005
    r.width = 10
    r.height = 10
    return r


# ── start_comparison — ValueError guards ─────────────────────────────────


def test_start_comparison_empty_bytes_raises_value_error():
    with pytest.raises(ValueError, match="boş olamaz"):
        visual_svc.start_comparison(name="login", actual_bytes=b"")


def test_start_comparison_pillow_unavailable_raises_value_error():
    mock_result = _make_compare_result(ok=False, status="pillow_unavailable", reason="Pillow kurulu değil")
    with patch("app.domains.visual.service.compare_png", return_value=mock_result):
        with pytest.raises(ValueError, match="Pillow"):
            visual_svc.start_comparison(name="login", actual_bytes=b"\x89PNG\r\n\x1a\n")


# ── start_comparison — success path ─────────────────────────────────────


def test_start_comparison_success_returns_dict_with_required_keys():
    mock_result = _make_compare_result()
    with patch("app.domains.visual.service.compare_png", return_value=mock_result):
        entry = visual_svc.start_comparison(name="login", actual_bytes=b"\x89PNG\r\n\x1a\n")
    assert isinstance(entry, dict)
    assert "result_id" in entry
    assert "ok" in entry


def test_start_comparison_result_id_stored_in_results():
    mock_result = _make_compare_result()
    with patch("app.domains.visual.service.compare_png", return_value=mock_result):
        entry = visual_svc.start_comparison(name="dashboard", actual_bytes=b"\x89PNG\r\n\x1a\n")
    result_id = entry["result_id"]
    # Must be retrievable immediately
    retrieved = visual_svc.get_result(result_id)
    assert retrieved["result_id"] == result_id


def test_start_comparison_ok_field_matches_compare_result():
    mock_result = _make_compare_result(ok=True, status="ok")
    with patch("app.domains.visual.service.compare_png", return_value=mock_result):
        entry = visual_svc.start_comparison(name="sidebar", actual_bytes=b"\x89PNG\r\n\x1a\n")
    assert entry["ok"] is True


# ── get_result ───────────────────────────────────────────────────────────


def test_get_result_unknown_id_raises_key_error():
    with pytest.raises(KeyError):
        visual_svc.get_result("nonexistent-result-id-00000000")


def test_get_result_known_id_returns_entry():
    mock_result = _make_compare_result()
    with patch("app.domains.visual.service.compare_png", return_value=mock_result):
        entry = visual_svc.start_comparison(name="header", actual_bytes=b"\x89PNG\r\n\x1a\n")
    fetched = visual_svc.get_result(entry["result_id"])
    assert fetched["name"] == "header"


# ── list_results ─────────────────────────────────────────────────────────


def test_list_results_returns_list():
    results = visual_svc.list_results()
    assert isinstance(results, list)


def test_list_results_name_filter_narrows_results():
    mock_result = _make_compare_result()
    unique_name = "unique_screen_xyz_abc"
    with patch("app.domains.visual.service.compare_png", return_value=mock_result):
        visual_svc.start_comparison(name=unique_name, actual_bytes=b"\x89PNG\r\n\x1a\n")

    filtered = visual_svc.list_results(name_filter=unique_name)
    assert all(r["name"] == unique_name for r in filtered)
    assert len(filtered) >= 1


def test_list_results_unknown_name_filter_returns_empty():
    filtered = visual_svc.list_results(name_filter="this_name_was_never_stored_zzzz")
    assert filtered == []
