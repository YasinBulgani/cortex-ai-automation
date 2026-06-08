"""Pure unit tests for design service helper functions.

These tests exercise the deterministic fallback functions and schema helpers
that have no DB/network dependencies.  They run in <1 second and are safe
for local development on any Python version supported by the project.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.test_management.design_service import (
        _fallback_bva,
        _fallback_dt,
        _fallback_pairwise,
    )
    from app.domains.test_management.schemas import (
        DesignFieldSpec,
        DtRunCreate,
        PairwiseRunCreate,
    )

    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="design service import failed")


# ── DtRunCreate.effective_fields() ───────────────────────────────────────────


class TestDtRunCreateEffectiveFields:
    def test_uses_fields_when_provided(self) -> None:
        spec = DesignFieldSpec(name="Cond", data_type="bool")
        dt = DtRunCreate(fields=[spec])
        result = dt.effective_fields()
        assert len(result) == 1
        assert result[0].name == "Cond"

    def test_converts_conditions_to_bool_fields(self) -> None:
        dt = DtRunCreate(conditions=["IsLoggedIn", "HasPermission"])
        result = dt.effective_fields()
        assert len(result) == 2
        assert all(f.data_type == "bool" for f in result)
        names = {f.name for f in result}
        assert names == {"IsLoggedIn", "HasPermission"}

    def test_strips_whitespace_from_conditions(self) -> None:
        dt = DtRunCreate(conditions=["  Cond1  ", " Cond2"])
        result = dt.effective_fields()
        assert {f.name for f in result} == {"Cond1", "Cond2"}

    def test_raises_when_no_fields_or_conditions(self) -> None:
        dt = DtRunCreate()
        with pytest.raises(ValueError, match="condition"):
            dt.effective_fields()

    def test_ignores_empty_conditions(self) -> None:
        dt = DtRunCreate(conditions=["", "  ", "RealCond"])
        result = dt.effective_fields()
        assert len(result) == 1
        assert result[0].name == "RealCond"

    def test_fields_takes_precedence_over_conditions(self) -> None:
        spec = DesignFieldSpec(name="FieldCond", data_type="int", min_value="0", max_value="10")
        dt = DtRunCreate(fields=[spec], conditions=["AlsoThis"])
        result = dt.effective_fields()
        # fields wins — conditions ignored
        assert len(result) == 1
        assert result[0].name == "FieldCond"
        assert result[0].data_type == "int"


# ── _fallback_dt ─────────────────────────────────────────────────────────────


class TestFallbackDt:
    def test_returns_nonempty_list_for_two_conditions(self) -> None:
        fields = [DesignFieldSpec(name="A", data_type="bool"), DesignFieldSpec(name="B", data_type="bool")]
        drafts = _fallback_dt(fields)
        assert len(drafts) >= 1

    def test_each_row_has_both_conditions_in_inputs(self) -> None:
        fields = [DesignFieldSpec(name="X", data_type="bool"), DesignFieldSpec(name="Y", data_type="bool")]
        drafts = _fallback_dt(fields)
        for d in drafts:
            assert "X" in d.inputs
            assert "Y" in d.inputs

    def test_all_true_row_has_primary_action(self) -> None:
        fields = [DesignFieldSpec(name="C1", data_type="bool"), DesignFieldSpec(name="C2", data_type="bool")]
        drafts = _fallback_dt(fields)
        all_true_rows = [d for d in drafts if d.inputs.get("C1") is True and d.inputs.get("C2") is True]
        assert all_true_rows
        assert all_true_rows[0].expected == "action_A"

    def test_cap_at_16_for_large_input(self) -> None:
        fields = [DesignFieldSpec(name=f"Cond{i}", data_type="bool") for i in range(10)]
        drafts = _fallback_dt(fields)
        assert len(drafts) <= 16

    def test_boundary_type_is_decision_row(self) -> None:
        fields = [DesignFieldSpec(name="A", data_type="bool"), DesignFieldSpec(name="B", data_type="bool")]
        assert all(d.boundary_type == "decision_row" for d in _fallback_dt(fields))

    def test_deterministic_output(self) -> None:
        fields = [DesignFieldSpec(name="P", data_type="bool"), DesignFieldSpec(name="Q", data_type="bool")]
        assert [d.model_dump() for d in _fallback_dt(fields)] == [d.model_dump() for d in _fallback_dt(fields)]


# ── _fallback_pairwise ───────────────────────────────────────────────────────


class TestFallbackPairwise:
    def test_two_binary_params_cover_four_pairs(self) -> None:
        fields = [
            DesignFieldSpec(name="A", data_type="enum", allowed_set=["a1", "a2"]),
            DesignFieldSpec(name="B", data_type="enum", allowed_set=["b1", "b2"]),
        ]
        drafts = _fallback_pairwise(fields)
        covered = {(d.inputs.get("A"), d.inputs.get("B")) for d in drafts}
        assert ("a1", "b1") in covered
        assert ("a1", "b2") in covered
        assert ("a2", "b1") in covered
        assert ("a2", "b2") in covered

    def test_each_row_contains_all_fields(self) -> None:
        fields = [
            DesignFieldSpec(name="F1", data_type="enum", allowed_set=["v1", "v2"]),
            DesignFieldSpec(name="F2", data_type="enum", allowed_set=["v3", "v4"]),
            DesignFieldSpec(name="F3", data_type="enum", allowed_set=["v5", "v6"]),
        ]
        drafts = _fallback_pairwise(fields)
        for d in drafts:
            assert "F1" in d.inputs
            assert "F2" in d.inputs
            assert "F3" in d.inputs

    def test_safety_cap_200(self) -> None:
        fields = [
            DesignFieldSpec(name=f"P{i}", data_type="enum", allowed_set=[f"v{i}_{j}" for j in range(6)])
            for i in range(8)
        ]
        assert len(_fallback_pairwise(fields)) <= 200

    def test_bool_fields_use_true_false(self) -> None:
        fields = [DesignFieldSpec(name="Flag", data_type="bool"), DesignFieldSpec(name="Active", data_type="bool")]
        drafts = _fallback_pairwise(fields)
        all_vals = {d.inputs.get("Flag") for d in drafts}
        assert True in all_vals and False in all_vals

    def test_int_fields_produce_numeric_values(self) -> None:
        fields = [
            DesignFieldSpec(name="Age", data_type="int", min_value="18", max_value="65"),
            DesignFieldSpec(name="Level", data_type="int", min_value="1", max_value="10"),
        ]
        drafts = _fallback_pairwise(fields)
        for d in drafts:
            assert isinstance(d.inputs.get("Age"), (int, float))
            assert isinstance(d.inputs.get("Level"), (int, float))

    def test_boundary_type_is_pairwise_row(self) -> None:
        fields = [
            DesignFieldSpec(name="X", data_type="enum", allowed_set=["x1", "x2"]),
            DesignFieldSpec(name="Y", data_type="enum", allowed_set=["y1", "y2"]),
        ]
        assert all(d.boundary_type == "pairwise_row" for d in _fallback_pairwise(fields))

    def test_empty_allowed_set_uses_default_values(self) -> None:
        fields = [
            DesignFieldSpec(name="StrField", data_type="string"),
            DesignFieldSpec(name="NumField", data_type="int", min_value="0", max_value="10"),
        ]
        drafts = _fallback_pairwise(fields)
        assert len(drafts) >= 1
        for d in drafts:
            assert "StrField" in d.inputs
            assert "NumField" in d.inputs
