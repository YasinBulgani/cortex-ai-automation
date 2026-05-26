"""Unit tests for app.domains.api_testing.spec_parser — pure helpers.

Tests are fully self-contained: no DB, no HTTP, no external validator.
Covers: detect_format, parse_raw, _extract_schema_from_content,
        _assess_risk (risk levels, PII/financial detection, compliance tags),
        _detect_dependencies, EndpointInfo.to_dict, SpecAnalysis.
"""
from __future__ import annotations

import json
import pytest

try:
    from app.domains.api_testing.spec_parser import (
        detect_format,
        parse_raw,
        _extract_schema_from_content,
        _assess_risk,
        _detect_dependencies,
        EndpointInfo,
        SpecAnalysis,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="spec_parser import failed")


# ---------------------------------------------------------------------------
# detect_format
# ---------------------------------------------------------------------------

class TestDetectFormat:
    def test_openapi_3_0(self):
        spec = {"openapi": "3.0.3", "info": {"title": "Test", "version": "1.0"}}
        assert detect_format(spec) == "openapi_3.0"

    def test_openapi_3_1(self):
        spec = {"openapi": "3.1.0"}
        assert detect_format(spec) == "openapi_3.1"

    def test_swagger_2_0(self):
        spec = {"swagger": "2.0"}
        assert detect_format(spec) == "swagger_2.0"

    def test_unknown_format(self):
        spec = {"raml": "1.0"}
        assert detect_format(spec) == "unknown"

    def test_empty_spec_unknown(self):
        assert detect_format({}) == "unknown"

    def test_returns_string(self):
        assert isinstance(detect_format({"openapi": "3.0.0"}), str)


# ---------------------------------------------------------------------------
# parse_raw
# ---------------------------------------------------------------------------

class TestParseRaw:
    def test_json_string_parsed(self):
        content = '{"openapi": "3.0.0", "info": {"title": "Test", "version": "1.0"}}'
        result = parse_raw(content)
        assert result["openapi"] == "3.0.0"

    def test_json_bytes_parsed(self):
        content = b'{"swagger": "2.0"}'
        result = parse_raw(content)
        assert result["swagger"] == "2.0"

    def test_yaml_string_parsed(self):
        content = "openapi: '3.0.0'\ninfo:\n  title: Test\n  version: '1.0'"
        result = parse_raw(content)
        assert result.get("openapi") == "3.0.0"

    def test_invalid_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_raw("not valid json or yaml that results in dict")

    def test_returns_dict(self):
        content = '{"key": "value"}'
        result = parse_raw(content)
        assert isinstance(result, dict)

    def test_nested_json_parsed(self):
        data = {"paths": {"/users": {"get": {"summary": "List users"}}}}
        content = json.dumps(data)
        result = parse_raw(content)
        assert "/users" in result["paths"]


# ---------------------------------------------------------------------------
# _extract_schema_from_content
# ---------------------------------------------------------------------------

class TestExtractSchemaFromContent:
    def test_application_json_preferred(self):
        content = {
            "application/json": {"schema": {"type": "object"}},
            "text/plain": {"schema": {"type": "string"}},
        }
        result = _extract_schema_from_content(content)
        assert result == {"type": "object"}

    def test_empty_content_returns_none(self):
        assert _extract_schema_from_content({}) is None

    def test_none_returns_none(self):
        assert _extract_schema_from_content(None) is None

    def test_fallback_to_first_available(self):
        content = {"text/html": {"schema": {"type": "string"}}}
        result = _extract_schema_from_content(content)
        assert result == {"type": "string"}

    def test_content_without_schema_key_returns_none(self):
        content = {"application/json": {"examples": {}}}
        result = _extract_schema_from_content(content)
        assert result is None


# ---------------------------------------------------------------------------
# _assess_risk
# ---------------------------------------------------------------------------

