"""Tests for M-1 (BVA) + M-2 (Equivalence) + M-9 (Parameterized Cases).

These exercise ``design_service`` directly (and a few router-level integration
paths) against the real dev Postgres DB. External I/O (the LLM gateway) is
patched at ``comments_service._call_llm`` — the service module imports the
symbol once, so patching the *origin* attribute makes the design service see
the patched version.
"""
from __future__ import annotations

import uuid as _uuid

import pytest

from app.domains.test_management import design_service
from app.domains.test_management import comments_service
from app.domains.test_management.models import (
    MgmtCaseDataRow,
    MgmtCaseParamSet,
    MgmtDesignTechniqueRun,
    TestManagementAuditEvent,
)
from app.domains.test_management.schemas import (
    ALLOWED_DATA_TYPES,
    ALLOWED_TECHNIQUES,
    BvaRunCreate,
    CaseDataGenerateRequest,
    CaseDataRowIn,
    CaseParamSetCreate,
    DesignFieldSpec,
    EqRunCreate,
    PromoteCasesRequest,
)
from sqlalchemy import select


# Ensure every test patches the LLM gateway by default so we never hit network.
@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    monkeypatch.setattr(comments_service, "_call_llm", lambda *a, **k: None)
    # design_service imports the bound symbol — patch there too.
    monkeypatch.setattr(design_service, "_call_llm", lambda *a, **k: None)


# ── Pure helpers (no DB) ─────────────────────────────────────────────────────


class TestBvaFallback:
    def test_deterministic_repeat_for_int(self) -> None:
        field = DesignFieldSpec(name="age", data_type="int", min_value="0", max_value="120")
        a = design_service._fallback_bva([field])
        b = design_service._fallback_bva([field])
        # Same input → same output (model_dump for determinism).
        assert [c.model_dump() for c in a] == [c.model_dump() for c in b]

    def test_int_field_produces_boundary_set(self) -> None:
        field = DesignFieldSpec(name="age", data_type="int", min_value="0", max_value="120")
        drafts = design_service._fallback_bva([field])
        boundary_types = {d.boundary_type for d in drafts}
        # min, just_inside, just_outside, max, nominal must all appear.
        for needed in ("min", "just_inside", "just_outside", "max", "nominal"):
            assert needed in boundary_types, f"missing {needed}: {boundary_types}"

    def test_string_nullable_yields_empty_accepted(self) -> None:
        field = DesignFieldSpec(
            name="nick",
            data_type="string",
            min_value="0",
            max_value="8",
            nullable=True,
        )
        drafts = design_service._fallback_bva([field])
        empty = [d for d in drafts if d.inputs.get("nick") == ""]
        assert empty and empty[0].expected == "accepted"

    def test_string_required_yields_empty_rejected(self) -> None:
        field = DesignFieldSpec(
            name="nick", data_type="string", min_value="1", max_value="8", nullable=False
        )
        drafts = design_service._fallback_bva([field])
        empty = [d for d in drafts if d.inputs.get("nick") == ""]
        assert empty and "rejected" in empty[0].expected

    def test_enum_includes_invalid_marker(self) -> None:
        field = DesignFieldSpec(
            name="state", data_type="enum", allowed_set=["new", "open", "closed"]
        )
        drafts = design_service._fallback_bva([field])
        values = [d.inputs.get("state") for d in drafts]
        for allowed in ("new", "open", "closed"):
            assert allowed in values
        assert "__INVALID__" in values

    def test_bool_field_covers_true_false_plus_invalid(self) -> None:
        field = DesignFieldSpec(name="flag", data_type="bool")
        drafts = design_service._fallback_bva([field])
        values = [d.inputs.get("flag") for d in drafts]
        assert True in values and False in values
        assert "__INVALID__" in values

    def test_date_field_emits_min_max_and_invalid(self) -> None:
        field = DesignFieldSpec(
            name="dob", data_type="date", min_value="2000-01-01", max_value="2025-12-31"
        )
        drafts = design_service._fallback_bva([field])
        values = [d.inputs.get("dob") for d in drafts]
        assert "2000-01-01" in values
        assert "2025-12-31" in values
        assert "9999-13-99" in values


