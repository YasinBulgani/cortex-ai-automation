"""Unit tests for api_testing.environment helpers and agents.v2.schemas.intent models.

Tests are fully self-contained: no DB, no HTTP, no LLM.
Covers:
  - _random_iban: format TR + 2-digit check + bank code
  - _random_tckn: 11 digits, first ≠ 0
  - _random_phone: +90 prefix, valid TR prefix, length
  - resolve_string: static vars, env.prefix, built-in $variables, unknown passthrough
  - resolve_dict: recursive string/dict/list resolution, type preservation
  - merge_variables: later sources override earlier
  - mask_sensitive: default sensitive keys masked, safe keys unchanged

  - RiskLevel: enum values
  - ActorRole: model creation, defaults
  - ComplianceRef: fields
  - AcceptanceCriterion: priority bounds
  - IntentGraph: domain/feature_area normalization, is_critical property, to_state_dict
"""
from __future__ import annotations

import re
import pytest

try:
    from app.domains.api_testing.environment import (
        _random_iban,
        _random_tckn,
        _random_phone,
        resolve_string,
        resolve_dict,
        merge_variables,
        mask_sensitive,
    )
    _ENV_OK = True
except ImportError:
    _ENV_OK = False

try:
    from app.domains.agents.v2.schemas.intent import (
        RiskLevel,
        ActorRole,
        ComplianceRef,
        AcceptanceCriterion,
        IntentGraph,
    )
    _INTENT_OK = True
except ImportError:
    _INTENT_OK = False


# ---------------------------------------------------------------------------
# _random_iban
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ENV_OK, reason="environment import failed")
class TestRandomIban:
    def test_starts_with_tr(self):
        assert _random_iban().startswith("TR")

    def test_total_length(self):
        # TR(2) + check(2) + bank(4) + "0"(1) + digits(16) = 25 chars
        assert len(_random_iban()) == 25

    def test_only_alphanumeric(self):
        iban = _random_iban()
        assert re.fullmatch(r"TR\d{23}", iban), f"Unexpected format: {iban}"

    def test_multiple_calls_differ(self):
        # Very unlikely to get 10 identical IBANs
        ibans = {_random_iban() for _ in range(10)}
        assert len(ibans) > 1


# ---------------------------------------------------------------------------
# _random_tckn
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ENV_OK, reason="environment import failed")
class TestRandomTckn:
    def test_length_11(self):
        assert len(_random_tckn()) == 11

    def test_all_digits(self):
        assert _random_tckn().isdigit()

    def test_first_digit_not_zero(self):
        for _ in range(20):
            assert _random_tckn()[0] != "0"

    def test_returns_string(self):
        assert isinstance(_random_tckn(), str)


# ---------------------------------------------------------------------------
# _random_phone
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ENV_OK, reason="environment import failed")
class TestRandomPhone:
    def test_starts_with_plus90(self):
        assert _random_phone().startswith("+90")

    def test_total_length(self):
        # +90 + 3 digit prefix + 7 digits = 13 chars
        assert len(_random_phone()) == 13

    def test_only_digits_after_plus(self):
        phone = _random_phone()
        assert phone[1:].isdigit()

    def test_returns_string(self):
        assert isinstance(_random_phone(), str)


# ---------------------------------------------------------------------------
# resolve_string — static variables
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ENV_OK, reason="environment import failed")
class TestResolveStringStatic:
    def test_no_placeholders_unchanged(self):
        assert resolve_string("hello world", {}) == "hello world"

    def test_variable_substituted(self):
        result = resolve_string("{{base_url}}/api", {"base_url": "http://localhost:8000"})
        assert result == "http://localhost:8000/api"

    def test_multiple_variables(self):
        result = resolve_string("{{a}}+{{b}}", {"a": "1", "b": "2"})
        assert result == "1+2"

    def test_env_prefix_removed(self):
        result = resolve_string("{{env.token}}", {"token": "secret123"})
        assert result == "secret123"

    def test_unknown_variable_kept_as_is(self):
        result = resolve_string("{{unknown_var}}", {})
        assert result == "{{unknown_var}}"

    def test_empty_string(self):
        assert resolve_string("", {}) == ""

    def test_whitespace_in_key_trimmed(self):
        result = resolve_string("{{ host }}", {"host": "example.com"})
        assert result == "example.com"

    def test_returns_string(self):
        assert isinstance(resolve_string("{{x}}", {"x": "42"}), str)