class TestAssessRisk:
    def _make_endpoint(self, method="GET", path="/test", auth_required=True, **kwargs):
        ep = EndpointInfo(method=method, path=path, auth_required=auth_required, **kwargs)
        return ep

    def test_auth_path_critical(self):
        ep = self._make_endpoint(method="POST", path="/auth/login")
        _assess_risk(ep)
        assert ep.risk_level == "critical"

    def test_financial_path_critical(self):
        ep = self._make_endpoint(method="POST", path="/transfers/create")
        _assess_risk(ep)
        assert ep.risk_level == "critical"

    def test_delete_with_auth_high(self):
        ep = self._make_endpoint(method="DELETE", path="/users/1", auth_required=True)
        _assess_risk(ep)
        assert ep.risk_level in ("high", "critical")

    def test_get_without_auth_low(self):
        ep = self._make_endpoint(method="GET", path="/public/status", auth_required=False)
        _assess_risk(ep)
        assert ep.risk_level == "low"

    def test_pii_in_path_flagged(self):
        ep = self._make_endpoint(path="/users/password/reset")
        _assess_risk(ep)
        assert ep.has_pii is True

    def test_pii_adds_kvkk_tag(self):
        ep = self._make_endpoint(path="/users/email")
        _assess_risk(ep)
        assert "KVKK" in ep.compliance_tags

    def test_financial_adds_bddk_masak_tags(self):
        ep = self._make_endpoint(path="/payment/process")
        _assess_risk(ep)
        assert "BDDK" in ep.compliance_tags
        assert "MASAK" in ep.compliance_tags

    def test_card_data_adds_pci_dss_tag(self):
        ep = self._make_endpoint(path="/card/charge")
        _assess_risk(ep)
        assert "PCI-DSS" in ep.compliance_tags

    def test_returns_none(self):
        ep = self._make_endpoint()
        result = _assess_risk(ep)
        assert result is None  # modifies in-place, returns None

    def test_pii_post_is_high(self):
        ep = self._make_endpoint(method="POST", path="/users/identity")
        _assess_risk(ep)
        # Has PII + POST → high (unless overridden by auth/financial)
        assert ep.risk_level in ("high", "critical")


# ---------------------------------------------------------------------------
# _detect_dependencies
# ---------------------------------------------------------------------------

class TestDetectDependencies:
    def test_empty_list_no_error(self):
        _detect_dependencies([])

    def test_auth_endpoint_dependency_added(self):
        login_ep = EndpointInfo(method="POST", path="/auth/login")
        get_ep = EndpointInfo(method="GET", path="/accounts/{id}", auth_required=True)
        _detect_dependencies([login_ep, get_ep])
        dep_endpoints = [d["endpoint"] for d in get_ep.depends_on]
        assert any("auth/login" in e for e in dep_endpoints)

    def test_path_param_dependency_detected(self):
        create_ep = EndpointInfo(method="POST", path="/users")
        get_ep = EndpointInfo(method="GET", path="/users/{user_id}", auth_required=False)
        _detect_dependencies([create_ep, get_ep])
        # user_id → user → POST /users
        dep_endpoints = [d["endpoint"] for d in get_ep.depends_on]
        assert any("POST /users" in e for e in dep_endpoints)

    def test_login_endpoint_has_no_login_dependency(self):
        login_ep = EndpointInfo(method="POST", path="/auth/login")
        _detect_dependencies([login_ep])
        # Login shouldn't depend on itself
        assert not login_ep.depends_on


# ---------------------------------------------------------------------------
# EndpointInfo.to_dict
# ---------------------------------------------------------------------------

class TestEndpointInfoToDict:
    def test_returns_dict(self):
        ep = EndpointInfo(method="GET", path="/test")
        result = ep.to_dict()
        assert isinstance(result, dict)

    def test_has_method_field(self):
        ep = EndpointInfo(method="POST", path="/users")
        result = ep.to_dict()
        assert result["method"] == "POST"

    def test_has_path_field(self):
        ep = EndpointInfo(method="GET", path="/accounts/{id}")
        result = ep.to_dict()
        assert result["path"] == "/accounts/{id}"

    def test_has_risk_level_field(self):
        ep = EndpointInfo(method="GET", path="/test")
        result = ep.to_dict()
        assert "risk_level" in result

    def test_has_pii_field(self):
        ep = EndpointInfo(method="GET", path="/test")
        result = ep.to_dict()
        assert "has_pii" in result

    def test_has_compliance_tags_field(self):
        ep = EndpointInfo(method="GET", path="/test")
        result = ep.to_dict()
        assert "compliance_tags" in result

    def test_operation_id_in_dict(self):
        ep = EndpointInfo(method="GET", path="/test", operation_id="listUsers")
        result = ep.to_dict()
        assert result["operation_id"] == "listUsers"


# ---------------------------------------------------------------------------
# SpecAnalysis dataclass
# ---------------------------------------------------------------------------

class TestSpecAnalysis:
    def test_can_instantiate_with_defaults(self):
        analysis = SpecAnalysis(spec_format="openapi_3.0")
        assert analysis.spec_format == "openapi_3.0"

    def test_endpoints_default_empty_list(self):
        analysis = SpecAnalysis(spec_format="swagger_2.0")
        assert analysis.endpoints == []

    def test_errors_default_empty_list(self):
        analysis = SpecAnalysis(spec_format="openapi_3.0")
        assert analysis.errors == []

    def test_endpoint_count_default_zero(self):
        analysis = SpecAnalysis(spec_format="openapi_3.0")
        assert analysis.endpoint_count == 0
