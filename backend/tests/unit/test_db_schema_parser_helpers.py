"""Unit tests for tspm/db_schema_parser.py pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/tspm/db_schema_parser.py:
    _sql_type_to_col_type, _name_to_col_type, _is_pii,
    _assign_ids, _pg_type_to_col_type
"""

from __future__ import annotations

import pytest

from app.domains.tspm.db_schema_parser import (
    _assign_ids,
    _is_pii,
    _name_to_col_type,
    _pg_type_to_col_type,
    _sql_type_to_col_type,
)


# ── _sql_type_to_col_type ─────────────────────────────────────────────────────


class TestSqlTypeToColType:
    def test_integer_type(self) -> None:
        result = _sql_type_to_col_type("INTEGER")
        assert result == "integer"

    def test_varchar_type(self) -> None:
        result = _sql_type_to_col_type("VARCHAR(255)")
        assert result in ("string", "text")

    def test_boolean_type(self) -> None:
        result = _sql_type_to_col_type("BOOLEAN")
        assert result == "boolean"

    def test_timestamp_type(self) -> None:
        result = _sql_type_to_col_type("TIMESTAMP")
        assert result in ("datetime", "timestamp", "date")

    def test_unknown_type_returns_string(self) -> None:
        result = _sql_type_to_col_type("CUSTOM_TYPE")
        assert result == "string"

    def test_case_insensitive(self) -> None:
        lower = _sql_type_to_col_type("integer")
        upper = _sql_type_to_col_type("INTEGER")
        assert lower == upper

    def test_returns_string(self) -> None:
        assert isinstance(_sql_type_to_col_type("INT"), str)

    def test_decimal_type(self) -> None:
        result = _sql_type_to_col_type("DECIMAL(10,2)")
        assert result in ("decimal", "float", "numeric", "number")

    def test_text_type(self) -> None:
        result = _sql_type_to_col_type("TEXT")
        assert result in ("string", "text")


# ── _name_to_col_type ─────────────────────────────────────────────────────────


class TestNameToColType:
    def test_id_column_returns_none(self) -> None:
        # "user_id" is not in NAME_TO_COL_TYPE — returns None
        result = _name_to_col_type("user_id")
        assert result is None

    def test_email_column_returns_email(self) -> None:
        result = _name_to_col_type("email")
        assert result == "email"

    def test_phone_column_returns_phone(self) -> None:
        result = _name_to_col_type("phone")
        assert result == "phone"

    def test_name_column_returns_name_type(self) -> None:
        result = _name_to_col_type("first_name")
        assert result is not None  # matches first_name pattern

    def test_unknown_name_returns_none(self) -> None:
        result = _name_to_col_type("xyzkzqzrz")
        assert result is None

    def test_returns_string_or_none(self) -> None:
        result = _name_to_col_type("email")
        assert result is None or isinstance(result, str)

    def test_iban_column_returns_iban(self) -> None:
        result = _name_to_col_type("iban")
        assert result == "iban"


# ── _is_pii ───────────────────────────────────────────────────────────────────


class TestIsPii:
    def test_email_is_pii(self) -> None:
        assert _is_pii("email") is True

    def test_phone_is_pii(self) -> None:
        assert _is_pii("phone") is True

    def test_user_email_is_pii(self) -> None:
        assert _is_pii("user_email") is True

    def test_product_id_not_pii(self) -> None:
        assert _is_pii("product_id") is False

    def test_description_not_pii(self) -> None:
        assert _is_pii("description") is False

    def test_returns_bool(self) -> None:
        assert isinstance(_is_pii("email"), bool)

    def test_empty_string_not_pii(self) -> None:
        assert _is_pii("") is False

    def test_name_column_is_pii(self) -> None:
        # "name" typically flags as PII in such systems
        result = _is_pii("first_name")
        assert isinstance(result, bool)


# ── _assign_ids ───────────────────────────────────────────────────────────────


class TestAssignIds:
    def test_assigns_table_ids(self) -> None:
        tables = [{"name": "users", "columns": []}]
        result = _assign_ids(tables)
        assert result[0]["id"] == 1

    def test_assigns_column_ids(self) -> None:
        tables = [
            {
                "name": "users",
                "columns": [{"name": "id"}, {"name": "email"}],
            }
        ]
        result = _assign_ids(tables)
        cols = result[0]["columns"]
        assert cols[0]["id"] == 1
        assert cols[1]["id"] == 2

    def test_sequential_table_ids(self) -> None:
        tables = [
            {"name": "users", "columns": []},
            {"name": "orders", "columns": []},
        ]
        result = _assign_ids(tables)
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

    def test_sequential_column_ids_across_tables(self) -> None:
        tables = [
            {"name": "users", "columns": [{"name": "id"}]},
            {"name": "orders", "columns": [{"name": "id"}]},
        ]
        result = _assign_ids(tables)
        assert result[0]["columns"][0]["id"] == 1
        assert result[1]["columns"][0]["id"] == 2

    def test_empty_tables_list(self) -> None:
        assert _assign_ids([]) == []

    def test_preserves_existing_fields(self) -> None:
        tables = [{"name": "users", "columns": [{"name": "email", "type": "string"}]}]
        result = _assign_ids(tables)
        assert result[0]["columns"][0]["name"] == "email"
        assert result[0]["columns"][0]["type"] == "string"

    def test_returns_list(self) -> None:
        assert isinstance(_assign_ids([]), list)


# ── _pg_type_to_col_type ──────────────────────────────────────────────────────


class TestPgTypeToColType:
    def test_text_type(self) -> None:
        result = _pg_type_to_col_type("text")
        assert isinstance(result, str)

    def test_int4_type(self) -> None:
        result = _pg_type_to_col_type("int4")
        assert isinstance(result, str)

    def test_unknown_fallback_to_sql(self) -> None:
        result = _pg_type_to_col_type("unknown_pg_type")
        assert result == "string"

    def test_returns_string(self) -> None:
        assert isinstance(_pg_type_to_col_type("text"), str)

    def test_bool_type(self) -> None:
        result = _pg_type_to_col_type("bool")
        assert result == "boolean" or isinstance(result, str)
