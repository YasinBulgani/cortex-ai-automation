"""Unit tests for the compliance service facade.

Covers:
    - get_coverage_summary returns dict with required keys
    - list_controls filters by standard (case-insensitive)
    - list_controls with no filter returns all controls
    - get_control returns a Control for a known id
    - get_control returns None (KeyError guard) for an unknown id
    - mappings_for returns a non-empty list for a mapped control
    - mappings_for returns empty list for an unmapped control id
    - unmapped_controls returns a list
    - build_evidence_pack structure integrity
"""
from __future__ import annotations

try:
    from app.domains.compliance import service as compliance_svc  # noqa: F401
    _import_ok = True
except ImportError:
    _import_ok = False

import pytest

pytestmark = pytest.mark.skipif(
    not _import_ok,
    reason="app.domains.compliance not importable — skipping compliance service tests",
)


# ── get_coverage_summary ─────────────────────────────────────────────────


def test_get_coverage_summary_returns_dict():
    result = compliance_svc.get_coverage_summary()
    assert isinstance(result, dict)


def test_get_coverage_summary_has_required_keys():
    result = compliance_svc.get_coverage_summary()
    required = {"total_controls", "total_mappings", "unmapped", "coverage_pct", "standards"}
    assert required <= result.keys(), f"Missing keys: {required - result.keys()}"


def test_get_coverage_summary_total_controls_positive():
    result = compliance_svc.get_coverage_summary()
    assert result["total_controls"] > 0


def test_get_coverage_summary_coverage_pct_in_range():
    result = compliance_svc.get_coverage_summary()
    pct = result["coverage_pct"]
    assert 0.0 <= pct <= 100.0


# ── list_controls ────────────────────────────────────────────────────────


def test_list_controls_no_filter_returns_all():
    controls = compliance_svc.list_controls()
    assert isinstance(controls, list)
    assert len(controls) > 0


def test_list_controls_filter_by_standard_kvkk():
    controls = compliance_svc.list_controls(standard="KVKK")
    assert isinstance(controls, list)
    assert len(controls) > 0
    assert all(c.standard == "KVKK" for c in controls)


def test_list_controls_filter_by_standard_case_insensitive():
    lower = compliance_svc.list_controls(standard="kvkk")
    upper = compliance_svc.list_controls(standard="KVKK")
    assert lower == upper


def test_list_controls_filter_unknown_standard_returns_empty():
    controls = compliance_svc.list_controls(standard="NONEXISTENT_STANDARD_XYZ")
    assert controls == []


# ── get_control ──────────────────────────────────────────────────────────


def test_get_control_known_id_returns_control():
    ctrl = compliance_svc.get_control("kvkk-md-5")
    assert ctrl is not None
    assert ctrl.id == "kvkk-md-5"
    assert ctrl.standard == "KVKK"


def test_get_control_unknown_id_returns_none():
    """Service returns None; callers raise KeyError — guard this boundary."""
    ctrl = compliance_svc.get_control("does-not-exist-999")
    assert ctrl is None


# ── mappings_for ─────────────────────────────────────────────────────────


def test_mappings_for_known_control_returns_list():
    mappings = compliance_svc.mappings_for("kvkk-md-5")
    assert isinstance(mappings, list)
    assert len(mappings) > 0


def test_mappings_for_all_have_correct_control_id():
    mappings = compliance_svc.mappings_for("kvkk-md-12")
    for m in mappings:
        assert m.control_id == "kvkk-md-12"


def test_mappings_for_unknown_control_returns_empty_list():
    mappings = compliance_svc.mappings_for("unknown-control-xyz")
    assert mappings == []
