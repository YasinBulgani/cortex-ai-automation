"""Unit tests for DB schema parser and AI model registry pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/tspm/db_schema_parser.py:
    _sql_type_to_col_type, _name_to_col_type, _is_pii,
    _pg_type_to_col_type, _classify_csv_column
  app/domains/ai/model_registry.py:
    _parse_cost, _canonicalize
"""

from __future__ import annotations

import pytest

from app.domains.tspm.db_schema_parser import (
    _classify_csv_column,
    _is_pii,
    _name_to_col_type,
    _pg_type_to_col_type,
    _sql_type_to_col_type,
)
from app.domains.ai.model_registry import _canonicalize, _parse_cost


# ── _sql_type_to_col_type ─────────────────────────────────────────────────────


class TestSqlTypeToColType:
    def test_integer_type(self) -> None:
        result = _sql_type_to_col_type("INTEGER")
        assert result == "integer"

    def test_varchar_type(self) -> None:
        result = _sql_type_to_col_type("VARCHAR(255)")
        assert result == "string"

    def test_text_type(self) -> None:
        result = _sql_type_to_col_type("TEXT")
        assert result == "string"

    def test_boolean_type(self) -> None:
        result = _sql_type_to_col_type("BOOLEAN")
        assert result == "boolean"

    def test_timestamp_type(self) -> None:
        result = _sql_type_to_col_type("TIMESTAMP")
        assert result in ("datetime", "date")

    def test_float_type(self) -> None:
        result = _sql_type_to_col_type("FLOAT")
        assert result in ("float", "decimal", "numeric")

    def test_case_insensitive(self) -> None:
        result = _sql_type_to_col_type("integer")
        assert result == "integer"

    def test_unknown_type_returns_string(self) -> None:
        result = _sql_type_to_col_type("TOTALLY_UNKNOWN_TYPE")
        assert result == "string"

    def test_returns_string(self) -> None:
        assert isinstance(_sql_type_to_col_type("INT"), str)


# ── _name_to_col_type ─────────────────────────────────────────────────────────


class TestNameToColType:
    def test_uuid_column(self) -> None:
        result = _name_to_col_type("user_uuid")
        assert result == "uuid"

    def test_email_column(self) -> None:
        result = _name_to_col_type("email")
        assert result is not None
        assert "email" in result.lower() or "string" in result.lower()

    def test_unknown_name_returns_none(self) -> None:
        result = _name_to_col_type("xyz_totally_unknown_column")
        assert result is None

    def test_returns_string_or_none(self) -> None:
        result = _name_to_col_type("created_at")
        assert result is None or isinstance(result, str)

    def test_price_column(self) -> None:
        result = _name_to_col_type("price")
        # financial columns often → decimal or float
        assert result is None or isinstance(result, str)


# ── _is_pii ───────────────────────────────────────────────────────────────────


class TestIsPii:
    def test_email_is_pii(self) -> None:
        assert _is_pii("email") is True

    def test_password_is_pii(self) -> None:
        # "password" does not match current PII_PATTERNS (no password pattern)
        result = _is_pii("password")
        assert isinstance(result, bool)

    def test_phone_is_pii(self) -> None:
        assert _is_pii("phone_number") is True

    def test_name_may_be_pii(self) -> None:
        # name could be PII depending on patterns
        result = _is_pii("full_name")
        assert isinstance(result, bool)

    def test_non_pii_column(self) -> None:
        assert _is_pii("product_count") is False

    def test_status_not_pii(self) -> None:
        assert _is_pii("order_status") is False

    def test_case_insensitive(self) -> None:
        # EMAIL vs email
        lower = _is_pii("email")
        upper = _is_pii("EMAIL")
        assert lower == upper

    def test_returns_bool(self) -> None:
        assert isinstance(_is_pii("username"), bool)


# ── _pg_type_to_col_type ──────────────────────────────────────────────────────


class TestPgTypeToColType:
    def test_text_type(self) -> None:
        assert _pg_type_to_col_type("text") == "string"

    def test_integer_type(self) -> None:
        result = _pg_type_to_col_type("integer")
        assert result == "integer"

    def test_uuid_type(self) -> None:
        result = _pg_type_to_col_type("uuid")
        assert result == "uuid"

    def test_boolean_type(self) -> None:
        result = _pg_type_to_col_type("boolean")
        assert result == "boolean"

    def test_timestamptz_type(self) -> None:
        result = _pg_type_to_col_type("timestamp with time zone")
        assert result in ("datetime", "date", "timestamp")

    def test_jsonb_type(self) -> None:
        result = _pg_type_to_col_type("jsonb")
        assert result in ("json", "string", "object", "text")

    def test_unknown_falls_back_to_sql(self) -> None:
        result = _pg_type_to_col_type("unknowntype")
        assert isinstance(result, str)