# ---------------------------------------------------------------------------
# resolve_string — built-in $variables
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ENV_OK, reason="environment import failed")
class TestResolveStringBuiltins:
    def test_random_int_is_numeric_string(self):
        result = resolve_string("{{$randomInt}}", {})
        assert result.isdigit()

    def test_random_uuid_format(self):
        result = resolve_string("{{$randomUUID}}", {})
        assert re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            result
        ), f"Not a UUID: {result}"

    def test_guid_alias(self):
        result = resolve_string("{{$guid}}", {})
        assert len(result) == 36

    def test_timestamp_is_integer_string(self):
        result = resolve_string("{{$timestamp}}", {})
        assert int(result) > 0

    def test_iso_timestamp_format(self):
        result = resolve_string("{{$isoTimestamp}}", {})
        assert "T" in result  # ISO 8601 contains 'T'
        assert "Z" in result or "+" in result  # timezone info

    def test_random_iban_in_string(self):
        result = resolve_string("IBAN: {{$randomIBAN}}", {})
        assert result.startswith("IBAN: TR")

    def test_random_tckn_in_string(self):
        result = resolve_string("TC: {{$randomTCKN}}", {})
        tc_part = result.replace("TC: ", "")
        assert len(tc_part) == 11
        assert tc_part.isdigit()

    def test_random_email_format(self):
        result = resolve_string("{{$randomEmail}}", {})
        assert "@nexusqa.test" in result

    def test_random_phone_format(self):
        result = resolve_string("{{$randomPhone}}", {})
        assert result.startswith("+90")

    def test_random_string_lowercase(self):
        result = resolve_string("{{$randomString}}", {})
        assert result.islower()
        assert len(result) == 12

    def test_random_boolean(self):
        result = resolve_string("{{$randomBoolean}}", {})
        assert result in ("true", "false")

    def test_random_float_numeric(self):
        result = resolve_string("{{$randomFloat}}", {})
        assert float(result) > 0


# ---------------------------------------------------------------------------
# resolve_dict
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ENV_OK, reason="environment import failed")
class TestResolveDict:
    def test_string_resolved(self):
        result = resolve_dict("{{url}}", {"url": "http://api.example.com"})
        assert result == "http://api.example.com"

    def test_dict_values_resolved(self):
        result = resolve_dict({"endpoint": "{{host}}/v1"}, {"host": "api.bank.com"})
        assert result == {"endpoint": "api.bank.com/v1"}

    def test_nested_dict_resolved(self):
        result = resolve_dict(
            {"outer": {"inner": "{{val}}"}},
            {"val": "resolved"}
        )
        assert result["outer"]["inner"] == "resolved"

    def test_list_elements_resolved(self):
        result = resolve_dict(["{{a}}", "{{b}}"], {"a": "x", "b": "y"})
        assert result == ["x", "y"]

    def test_int_unchanged(self):
        result = resolve_dict(42, {})
        assert result == 42

    def test_none_unchanged(self):
        result = resolve_dict(None, {})
        assert result is None

    def test_bool_unchanged(self):
        result = resolve_dict(True, {})
        assert result is True

    def test_full_match_json_type_preserved(self):
        # "{{count}}" where count="5" → tries json.loads("5") → int 5
        result = resolve_dict("{{count}}", {"count": "5"})
        assert result == 5


# ---------------------------------------------------------------------------
# merge_variables
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ENV_OK, reason="environment import failed")
class TestMergeVariables:
    def test_single_source(self):
        result = merge_variables({"a": "1"})
        assert result == {"a": "1"}

    def test_later_overrides_earlier(self):
        result = merge_variables({"a": "1", "b": "2"}, {"a": "99"})
        assert result["a"] == "99"
        assert result["b"] == "2"

    def test_multiple_sources(self):
        result = merge_variables({"a": "1"}, {"b": "2"}, {"c": "3"})
        assert result == {"a": "1", "b": "2", "c": "3"}

    def test_empty_sources_ignored(self):
        result = merge_variables({}, {"x": "1"}, {})
        assert result == {"x": "1"}

    def test_returns_dict(self):
        assert isinstance(merge_variables({"a": "1"}), dict)


# ---------------------------------------------------------------------------
# mask_sensitive
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ENV_OK, reason="environment import failed")
class TestMaskSensitive:
    def test_password_masked(self):
        result = mask_sensitive({"password": "mysecret12345"})
        assert result["password"] != "mysecret12345"
        assert "*" in result["password"]

    def test_token_masked(self):
        result = mask_sensitive({"auth_token": "abcdefghijklmnop"})
        assert "*" in result["auth_token"]

    def test_safe_key_unchanged(self):
        result = mask_sensitive({"base_url": "http://api.example.com"})
        assert result["base_url"] == "http://api.example.com"

    def test_short_value_masked_to_four_stars(self):
        # len("abc") = 3 <= 10 → "****"
        result = mask_sensitive({"secret": "abc"})
        assert result["secret"] == "****"

    def test_long_value_shows_first_and_last(self):
        # len("abcdefghijklmnop") = 16 > 10
        val = "abcdefghijklmnop"
        result = mask_sensitive({"api_key": val})
        masked = result["api_key"]
        assert masked.startswith("abcd")
        assert masked.endswith("mnop")

    def test_custom_sensitive_keys(self):
        result = mask_sensitive({"my_credential": "supersecret1234"}, sensitive_keys=["credential"])
        assert "*" in result["my_credential"]

    def test_returns_dict(self):
        assert isinstance(mask_sensitive({}), dict)


# ---------------------------------------------------------------------------
# RiskLevel
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _INTENT_OK, reason="intent import failed")
class TestRiskLevel:
    def test_low(self):
        assert RiskLevel.LOW == "low"

    def test_medium(self):
        assert RiskLevel.MEDIUM == "medium"

    def test_high(self):
        assert RiskLevel.HIGH == "high"

    def test_critical(self):
        assert RiskLevel.CRITICAL == "critical"

    def test_all_are_strings(self):
        for level in RiskLevel:
            assert isinstance(level.value, str)