class TestEqFallback:
    def test_int_field_has_valid_plus_two_invalid(self) -> None:
        field = DesignFieldSpec(name="age", data_type="int", min_value="0", max_value="120")
        parts, cases = design_service._fallback_eq([field])
        valids = [p for p in parts if p["is_valid"]]
        invalids = [p for p in parts if not p["is_valid"]]
        assert len(valids) >= 1
        assert len(invalids) >= 2  # below min + above max
        # Cases pair with partitions 1:1.
        assert len(cases) == len(parts)

    def test_nullable_emits_null_partition(self) -> None:
        field = DesignFieldSpec(
            name="weight", data_type="float", min_value="0", max_value="500", nullable=True
        )
        parts, _ = design_service._fallback_eq([field])
        assert any(p["partition_label"] == "null" for p in parts)

    def test_enum_partitions_one_per_allowed_plus_invalid(self) -> None:
        field = DesignFieldSpec(
            name="state", data_type="enum", allowed_set=["a", "b", "c"]
        )
        parts, cases = design_service._fallback_eq([field])
        valid_labels = {p["partition_label"] for p in parts if p["is_valid"]}
        assert len(valid_labels) == 3
        assert any(p["partition_label"] == "not in allowed_set" for p in parts)
        # Every partition has at least one case.
        for part in parts:
            assert any(c.partition_label == part["partition_label"] for c in cases)

    def test_string_required_yields_empty_invalid(self) -> None:
        field = DesignFieldSpec(name="t", data_type="string", min_value="1", max_value="8")
        parts, _ = design_service._fallback_eq([field])
        labels = {p["partition_label"] for p in parts}
        assert "empty (required)" in labels


# ── DB-backed runs ───────────────────────────────────────────────────────────


def _user(seeded_users, make_user, alias="alice"):
    return make_user(seeded_users[alias], "00000000-0000-0000-0000-000000000001")


class TestBvaRunCreate:
    def test_happy_path_persists_run_and_audit(
        self, db_session, seeded_users, make_user, design_project
    ) -> None:
        user = _user(seeded_users, make_user)
        payload = BvaRunCreate(
            project_id=design_project,
            fields=[DesignFieldSpec(name="age", data_type="int", min_value="0", max_value="120")],
            requirement_text="Age must be 0..120",
        )
        run = design_service.create_bva_run(db_session, user.tenant_id, user, payload)

        assert run.technique == "BVA"
        assert run.source == "fallback"  # LLM patched to return None
        assert run.generated_cases, "must produce some generated drafts"
        assert run.project_id == design_project

        # Audit row exists.
        events = db_session.execute(
            select(TestManagementAuditEvent).where(
                TestManagementAuditEvent.entity_id == run.id,
                TestManagementAuditEvent.action == "design.run.create",
            )
        ).scalars().all()
        assert events, "design.run.create audit event missing"

    def test_requirement_id_round_trips(
        self, db_session, seeded_users, make_user, design_project
    ) -> None:
        from sqlalchemy import text

        user = _user(seeded_users, make_user)
        req_id = str(_uuid.uuid4())
        db_session.execute(
            text(
                "INSERT INTO test_management_requirements (id, project_id, title) "
                "VALUES (:id, :pid, 'r')"
            ),
            {"id": req_id, "pid": design_project},
        )
        db_session.commit()
        try:
            payload = BvaRunCreate(
                project_id=design_project,
                requirement_id=req_id,
                fields=[DesignFieldSpec(name="x", data_type="int", min_value="0", max_value="9")],
            )
            run = design_service.create_bva_run(db_session, user.tenant_id, user, payload)
            assert run.requirement_id == req_id
        finally:
            db_session.execute(
                text("DELETE FROM test_management_requirements WHERE id = :id"),
                {"id": req_id},
            )
            db_session.commit()

    def test_empty_fields_rejected_at_schema_layer(self) -> None:
        # Pydantic validation blocks fields=[] before the service even runs.
        with pytest.raises(Exception):
            BvaRunCreate(fields=[])

    def test_invalid_data_type_rejected(self) -> None:
        with pytest.raises(Exception):
            DesignFieldSpec(name="x", data_type="blob")
        assert "blob" not in ALLOWED_DATA_TYPES


