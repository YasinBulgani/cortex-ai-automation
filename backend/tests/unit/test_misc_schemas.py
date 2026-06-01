"""Unit tests for misc pure Pydantic schema modules.

Tests are fully self-contained: no DB, no HTTP.
Covers:
  - onboarding.schemas: OnboardingStep (order bounds), OnboardingProgress
    (completion_pct bounds, is_fully_onboarded), ProgressUpdateRequest
  - dsl.schemas: DslParameter, DslImplementation, DslDeprecation, DslAction, DslStats
  - catalog.schema_v1: FieldType enum, FieldSpec, SchemaSnapshotV1
  - notifications.schemas: WSMessage
"""
from __future__ import annotations

import pytest

try:
    from app.domains.onboarding.schemas import (
        OnboardingStep,
        OnboardingProgress,
        ProgressUpdateRequest,
    )
    _ONBOARD_OK = True
except ImportError:
    _ONBOARD_OK = False

try:
    from app.domains.dsl.schemas import (
        DslParameter,
        DslImplementation,
        DslDeprecation,
        DslAction,
        DslStats,
    )
    _DSL_OK = True
except ImportError:
    _DSL_OK = False

try:
    from app.domains.catalog.schema_v1 import (
        FieldType,
        FieldSpec,
        SchemaSnapshotV1,
    )
    _CATALOG_OK = True
except ImportError:
    _CATALOG_OK = False

try:
    from app.domains.notifications.schemas import WSMessage
    _NOTIF_OK = True
except ImportError:
    _NOTIF_OK = False


# ---------------------------------------------------------------------------
# OnboardingStep
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ONBOARD_OK, reason="onboarding.schemas import failed")
class TestOnboardingStep:
    def test_creation(self):
        s = OnboardingStep(id="create_project", order=1, title="Create Project", description="desc")
        assert s.id == "create_project"
        assert s.order == 1

    def test_is_optional_default_false(self):
        s = OnboardingStep(id="x", order=1, title="t", description="d")
        assert s.is_optional is False

    def test_action_url_default_none(self):
        s = OnboardingStep(id="x", order=1, title="t", description="d")
        assert s.action_url is None

    def test_help_doc_default_none(self):
        s = OnboardingStep(id="x", order=1, title="t", description="d")
        assert s.help_doc is None

    def test_order_min_1(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OnboardingStep(id="x", order=0, title="t", description="d")

    def test_order_max_100(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OnboardingStep(id="x", order=101, title="t", description="d")

    def test_order_100_valid(self):
        s = OnboardingStep(id="x", order=100, title="t", description="d")
        assert s.order == 100

    def test_extra_fields_ignored(self):
        # model_config = extra="ignore"
        s = OnboardingStep(id="x", order=1, title="t", description="d", unknown_field="val")
        assert not hasattr(s, "unknown_field")


# ---------------------------------------------------------------------------
# OnboardingProgress
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ONBOARD_OK, reason="onboarding.schemas import failed")
class TestOnboardingProgress:
    def _make_progress(self, **kwargs):
        defaults = dict(
            project_id="proj-1",
            steps=[],
            completion_pct=50.0,
            total_required=4,
            completed_required=2,
            is_fully_onboarded=False,
        )
        defaults.update(kwargs)
        return OnboardingProgress(**defaults)

    def test_creation(self):
        p = self._make_progress()
        assert p.project_id == "proj-1"

    def test_completion_pct_bounds_low(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self._make_progress(completion_pct=-1.0)

    def test_completion_pct_bounds_high(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self._make_progress(completion_pct=100.1)

    def test_completion_pct_100_valid(self):
        p = self._make_progress(completion_pct=100.0, is_fully_onboarded=True)
        assert p.completion_pct == pytest.approx(100.0)

    def test_completed_default_empty_dict(self):
        p = self._make_progress()
        assert p.completed == {}

    def test_is_fully_onboarded(self):
        p = self._make_progress(is_fully_onboarded=True)
        assert p.is_fully_onboarded is True


# ---------------------------------------------------------------------------
# ProgressUpdateRequest
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ONBOARD_OK, reason="onboarding.schemas import failed")
class TestProgressUpdateRequest:
    def test_creation(self):
        r = ProgressUpdateRequest(project_id="proj-1", step_id="create_project")
        assert r.project_id == "proj-1"
        assert r.step_id == "create_project"

    def test_done_default_true(self):
        r = ProgressUpdateRequest(project_id="proj-1", step_id="step-x")
        assert r.done is True

    def test_done_false(self):
        r = ProgressUpdateRequest(project_id="proj-1", step_id="step-x", done=False)
        assert r.done is False

    def test_project_id_min_length(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ProgressUpdateRequest(project_id="", step_id="step")

    def test_step_id_min_length(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ProgressUpdateRequest(project_id="proj", step_id="")


# ---------------------------------------------------------------------------
# DslParameter
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSL_OK, reason="dsl.schemas import failed")
class TestDslParameter:
    def test_creation(self):
        p = DslParameter(name="selector", type="string")
        assert p.name == "selector"
        assert p.type == "string"

    def test_required_default_true(self):
        p = DslParameter(name="x", type="string")
        assert p.required is True

    def test_description_default_none(self):
        p = DslParameter(name="x", type="string")
        assert p.description is None

    def test_default_value_none(self):
        p = DslParameter(name="x", type="string")
        assert p.default is None

    def test_with_default_value(self):
        p = DslParameter(name="timeout", type="integer", default=5000)
        assert p.default == 5000


# ---------------------------------------------------------------------------
# DslImplementation
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSL_OK, reason="dsl.schemas import failed")
class TestDslImplementation:
    def test_creation(self):
        impl = DslImplementation(source_file="playwright/steps.py")
        assert impl.source_file == "playwright/steps.py"

    def test_module_default_none(self):
        impl = DslImplementation(source_file="steps.py")
        assert impl.module is None

    def test_function_default_none(self):
        impl = DslImplementation(source_file="steps.py")
        assert impl.function is None

    def test_cls_via_class_alias(self):
        # cls field has alias "class"
        impl = DslImplementation(source_file="steps.java", **{"class": "LoginSteps"})
        assert impl.cls == "LoginSteps"


# ---------------------------------------------------------------------------
# DslAction
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSL_OK, reason="dsl.schemas import failed")
class TestDslAction:
    def test_creation(self):
        a = DslAction(id="ui.click.button", category="ui", description="Click a button")
        assert a.id == "ui.click.button"

    def test_defaults_empty(self):
        a = DslAction(id="x", category="ui", description="d")
        assert a.aliases == {}
        assert a.parameters == []
        assert a.implementations == {}
        assert a.tags == []
        assert a.examples == []

    def test_since_default_none(self):
        a = DslAction(id="x", category="ui", description="d")
        assert a.since is None

    def test_deprecated_default_none(self):
        a = DslAction(id="x", category="ui", description="d")
        assert a.deprecated is None

    def test_source_yaml_default_none(self):
        a = DslAction(id="x", category="ui", description="d")
        assert a.source_yaml is None

    def test_with_deprecation_bool(self):
        a = DslAction(id="x", category="ui", description="d", deprecated=True)
        assert a.deprecated is True


# ---------------------------------------------------------------------------
# DslStats
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSL_OK, reason="dsl.schemas import failed")
class TestDslStats:
    def test_creation(self):
        s = DslStats(total=100, unique_ids=98)
        assert s.total == 100
        assert s.unique_ids == 98

    def test_defaults_empty_dicts(self):
        s = DslStats(total=0, unique_ids=0)
        assert s.by_top_category == {}
        assert s.by_full_category == {}
        assert s.by_implementation == {}
        assert s.top_tags == []


