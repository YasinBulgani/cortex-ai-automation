from __future__ import annotations

from app.domains.ai.structured_output import (
    schema_policy,
    should_validate_task,
    validate_response,
)


def test_known_json_task_requires_validation():
    assert schema_policy("generate_test_cases") == "json_schema"
    assert should_validate_task("generate_test_cases") is True


def test_analyze_document_contract_matches_agents_v2_intent_graph():
    valid, error, parsed = validate_response(
        "analyze_document",
        """
        {
          "domain": "banking",
          "feature_area": "login",
          "title": "Login akışı",
          "summary": "Kullanıcı güvenli giriş yapar.",
          "acceptance_criteria": [
            {"id": "AC-1", "given": "Geçerli kullanıcı", "when": "Giriş yapar", "then": "Dashboard açılır"}
          ],
          "risk_level": "medium"
        }
        """,
    )

    assert valid is True
    assert error is None
    assert parsed is not None
    assert parsed["domain"] == "banking"
    assert parsed["feature_area"] == "login"
    assert parsed["acceptance_criteria"][0]["id"] == "AC-1"


def test_explicit_unstructured_task_skips_validation():
    assert schema_policy("generate_playwright") == "explicit_unstructured"
    assert should_validate_task("generate_playwright") is False
    valid, error, parsed = validate_response("generate_playwright", "plain code")
    assert valid is True
    assert error is None
    assert parsed is None


def test_unknown_task_is_missing_policy_not_fail_open():
    assert schema_policy("mystery_task") == "missing_policy"
    assert should_validate_task("mystery_task") is True
    valid, error, parsed = validate_response("mystery_task", "{}")
    assert valid is False
    assert "policy" in (error or "")
    assert parsed is None