class TestEqRunCreate:
    def test_eq_run_records_partitions(
        self, db_session, seeded_users, make_user, design_project
    ) -> None:
        user = _user(seeded_users, make_user)
        payload = EqRunCreate(
            project_id=design_project,
            fields=[
                DesignFieldSpec(name="state", data_type="enum", allowed_set=["a", "b"])
            ],
        )
        run = design_service.create_eq_run(db_session, user.tenant_id, user, payload)
        assert run.technique == "EQ"
        assert len(run.partitions) >= 2  # at least one valid + invalid
        labels = {p.partition_label for p in run.partitions}
        assert any("allowed" in l for l in labels)
        assert "not in allowed_set" in labels


class TestListAndGetRuns:
    def test_filter_by_technique_and_tenant_isolation(
        self, db_session, seeded_users, make_user, design_project
    ) -> None:
        alice = _user(seeded_users, make_user, "alice")
        eve = _user(seeded_users, make_user, "eve")
        eve.tenant_id = "00000000-0000-0000-0000-0000000000b2"

        f = DesignFieldSpec(name="x", data_type="int", min_value="0", max_value="9")
        # Alice creates BVA and EQ.
        design_service.create_bva_run(
            db_session, alice.tenant_id, alice,
            BvaRunCreate(project_id=design_project, fields=[f]),
        )
        design_service.create_eq_run(
            db_session, alice.tenant_id, alice,
            EqRunCreate(project_id=design_project, fields=[f]),
        )
        # Eve creates a BVA in a different tenant (no project_id needed).
        design_service.create_bva_run(
            db_session, eve.tenant_id, eve, BvaRunCreate(fields=[f]),
        )

        alice_bva = design_service.list_design_runs(
            db_session, alice.tenant_id, technique="BVA"
        )
        assert all(r.technique == "BVA" for r in alice_bva)
        assert all(r.tenant_id == alice.tenant_id for r in alice_bva)

        alice_eq = design_service.list_design_runs(
            db_session, alice.tenant_id, technique="EQ"
        )
        assert all(r.technique == "EQ" for r in alice_eq)

        # Eve sees only her own.
        eve_runs = design_service.list_design_runs(db_session, eve.tenant_id)
        assert all(r.tenant_id == eve.tenant_id for r in eve_runs)
        assert all(r.tenant_id != alice.tenant_id for r in eve_runs)

    def test_get_run_404_for_other_tenant(
        self, db_session, seeded_users, make_user, design_project
    ) -> None:
        alice = _user(seeded_users, make_user)
        run = design_service.create_bva_run(
            db_session, alice.tenant_id, alice,
            BvaRunCreate(
                project_id=design_project,
                fields=[DesignFieldSpec(name="x", data_type="int", min_value="0", max_value="9")],
            ),
        )
        with pytest.raises(KeyError):
            design_service.get_design_run(
                db_session, "00000000-0000-0000-0000-0000000000b2", run.id
            )

    def test_list_limit(
        self, db_session, seeded_users, make_user, design_project
    ) -> None:
        alice = _user(seeded_users, make_user)
        f = DesignFieldSpec(name="x", data_type="int", min_value="0", max_value="9")
        for _ in range(3):
            design_service.create_bva_run(
                db_session, alice.tenant_id, alice,
                BvaRunCreate(project_id=design_project, fields=[f]),
            )
        runs = design_service.list_design_runs(db_session, alice.tenant_id, limit=2)
        assert len(runs) <= 2

    def test_invalid_technique_filter_rejected(
        self, db_session, seeded_users, make_user
    ) -> None:
        alice = _user(seeded_users, make_user)
        with pytest.raises(ValueError):
            design_service.list_design_runs(
                db_session, alice.tenant_id, technique="NOPE"
            )


