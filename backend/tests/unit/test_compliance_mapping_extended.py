"""Unit tests for the compliance mapping module.

Tests app/domains/compliance/mapping.py — pure in-memory data + query API.
Covers: Control/Mapping data integrity, query functions, evidence pack.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.compliance.mapping import (
    CONTROLS,
    MAPPINGS,
    Control,
    Mapping,
    all_markers,
    build_evidence_pack,
    controls_for_feature,
    export_evidence,
    get_control,
    list_controls,
    mappings_for,
    unmapped_controls,
)


# ── Data integrity ────────────────────────────────────────────────────────────


class TestControlsDataIntegrity:
    def test_controls_not_empty(self) -> None:
        assert len(CONTROLS) > 0

    def test_all_control_ids_unique(self) -> None:
        ids = [c.id for c in CONTROLS]
        assert len(ids) == len(set(ids)), "Duplicate control IDs found"

    def test_all_controls_have_required_fields(self) -> None:
        for c in CONTROLS:
            assert c.id, f"Control missing id: {c}"
            assert c.standard, f"Control missing standard: {c.id}"
            assert c.article, f"Control missing article: {c.id}"
            assert c.title, f"Control missing title: {c.id}"
            assert c.description, f"Control missing description: {c.id}"

    def test_risk_levels_are_valid(self) -> None:
        valid_levels = {"low", "medium", "high", "critical"}
        for c in CONTROLS:
            assert c.risk_level in valid_levels, f"{c.id} has invalid risk_level: {c.risk_level}"

    def test_standards_are_known(self) -> None:
        known_standards = {"KVKK", "BDDK", "ISO27001", "SOC2", "GDPR"}
        for c in CONTROLS:
            assert c.standard in known_standards, f"Unknown standard: {c.standard}"

    def test_at_least_one_kvkk_control(self) -> None:
        kvkk = [c for c in CONTROLS if c.standard == "KVKK"]
        assert len(kvkk) >= 1

    def test_control_is_frozen(self) -> None:
        c = CONTROLS[0]
        with pytest.raises((TypeError, AttributeError)):
            c.id = "modified"  # type: ignore[misc]


class TestMappingsDataIntegrity:
    def test_mappings_not_empty(self) -> None:
        assert len(MAPPINGS) > 0

    def test_all_mapping_control_ids_reference_valid_controls(self) -> None:
        control_ids = {c.id for c in CONTROLS}
        for m in MAPPINGS:
            assert m.control_id in control_ids, f"Mapping references unknown control: {m.control_id}"

    def test_all_mappings_have_feature_name(self) -> None:
        for m in MAPPINGS:
            assert m.feature_name, f"Mapping for {m.control_id} missing feature_name"

    def test_all_mappings_have_test_marker(self) -> None:
        for m in MAPPINGS:
            assert m.test_marker, f"Mapping for {m.control_id} missing test_marker"

    def test_mapping_is_frozen(self) -> None:
        m = MAPPINGS[0]
        with pytest.raises((TypeError, AttributeError)):
            m.control_id = "modified"  # type: ignore[misc]


# ── get_control ───────────────────────────────────────────────────────────────


class TestGetControl:
    def test_returns_control_by_id(self) -> None:
        # Use the first real control ID
        first_id = CONTROLS[0].id
        result = get_control(first_id)
        assert result is not None
        assert result.id == first_id

    def test_returns_none_for_unknown_id(self) -> None:
        assert get_control("does-not-exist-xyz") is None

    def test_all_controls_retrievable(self) -> None:
        for c in CONTROLS:
            found = get_control(c.id)
            assert found is not None
            assert found is c


# ── list_controls ─────────────────────────────────────────────────────────────


class TestListControls:
    def test_no_filter_returns_all(self) -> None:
        result = list_controls()
        assert len(result) == len(CONTROLS)

    def test_filter_by_kvkk(self) -> None:
        kvkk_controls = list_controls(standard="KVKK")
        assert all(c.standard == "KVKK" for c in kvkk_controls)

    def test_filter_case_insensitive(self) -> None:
        lower = list_controls(standard="kvkk")
        upper = list_controls(standard="KVKK")
        assert len(lower) == len(upper)

    def test_unknown_standard_returns_empty(self) -> None:
        result = list_controls(standard="NONEXISTENT")
        assert result == []

    def test_returns_list_not_tuple(self) -> None:
        result = list_controls()
        assert isinstance(result, list)


# ── mappings_for ──────────────────────────────────────────────────────────────


class TestMappingsFor:
    def test_returns_list(self) -> None:
        first_control = CONTROLS[0]
        result = mappings_for(first_control.id)
        assert isinstance(result, list)

    def test_unknown_control_returns_empty(self) -> None:
        assert mappings_for("unknown-control-id") == []

    def test_all_returned_mappings_match_control_id(self) -> None:
        for c in CONTROLS:
            mappings = mappings_for(c.id)
            for m in mappings:
                assert m.control_id == c.id


# ── controls_for_feature ──────────────────────────────────────────────────────


class TestControlsForFeature:
    def test_known_feature_returns_controls(self) -> None:
        if not MAPPINGS:
            pytest.skip("No mappings defined")
        feature = MAPPINGS[0].feature_name
        result = controls_for_feature(feature)
        assert len(result) >= 1
        for c in result:
            # Verify the feature is indeed mapped to this control
            mapped_controls = {m.control_id for m in MAPPINGS if m.feature_name == feature}
            assert c.id in mapped_controls

    def test_unknown_feature_returns_empty(self) -> None:
        assert controls_for_feature("nonexistent.feature.xyz") == []


# ── unmapped_controls ─────────────────────────────────────────────────────────


class TestUnmappedControls:
    def test_returns_list(self) -> None:
        assert isinstance(unmapped_controls(), list)

    def test_unmapped_are_not_in_mappings(self) -> None:
        mapped_ids = {m.control_id for m in MAPPINGS}
        for c in unmapped_controls():
            assert c.id not in mapped_ids

    def test_unmapped_plus_mapped_equals_all_controls(self) -> None:
        mapped_ids = {m.control_id for m in MAPPINGS}
        mapped_controls = [c for c in CONTROLS if c.id in mapped_ids]
        unmapped = unmapped_controls()
        assert len(mapped_controls) + len(unmapped) == len(CONTROLS)


# ── all_markers ───────────────────────────────────────────────────────────────


class TestAllMarkers:
    def test_returns_list_of_strings(self) -> None:
        markers = all_markers()
        assert isinstance(markers, list)
        assert all(isinstance(m, str) for m in markers)

    def test_markers_have_compliance_prefix(self) -> None:
        for marker in all_markers():
            assert marker.startswith("compliance:"), f"Unexpected marker format: {marker}"

    def test_markers_are_sorted(self) -> None:
        markers = all_markers()
        assert markers == sorted(markers)

    def test_markers_are_unique(self) -> None:
        markers = all_markers()
        assert len(markers) == len(set(markers))

    def test_at_least_one_marker(self) -> None:
        if not MAPPINGS:
            pytest.skip("No mappings defined")
        assert len(all_markers()) >= 1


# ── build_evidence_pack ───────────────────────────────────────────────────────


class TestBuildEvidencePack:
    def test_returns_dict_with_required_keys(self) -> None:
        pack = build_evidence_pack()
        assert "controls" in pack
        assert "mappings" in pack
        assert "unmapped" in pack
        assert "coverage_pct" in pack
        assert "generated_standards" in pack

    def test_controls_serialised_as_list_of_dicts(self) -> None:
        pack = build_evidence_pack()
        assert isinstance(pack["controls"], list)
        if pack["controls"]:
            assert isinstance(pack["controls"][0], dict)
            assert "id" in pack["controls"][0]

    def test_coverage_pct_is_float_in_range(self) -> None:
        pack = build_evidence_pack()
        pct = pack["coverage_pct"]
        assert isinstance(pct, float)
        assert 0.0 <= pct <= 100.0

    def test_coverage_pct_correct(self) -> None:
        pack = build_evidence_pack()
        n_unmapped = len(unmapped_controls())
        n_total = len(CONTROLS)
        expected = round(100.0 * (1 - n_unmapped / max(1, n_total)), 2)
        assert pack["coverage_pct"] == expected

    def test_standards_list_sorted(self) -> None:
        pack = build_evidence_pack()
        stds = pack["generated_standards"]
        assert stds == sorted(stds)

    def test_pack_is_json_serialisable(self) -> None:
        pack = build_evidence_pack()
        # Should not raise
        text = json.dumps(pack, ensure_ascii=False)
        assert len(text) > 10


# ── export_evidence ───────────────────────────────────────────────────────────


class TestExportEvidence:
    def test_creates_file(self, tmp_path: Path) -> None:
        target = tmp_path / "evidence" / "compliance.json"
        export_evidence(target)
        assert target.exists()

    def test_file_contains_valid_json(self, tmp_path: Path) -> None:
        target = tmp_path / "out.json"
        export_evidence(target)
        data = json.loads(target.read_text(encoding="utf-8"))
        assert "controls" in data
        assert "coverage_pct" in data

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        target = tmp_path / "a" / "b" / "c" / "evidence.json"
        export_evidence(target)
        assert target.exists()
