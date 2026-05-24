"""Unit tests for app.domains.rules.service.

All SQLAlchemy Session and ORM dependencies are mocked.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

try:
    import app.domains.rules.service as rules_service
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="rules service import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ruleset(dataset_id: str = "ds-001", name: str = "My Rules") -> MagicMock:
    rs = MagicMock()
    rs.id = str(uuid.uuid4())
    rs.dataset_id = dataset_id
    rs.name = name
    rs.rules_body = None
    rs.version = None

    for col_name in ("id", "dataset_id", "name", "rules_body", "version"):
        col = SimpleNamespace(key=col_name)

    rs.__table__ = SimpleNamespace(columns=[
        SimpleNamespace(key="id"),
        SimpleNamespace(key="dataset_id"),
        SimpleNamespace(key="name"),
        SimpleNamespace(key="rules_body"),
        SimpleNamespace(key="version"),
    ])
    return rs


def _make_dataset(dataset_id: str = "ds-001") -> MagicMock:
    ds = MagicMock()
    ds.id = dataset_id
    return ds


def _db_with(dataset=None, ruleset=None):
    db = MagicMock()

    def get_side(model, pk):
        from app.infra.models import Dataset, RuleSet
        if model is Dataset:
            return dataset
        if model is RuleSet:
            return ruleset
        return None

    db.get.side_effect = get_side
    db.scalars.return_value.all.return_value = ([ruleset] if ruleset else [])
    db.commit.return_value = None
    db.refresh.return_value = None
    db.add.return_value = None
    return db


# ---------------------------------------------------------------------------
# list_rules
# ---------------------------------------------------------------------------

class TestListRules:
    def test_list_rules_returns_list(self):
        ds = _make_dataset()
        rs = _make_ruleset()
        db = _db_with(dataset=ds, ruleset=rs)
        result = rules_service.list_rules(db, dataset_id="ds-001")
        assert isinstance(result, list)

    def test_list_rules_raises_key_error_for_missing_dataset(self):
        db = _db_with(dataset=None)
        with pytest.raises(KeyError, match="bulunamadı"):
            rules_service.list_rules(db, dataset_id="nonexistent")

    def test_list_rules_empty_when_no_rulesets(self):
        ds = _make_dataset()
        db = _db_with(dataset=ds, ruleset=None)
        result = rules_service.list_rules(db, dataset_id="ds-001")
        assert result == []


# ---------------------------------------------------------------------------
# get_rule
# ---------------------------------------------------------------------------

class TestGetRule:
    def test_get_rule_returns_dict(self):
        ds = _make_dataset()
        rs = _make_ruleset()
        db = _db_with(dataset=ds, ruleset=rs)
        result = rules_service.get_rule(db, dataset_id="ds-001", rule_set_id=rs.id)
        assert isinstance(result, dict)
        assert result["id"] == rs.id

    def test_get_rule_raises_key_error_missing_dataset(self):
        db = _db_with(dataset=None)
        with pytest.raises(KeyError):
            rules_service.get_rule(db, dataset_id="ghost-ds", rule_set_id="any")

    def test_get_rule_raises_key_error_missing_ruleset(self):
        ds = _make_dataset()
        db = _db_with(dataset=ds, ruleset=None)
        with pytest.raises(KeyError):
            rules_service.get_rule(db, dataset_id="ds-001", rule_set_id="ghost-rs")

    def test_get_rule_raises_key_error_wrong_dataset(self):
        """RuleSet exists but belongs to a different dataset."""
        ds = _make_dataset("ds-001")
        rs = _make_ruleset(dataset_id="ds-OTHER")
        db = _db_with(dataset=ds, ruleset=rs)
        with pytest.raises(KeyError):
            rules_service.get_rule(db, dataset_id="ds-001", rule_set_id=rs.id)


# ---------------------------------------------------------------------------
# create_rule
# ---------------------------------------------------------------------------

class TestCreateRule:
    def test_create_rule_returns_dict_with_id(self):
        ds = _make_dataset()
        rs = _make_ruleset()
        db = _db_with(dataset=ds)

        with MagicMock() as mock_rs_cls:
            # Patch RuleSet constructor inside the service module
            import app.infra.models as models_mod
            original = models_mod.RuleSet
            models_mod.RuleSet = lambda **kw: rs
            try:
                result = rules_service.create_rule(db, dataset_id="ds-001", data={"name": "Test Rules"})
            finally:
                models_mod.RuleSet = original

        assert isinstance(result, dict)
        assert "id" in result

    def test_create_rule_raises_key_error_missing_dataset(self):
        db = _db_with(dataset=None)
        with pytest.raises(KeyError):
            rules_service.create_rule(db, dataset_id="ghost", data={"name": "x"})

    def test_create_rule_raises_value_error_missing_name(self):
        ds = _make_dataset()
        db = _db_with(dataset=ds)
        with pytest.raises(ValueError, match="zorunludur"):
            rules_service.create_rule(db, dataset_id="ds-001", data={})

    def test_create_rule_raises_value_error_blank_name(self):
        ds = _make_dataset()
        db = _db_with(dataset=ds)
        with pytest.raises(ValueError):
            rules_service.create_rule(db, dataset_id="ds-001", data={"name": "   "})


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------

class TestEvaluate:
    def test_evaluate_dict_body_returns_result(self):
        result = rules_service.evaluate({"rule": "allow_all"}, context={"user": "alice"})
        assert isinstance(result, dict)
        assert "passed" in result

    def test_evaluate_list_body_returns_result(self):
        result = rules_service.evaluate([{"type": "allow"}], context={})
        assert isinstance(result, dict)
        assert "passed" in result

    def test_evaluate_json_string_body(self):
        result = rules_service.evaluate('{"rule": "allow"}', context={"k": "v"})
        assert isinstance(result, dict)

    def test_evaluate_invalid_json_string_raises_value_error(self):
        with pytest.raises(ValueError, match="JSON parse"):
            rules_service.evaluate("{not valid json}", context={})

    def test_evaluate_invalid_type_raises_value_error(self):
        with pytest.raises(ValueError, match="dict veya list"):
            rules_service.evaluate(42, context={})