class TestPromoteCases:
    def test_promote_calls_tm_service_and_audits(
        self, db_session, seeded_users, make_user, design_project, monkeypatch
    ) -> None:
        alice = _user(seeded_users, make_user)
        run = design_service.create_bva_run(
            db_session, alice.tenant_id, alice,
            BvaRunCreate(
                project_id=design_project,
                fields=[DesignFieldSpec(name="x", data_type="int", min_value="0", max_value="9")],
            ),
        )

        # Avoid the heavy create_case path (it needs suites/folders/versions).
        created = []

        def _fake_create_case(db, project_id, payload, user):
            class _Stub:
                id = _uuid.uuid4().hex
            stub = _Stub()
            created.append((project_id, payload.title))
            return stub

        monkeypatch.setattr(design_service.tm_service, "create_case", _fake_create_case)

        ids = design_service.promote_cases(
            db_session, alice.tenant_id, alice, run.id,
            PromoteCasesRequest(case_indexes=[0, 1]),
        )
        assert len(ids) == 2
        assert len(created) == 2

        events = db_session.execute(
            select(TestManagementAuditEvent).where(
                TestManagementAuditEvent.entity_id == run.id,
                TestManagementAuditEvent.action == "design.run.promote",
            )
        ).scalars().all()
        assert events

    def test_promote_out_of_range_raises(
        self, db_session, seeded_users, make_user, design_project, monkeypatch
    ) -> None:
        alice = _user(seeded_users, make_user)
        run = design_service.create_bva_run(
            db_session, alice.tenant_id, alice,
            BvaRunCreate(
                project_id=design_project,
                fields=[DesignFieldSpec(name="x", data_type="int", min_value="0", max_value="9")],
            ),
        )
        monkeypatch.setattr(
            design_service.tm_service, "create_case",
            lambda *a, **k: type("S", (), {"id": _uuid.uuid4().hex})(),
        )
        with pytest.raises(ValueError):
            design_service.promote_cases(
                db_session, alice.tenant_id, alice, run.id,
                PromoteCasesRequest(case_indexes=[9999]),
            )

    def test_promote_requires_project(
        self, db_session, seeded_users, make_user
    ) -> None:
        alice = _user(seeded_users, make_user)
        run = design_service.create_bva_run(
            db_session, alice.tenant_id, alice,
            BvaRunCreate(
                fields=[DesignFieldSpec(name="x", data_type="int", min_value="0", max_value="9")],
            ),
        )
        with pytest.raises(ValueError):
            design_service.promote_cases(
                db_session, alice.tenant_id, alice, run.id,
                PromoteCasesRequest(case_indexes=[0]),
            )


# ── M-9 Parameterized cases ──────────────────────────────────────────────────


class TestParamSetCRUD:
    def test_create_and_list(
        self, db_session, seeded_users, make_user, design_case
    ) -> None:
        alice = _user(seeded_users, make_user)
        payload = CaseParamSetCreate(
            case_id=design_case,
            schema_json={"fields": [{"name": "age", "type": "int", "required": True}]},
        )
        ps = design_service.create_param_set(db_session, alice.tenant_id, alice, payload)
        assert ps.case_id == design_case
        assert ps.schema_json["fields"][0]["name"] == "age"

        sets = design_service.list_param_sets(db_session, alice.tenant_id, design_case)
        assert any(s.id == ps.id for s in sets)

    def test_missing_fields_list_rejected(
        self, db_session, seeded_users, make_user, design_case
    ) -> None:
        alice = _user(seeded_users, make_user)
        with pytest.raises(ValueError):
            design_service.create_param_set(
                db_session, alice.tenant_id, alice,
                CaseParamSetCreate(case_id=design_case, schema_json={"foo": "bar"}),
            )

    def test_field_without_name_rejected(
        self, db_session, seeded_users, make_user, design_case
    ) -> None:
        alice = _user(seeded_users, make_user)
        with pytest.raises(ValueError):
            design_service.create_param_set(
                db_session, alice.tenant_id, alice,
                CaseParamSetCreate(
                    case_id=design_case,
                    schema_json={"fields": [{"type": "int"}]},
                ),
            )