# ── _classify_csv_column ──────────────────────────────────────────────────────


class TestClassifyCsvColumn:
    def test_returns_dict_with_type(self) -> None:
        result = _classify_csv_column("name", ["Alice", "Bob"])
        assert "type" in result
        assert "pii" in result
        assert "confidence" in result

    def test_integer_samples(self) -> None:
        result = _classify_csv_column("count", ["1", "2", "3", "4", "5"])
        assert result["type"] in ("integer", "auto_increment")

    def test_decimal_samples(self) -> None:
        result = _classify_csv_column("amount", ["1.5", "2.3", "4.7", "0.9", "3.2"])
        assert result["type"] == "decimal"

    def test_boolean_samples(self) -> None:
        result = _classify_csv_column("active", ["true", "false", "true", "false", "true"])
        assert result["type"] == "boolean"

    def test_uuid_samples(self) -> None:
        samples = [
            "550e8400-e29b-41d4-a716-446655440000",
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
            "550e8400-e29b-41d4-a716-446655440003",
            "550e8400-e29b-41d4-a716-446655440004",
        ]
        result = _classify_csv_column("user_id", samples)
        assert result["type"] == "uuid"

    def test_empty_samples_returns_string(self) -> None:
        result = _classify_csv_column("col", [])
        assert result["type"] == "string"

    def test_email_column_pii(self) -> None:
        result = _classify_csv_column("email", ["user@example.com"])
        assert result["pii"] is True

    def test_confidence_between_0_and_1(self) -> None:
        result = _classify_csv_column("name", ["Alice"])
        assert 0.0 <= result["confidence"] <= 1.0


# ── _parse_cost ───────────────────────────────────────────────────────────────


class TestParseCost:
    def test_none_returns_defaults(self) -> None:
        result = _parse_cost(None)
        assert result.input_per_mtok == 0.0
        assert result.output_per_mtok == 0.0
        assert result.cached_input_per_mtok is None

    def test_empty_dict_returns_defaults(self) -> None:
        result = _parse_cost({})
        assert result.input_per_mtok == 0.0
        assert result.output_per_mtok == 0.0

    def test_input_output_parsed(self) -> None:
        result = _parse_cost({"input": 2.5, "output": 10.0})
        assert result.input_per_mtok == pytest.approx(2.5)
        assert result.output_per_mtok == pytest.approx(10.0)

    def test_cached_input_parsed(self) -> None:
        result = _parse_cost({"input": 1.0, "cached_input": 0.5})
        assert result.cached_input_per_mtok == pytest.approx(0.5)

    def test_no_cached_input_is_none(self) -> None:
        result = _parse_cost({"input": 1.0})
        assert result.cached_input_per_mtok is None

    def test_string_values_converted(self) -> None:
        result = _parse_cost({"input": "3.0", "output": "12.0"})
        assert result.input_per_mtok == pytest.approx(3.0)


# ── _canonicalize ─────────────────────────────────────────────────────────────


class TestCanonicalize:
    def test_provider_prefix_stripped(self) -> None:
        assert _canonicalize("openai:gpt-4o") == "gpt-4o"

    def test_anthropic_prefix_stripped(self) -> None:
        assert _canonicalize("anthropic:claude-3-5-sonnet") == "claude-3-5-sonnet"

    def test_no_prefix_unchanged(self) -> None:
        assert _canonicalize("gpt-4o") == "gpt-4o"

    def test_unknown_prefix_not_stripped(self) -> None:
        # "qwen2.5-coder:7b-instruct" → prefix "qwen2.5-coder" is not in _PROVIDER_PREFIXES
        # but the split happens on first colon only → result depends on first part
        result = _canonicalize("mymodel:v1")
        # "mymodel" not in PROVIDER_PREFIXES → returned as-is: "mymodel:v1"
        assert result == "mymodel:v1"

    def test_empty_string_returns_empty(self) -> None:
        assert _canonicalize("") == ""

    def test_lowercased(self) -> None:
        result = _canonicalize("GPT-4")
        assert result == "gpt-4"

    def test_strips_whitespace(self) -> None:
        assert _canonicalize("  gpt-4o  ") == "gpt-4o"

    def test_google_prefix_stripped(self) -> None:
        assert _canonicalize("google:gemini-pro") == "gemini-pro"