# ---------------------------------------------------------------------------
# FieldType
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CATALOG_OK, reason="catalog.schema_v1 import failed")
class TestFieldType:
    def test_string(self):
        # FieldType uses lowercase member names
        assert FieldType.string == "string"

    def test_integer(self):
        assert FieldType.integer == "integer"

    def test_float(self):
        assert FieldType.float == "float"

    def test_boolean(self):
        assert FieldType.boolean == "boolean"

    def test_date(self):
        assert FieldType.date == "date"

    def test_no_number_type(self):
        assert not hasattr(FieldType, "number")

    def test_all_are_strings(self):
        for ft in FieldType:
            assert isinstance(ft.value, str)


# ---------------------------------------------------------------------------
# FieldSpec
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CATALOG_OK, reason="catalog.schema_v1 import failed")
class TestFieldSpec:
    def test_creation(self):
        f = FieldSpec(name="customer_id", type=FieldType.integer)
        assert f.name == "customer_id"
        assert f.type == FieldType.integer

    def test_nullable_default_false(self):
        # FieldSpec.nullable defaults to False
        f = FieldSpec(name="x", type=FieldType.string)
        assert f.nullable is False


# ---------------------------------------------------------------------------
# SchemaSnapshotV1
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CATALOG_OK, reason="catalog.schema_v1 import failed")
class TestSchemaSnapshotV1:
    def test_version_default(self):
        # SchemaSnapshotV1 requires min 1 field (MinLen(1))
        f = FieldSpec(name="id", type=FieldType.integer)
        snap = SchemaSnapshotV1(fields=[f])
        assert snap.version == 1

    def test_with_fields(self):
        f = FieldSpec(name="id", type=FieldType.integer)
        snap = SchemaSnapshotV1(version=1, fields=[f])
        assert len(snap.fields) == 1
        assert snap.fields[0].name == "id"

    def test_empty_fields_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SchemaSnapshotV1(version=1, fields=[])


# ---------------------------------------------------------------------------
# WSMessage
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _NOTIF_OK, reason="notifications.schemas import failed")
class TestWSMessage:
    def test_creation(self):
        msg = WSMessage(type="test_run_update", payload={"run_id": "abc"})
        assert msg.type == "test_run_update"
        assert msg.payload == {"run_id": "abc"}

    def test_timestamp_default_none(self):
        # timestamp is Optional[datetime] with no auto-factory
        msg = WSMessage(type="event", payload={})
        assert msg.timestamp is None

    def test_payload_can_be_any_dict(self):
        msg = WSMessage(type="x", payload={"nested": {"key": [1, 2, 3]}})
        assert msg.payload["nested"]["key"] == [1, 2, 3]