class TestDataRows:
    @pytest.fixture()
    def param_set(self, db_session, seeded_users, make_user, design_case):
        alice = _user(seeded_users, make_user)
        ps = design_service.create_param_set(
            db_session, alice.tenant_id, alice,
            CaseParamSetCreate(
                case_id=design_case,
                schema_json={"fields": [
                    {"name": "name", "type": "string", "required": True},
                    {"name": "age", "type": "int", "required": False},
                ]},
            ),
        )
        return ps, alice

    def test_llm_source_falls_back_to_deterministic_rows(
        self, db_session, param_set
    ) -> None:
        ps, alice = param_set
        rows = design_service.generate_data_rows(
            db_session, alice.tenant_id, alice,
            CaseDataGenerateRequest(param_set_id=ps.id, source="llm", count=3),
        )
        assert len(rows) == 3
        # Fallback marks source="llm" on the row (because requester asked) — values present.
        for r in rows:
            assert "name" in r.values

    def test_csv_source_parses_rows(self, db_session, param_set) -> None:
        ps, alice = param_set
        csv = "name,age\nAlice,30\nBob,25\n"
        rows = design_service.generate_data_rows(
            db_session, alice.tenant_id, alice,
            CaseDataGenerateRequest(param_set_id=ps.id, source="csv", csv_content=csv),
        )
        assert len(rows) == 2
        assert rows[0].values.get("name") == "Alice"
        assert rows[1].values.get("name") == "Bob"

    def test_csv_drops_unknown_columns(self, db_session, param_set) -> None:
        ps, alice = param_set
        csv = "name,age,extra\nAlice,30,xx\n"
        rows = design_service.generate_data_rows(
            db_session, alice.tenant_id, alice,
            CaseDataGenerateRequest(param_set_id=ps.id, source="csv", csv_content=csv),
        )
        assert len(rows) == 1
        assert "extra" not in rows[0].values

    def test_csv_without_content_rejected(self, db_session, param_set) -> None:
        ps, alice = param_set
        with pytest.raises(ValueError):
            design_service.generate_data_rows(
                db_session, alice.tenant_id, alice,
                CaseDataGenerateRequest(param_set_id=ps.id, source="csv", csv_content=None),
            )

    def test_invalid_source_rejected(self, db_session, param_set) -> None:
        ps, alice = param_set
        with pytest.raises(ValueError):
            design_service.generate_data_rows(
                db_session, alice.tenant_id, alice,
                CaseDataGenerateRequest(param_set_id=ps.id, source="grok"),
            )

    def test_manual_append_rows(self, db_session, param_set) -> None:
        ps, alice = param_set
        created = design_service.add_data_rows(
            db_session, alice.tenant_id, alice, ps.id,
            [CaseDataRowIn(values={"name": "X", "age": 1})],
        )
        assert len(created) == 1
        listed = design_service.list_data_rows(db_session, alice.tenant_id, ps.id)
        assert any(r.id == created[0].id for r in listed)

    def test_data_rows_other_tenant_404(self, db_session, param_set) -> None:
        ps, _alice = param_set
        with pytest.raises(KeyError):
            design_service.list_data_rows(
                db_session, "00000000-0000-0000-0000-0000000000b2", ps.id
            )