# ---------------------------------------------------------------------------
# ActorRole
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _INTENT_OK, reason="intent import failed")
class TestActorRole:
    def test_creation(self):
        actor = ActorRole(name="customer")
        assert actor.name == "customer"

    def test_description_defaults_none(self):
        actor = ActorRole(name="admin")
        assert actor.description is None

    def test_permissions_default_empty(self):
        actor = ActorRole(name="user")
        assert actor.permissions == []

    def test_with_permissions(self):
        actor = ActorRole(name="admin", permissions=["read", "write"])
        assert "read" in actor.permissions

    def test_extra_fields_allowed(self):
        # model_config = ConfigDict(extra="allow")
        actor = ActorRole(name="teller", branch_id="B001")
        assert actor.branch_id == "B001"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# ComplianceRef
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _INTENT_OK, reason="intent import failed")
class TestComplianceRef:
    def test_creation(self):
        ref = ComplianceRef(framework="KVKK", article="Madde 12")
        assert ref.framework == "KVKK"
        assert ref.article == "Madde 12"

    def test_note_defaults_none(self):
        ref = ComplianceRef(framework="BDDK", article="2.3.1")
        assert ref.note is None


# ---------------------------------------------------------------------------
# AcceptanceCriterion
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _INTENT_OK, reason="intent import failed")
class TestAcceptanceCriterion:
    def test_creation(self):
        ac = AcceptanceCriterion(
            id="AC-001",
            given="a logged-in user",
            when="they transfer money",
            then="the balance is reduced",
        )
        assert ac.id == "AC-001"

    def test_priority_default_3(self):
        ac = AcceptanceCriterion(id="x", given="g", when="w", then="t")
        assert ac.priority == 3

    def test_priority_bounds_min(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AcceptanceCriterion(id="x", given="g", when="w", then="t", priority=0)

    def test_priority_bounds_max(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AcceptanceCriterion(id="x", given="g", when="w", then="t", priority=6)

    def test_priority_5_valid(self):
        ac = AcceptanceCriterion(id="x", given="g", when="w", then="t", priority=5)
        assert ac.priority == 5


# ---------------------------------------------------------------------------
# IntentGraph
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _INTENT_OK, reason="intent import failed")
def _make_intent(**kwargs):
    defaults = dict(domain="banking", feature_area="Login", title="Login Feature")
    defaults.update(kwargs)
    return IntentGraph(**defaults)


@pytest.mark.skipif(not _INTENT_OK, reason="intent import failed")
class TestIntentGraph:
    def test_creation(self):
        ig = _make_intent()
        assert ig.title == "Login Feature"

    def test_domain_normalized_lowercase(self):
        ig = _make_intent(domain="Banking")
        assert ig.domain == "banking"

    def test_domain_spaces_replaced(self):
        ig = _make_intent(domain="Core Banking")
        assert ig.domain == "core_banking"

    def test_feature_area_normalized(self):
        ig = _make_intent(feature_area="User Login")
        assert ig.feature_area == "user_login"

    def test_default_risk_level_medium(self):
        ig = _make_intent()
        assert ig.risk_level == RiskLevel.MEDIUM

    def test_default_language(self):
        ig = _make_intent()
        assert ig.language == "tr-TR"

    def test_default_lists_empty(self):
        ig = _make_intent()
        assert ig.actors == []
        assert ig.goals == []
        assert ig.acceptance_criteria == []
        assert ig.compliance_refs == []

    def test_is_critical_false_for_medium(self):
        ig = _make_intent(risk_level=RiskLevel.MEDIUM)
        assert ig.is_critical is False

    def test_is_critical_false_for_low(self):
        ig = _make_intent(risk_level=RiskLevel.LOW)
        assert ig.is_critical is False

    def test_is_critical_true_for_high(self):
        ig = _make_intent(risk_level=RiskLevel.HIGH)
        assert ig.is_critical is True

    def test_is_critical_true_for_critical(self):
        ig = _make_intent(risk_level=RiskLevel.CRITICAL)
        assert ig.is_critical is True

    def test_to_state_dict_keys(self):
        ig = _make_intent()
        d = ig.to_state_dict()
        assert isinstance(d, dict)
        assert "domain" in d
        assert "feature_area" in d

    def test_to_state_dict_domain(self):
        ig = _make_intent(domain="insurance")
        d = ig.to_state_dict()
        assert d["domain"] == "insurance"

    def test_to_state_dict_actors_list(self):
        ig = _make_intent()
        ig.actors.append(ActorRole(name="teller"))
        d = ig.to_state_dict()
        assert "teller" in d["actors"]

    def test_goals_stored(self):
        ig = _make_intent(goals=["goal1", "goal2"])
        assert "goal1" in ig.goals

    def test_validate_assignment_on_risk(self):
        ig = _make_intent()
        ig.risk_level = RiskLevel.CRITICAL
        assert ig.is_critical is True
