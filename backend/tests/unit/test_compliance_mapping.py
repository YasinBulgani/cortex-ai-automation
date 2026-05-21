"""Compliance mapping — veri bütünlüğü + CLI davranış testleri."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.compliance.mapping import (
    CONTROLS,
    MAPPINGS,
    all_markers,
    build_evidence_pack,
    controls_for_feature,
    export_evidence,
    get_control,
    list_controls,
    mappings_for,
    unmapped_controls,
)


# ── Veri bütünlüğü ──────────────────────────────────────────────────────


def test_all_mappings_reference_existing_control() -> None:
    control_ids = {c.id for c in CONTROLS}
    orphans = [m for m in MAPPINGS if m.control_id not in control_ids]
    assert orphans == [], f"Orphan mapping'ler: {orphans}"


def test_no_duplicate_controls() -> None:
    ids = [c.id for c in CONTROLS]
    assert len(ids) == len(set(ids)), "Duplicate control.id"


def test_all_risk_levels_valid() -> None:
    valid = {"low", "medium", "high", "critical"}
    for c in CONTROLS:
        assert c.risk_level in valid, f"{c.id}: bilinmeyen risk_level"


def test_feature_modules_exist() -> None:
    repo = Path(__file__).resolve().parents[3]  # backend/tests/unit/ → ../../..
    # Dosya ya da dizin — mapping.feature_module iki tipi de destekliyor
    for m in MAPPINGS:
        path = repo / m.feature_module
        assert path.exists(), f"{m.control_id}: feature yolu yok: {path}"


def test_test_locations_exist() -> None:
    repo = Path(__file__).resolve().parents[3]
    for m in MAPPINGS:
        path = repo / m.test_location
        assert path.exists(), f"{m.control_id}: test yolu yok: {path}"


# ── Query API ────────────────────────────────────────────────────────────


class TestQueries:
    def test_get_control_found(self) -> None:
        c = get_control("kvkk-md-12")
        assert c is not None
        assert c.standard == "KVKK"

    def test_get_control_missing(self) -> None:
        assert get_control("unknown") is None

    def test_list_controls_by_standard(self) -> None:
        kvkks = list_controls("KVKK")
        assert len(kvkks) >= 3
        assert all(c.standard == "KVKK" for c in kvkks)
        assert list_controls("BDDK") and list_controls("ISO27001")

    def test_mappings_for_audit(self) -> None:
        ms = mappings_for("kvkk-md-12")
        # audit_hash_chain + prompt_shield bekleniyor (kvkk-md-12 için iki mapping)
        assert len(ms) >= 1
        features = {m.feature_name for m in ms}
        assert "audit_hash_chain" in features

    def test_controls_for_feature(self) -> None:
        cs = controls_for_feature("audit_hash_chain")
        ids = {c.id for c in cs}
        assert "kvkk-md-12" in ids
        assert "bddk-bgy-6" in ids

    def test_all_markers_formatted(self) -> None:
        markers = all_markers()
        assert markers, "marker listesi boş"
        assert all(m.startswith("compliance:") for m in markers)


# ── Evidence pack ────────────────────────────────────────────────────────


class TestEvidencePack:
    def test_build_pack_structure(self) -> None:
        pack = build_evidence_pack()
        assert "controls" in pack
        assert "mappings" in pack
        assert "unmapped" in pack
        assert "coverage_pct" in pack
        # 0-100 arası yüzde
        assert 0 <= pack["coverage_pct"] <= 100

    def test_pack_json_serializable(self) -> None:
        pack = build_evidence_pack()
        s = json.dumps(pack, ensure_ascii=False)
        assert len(s) > 100

    def test_export_writes_file(self, tmp_path: Path) -> None:
        target = tmp_path / "sub" / "pack.json"
        out = export_evidence(target)
        assert out == target
        assert target.exists()
        data = json.loads(target.read_text(encoding="utf-8"))
        assert "controls" in data


# ── Coverage ─────────────────────────────────────────────────────────────


def test_coverage_above_threshold() -> None:
    """Eklenen her kontrol için mapping zorunlu (unmapped coverage gap).

    Şu an eklediğimiz tüm kontrollerin mapping'i olmalı. Yeni kontrol
    eklenip mapping unutulursa bu test kırılır.
    """
    unmapped = unmapped_controls()
    assert unmapped == [], f"Mapping'i eksik kontroller: {[c.id for c in unmapped]}"