class TestExpandCase:
    def test_expand_returns_row_ids_and_is_idempotent(
        self, db_session, seeded_users, make_user, design_case
    ) -> None:
        alice = _user(seeded_users, make_user)
        ps = design_service.create_param_set(
            db_session, alice.tenant_id, alice,
            CaseParamSetCreate(
                case_id=design_case,
                schema_json={"fields": [{"name": "n", "type": "int", "required": True}]},
            ),
        )
        design_service.generate_data_rows(
            db_session, alice.tenant_id, alice,
            CaseDataGenerateRequest(param_set_id=ps.id, source="llm", count=2),
        )
        first = design_service.expand_case(db_session, alice.tenant_id, alice, design_case)
        second = design_service.expand_case(db_session, alice.tenant_id, alice, design_case)
        assert first["execution_ids"] == second["execution_ids"]
        assert len(first["execution_ids"]) == 2

        events = db_session.execute(
            select(TestManagementAuditEvent).where(
                TestManagementAuditEvent.entity_id == design_case,
                TestManagementAuditEvent.action == "design.params.expand",
            )
        ).scalars().all()
        assert len(events) >= 2

    def test_expand_unknown_case_raises(
        self, db_session, seeded_users, make_user
    ) -> None:
        alice = _user(seeded_users, make_user)
        with pytest.raises(KeyError):
            design_service.expand_case(
                db_session, alice.tenant_id, alice, _uuid.uuid4().hex
            )


# ── LLM gateway integration ──────────────────────────────────────────────────


class TestLLMFallback:
    def test_invalid_json_falls_back(
        self, db_session, seeded_users, make_user, design_project, monkeypatch
    ) -> None:
        # _call_llm returns None when JSON extraction fails — same as default.
        monkeypatch.setattr(design_service, "_call_llm", lambda *a, **k: None)
        alice = _user(seeded_users, make_user)
        run = design_service.create_bva_run(
            db_session, alice.tenant_id, alice,
            BvaRunCreate(
                project_id=design_project,
                fields=[DesignFieldSpec(name="x", data_type="int", min_value="0", max_value="9")],
            ),
        )
        assert run.source == "fallback"
        assert run.llm_trace_id is None

    def test_llm_branch_marks_source_llm(
        self, db_session, seeded_users, make_user, design_project, monkeypatch
    ) -> None:
        def _stub(*_a, **_k):
            return {
                "cases": [
                    {
                        "name": "AI: nominal",
                        "field_name": "x",
                        "boundary_type": "nominal",
                        "inputs": {"x": 5},
                        "expected": "accepted",
                        "rationale": "mid",
                    }
                ]
            }

        monkeypatch.setattr(design_service, "_call_llm", _stub)
        alice = _user(seeded_users, make_user)
        run = design_service.create_bva_run(
            db_session, alice.tenant_id, alice,
            BvaRunCreate(
                project_id=design_project,
                fields=[DesignFieldSpec(name="x", data_type="int", min_value="0", max_value="9")],
            ),
        )
        assert run.source == "llm"
        assert run.llm_trace_id  # hex string assigned
        assert any(c.name == "AI: nominal" for c in run.generated_cases)

    def test_eq_llm_branch_marks_source_llm(
        self, db_session, seeded_users, make_user, design_project, monkeypatch
    ) -> None:
        def _stub(*_a, **_k):
            return {
                "partitions": [
                    {"field_name": "x", "partition_label": "ok", "is_valid": True, "sample_value": "5"},
                ],
                "cases": [
                    {
                        "name": "AI: ok",
                        "field_name": "x",
                        "partition_label": "ok",
                        "inputs": {"x": 5},
                        "expected": "accepted",
                    }
                ],
            }

        monkeypatch.setattr(design_service, "_call_llm", _stub)
        alice = _user(seeded_users, make_user)
        run = design_service.create_eq_run(
            db_session, alice.tenant_id, alice,
            EqRunCreate(
                project_id=design_project,
                fields=[DesignFieldSpec(name="x", data_type="int", min_value="0", max_value="9")],
            ),
        )
        assert run.source == "llm"
        assert any(p.partition_label == "ok" for p in run.partitions)


# ── Module-level sanity ──────────────────────────────────────────────────────


class TestAllowedConstants:
    def test_techniques_constant_contains_bva_eq(self) -> None:
        assert {"BVA", "EQ"}.issubset(ALLOWED_TECHNIQUES)

    def test_data_types_constant_complete(self) -> None:
        assert {"int", "float", "string", "date", "bool", "enum"} == ALLOWED_DATA_TYPES
