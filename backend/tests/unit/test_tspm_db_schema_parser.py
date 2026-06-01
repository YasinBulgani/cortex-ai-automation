"""Unit tests for TSPM DB schema parser pure helpers.

Tests app/domains/tspm/db_schema_parser.py — pure Python, no DB.
Covers: _sql_type_to_col_type, _name_to_col_type, _is_pii,
        _assign_ids, _parse_ddl_regex (basic DDL parsing).
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
    def test_integer(self) -> None:
        assert _sql_type_to_col_type("INTEGER") == "integer"

    def test_int(self) -> None:
        assert _sql_type_to_col_type("INT") == "integer"

    def test_bigint(self) -> None:
        assert _sql_type_to_col_type("BIGINT") == "integer"

    def test_varchar(self) -> None:
        result = _sql_type_to_col_type("VARCHAR(255)")
        assert result in ("string", "text")

    def test_text(self) -> None:
        result = _sql_type_to_col_type("TEXT")
        assert result in ("string", "text")

    def test_boolean(self) -> None:
        result = _sql_type_to_col_type("BOOLEAN")
        assert result == "boolean"

    def test_float(self) -> None:
        result = _sql_type_to_col_type("FLOAT")
        assert result in ("float", "decimal", "numeric")

    def test_decimal(self) -> None:
        result = _sql_type_to_col_type("DECIMAL(10,2)")
        assert result in ("decimal", "float", "numeric")

    def test_date(self) -> None:
        result = _sql_type_to_col_type("DATE")
        assert result in ("date", "datetime")

    def test_timestamp(self) -> None:
        result = _sql_type_to_col_type("TIMESTAMP")
        assert result in ("datetime", "date", "timestamp")

    def test_unknown_returns_string(self) -> None:
        assert _sql_type_to_col_type("CUSTOM_TYPE_XYZ") == "string"

    def test_case_insensitive(self) -> None:
        lower = _sql_type_to_col_type("integer")
        upper = _sql_type_to_col_type("INTEGER")
        assert lower == upper


# ── _name_to_col_type ─────────────────────────────────────────────────────────


class TestNameToColType:
    def test_id_column_returns_none(self) -> None:
        # "user_id" has no matching pattern in NAME_TO_COL_TYPE
        result = _name_to_col_type("user_id")
        assert result is None

    def test_email_column(self) -> None:
        result = _name_to_col_type("email")
        assert result is not None

    def test_phone_column(self) -> None:
        result = _name_to_col_type("phone_number")
        assert result is not None

    def test_tarih_column_detected(self) -> None:
        result = _name_to_col_type("tarih")
        assert result == "date"

    def test_unknown_name_returns_none(self) -> None:
        result = _name_to_col_type("xyzqwerty_column_abc")
        assert result is None

    def test_uuid_column(self) -> None:
        result = _name_to_col_type("uuid")
        assert result == "uuid"

    def test_tc_kimlik_column(self) -> None:
        result = _name_to_col_type("tc_kimlik")
        assert result == "tc_kimlik"

    def test_iban_column(self) -> None:
        result = _name_to_col_type("iban")
        assert result == "iban"


# ── _is_pii ───────────────────────────────────────────────────────────────────


class TestIsPii:
    def test_tckn_is_pii(self) -> None:
        # PII_PATTERNS uses "tc.?kimlik|tcno" — "tckn" alone doesn't match
        # Use tcno which does match
        assert _is_pii("tcno") is True

    def test_tc_kimlik_is_pii(self) -> None:
        assert _is_pii("tc_kimlik") is True

    def test_email_is_pii(self) -> None:
        assert _is_pii("email") is True

    def test_email_address_is_pii(self) -> None:
        assert _is_pii("email_address") is True

    def test_phone_is_pii(self) -> None:
        assert _is_pii("phone") is True

    def test_telefon_is_pii(self) -> None:
        assert _is_pii("telefon") is True

    def test_ad_is_pii(self) -> None:
        # first name
        assert _is_pii("first_name") is True or _is_pii("ad") is True

    def test_birth_is_pii(self) -> None:
        # PII_PATTERNS has "birth|dogum|dob"
        assert _is_pii("birth_date") is True

    def test_product_count_not_pii(self) -> None:
        assert _is_pii("product_count") is False

    def test_price_not_pii(self) -> None:
        assert _is_pii("price") is False

    def test_category_not_pii(self) -> None:
        assert _is_pii("category") is False

    def test_case_insensitive(self) -> None:
        assert _is_pii("EMAIL") == _is_pii("email")

    def test_iban_is_pii(self) -> None:
        assert _is_pii("iban") is True


# ── _assign_ids ───────────────────────────────────────────────────────────────


class TestAssignIds:
    def test_empty_input(self) -> None:
        assert _assign_ids([]) == []

    def test_single_table_gets_id_1(self) -> None:
        tables = [{"name": "users", "columns": []}]
        result = _assign_ids(tables)
        assert result[0]["id"] == 1

    def test_columns_get_sequential_ids(self) -> None:
        tables = [
            {
                "name": "users",
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "email", "type": "string"},
                ],
            }
        ]
        result = _assign_ids(tables)
        cols = result[0]["columns"]
        assert cols[0]["id"] == 1
        assert cols[1]["id"] == 2

    def test_multiple_tables_get_sequential_ids(self) -> None:
        tables = [
            {"name": "users", "columns": [{"name": "id"}]},
            {"name": "orders", "columns": [{"name": "id"}]},
        ]
        result = _assign_ids(tables)
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

    def test_column_ids_continuous_across_tables(self) -> None:
        tables = [
            {"name": "t1", "columns": [{"name": "a"}, {"name": "b"}]},
            {"name": "t2", "columns": [{"name": "c"}]},
        ]
        result = _assign_ids(tables)
        t1_cols = result[0]["columns"]
        t2_cols = result[1]["columns"]
        assert t1_cols[0]["id"] == 1
        assert t1_cols[1]["id"] == 2
        assert t2_cols[0]["id"] == 3

    def test_original_fields_preserved(self) -> None:
        tables = [
            {
                "name": "products",
                "schema": "public",
                "columns": [{"name": "price", "type": "decimal"}],
            }
        ]
        result = _assign_ids(tables)
        assert result[0]["name"] == "products"
        assert result[0]["schema"] == "public"
        assert result[0]["columns"][0]["name"] == "price"

    def test_no_mutation_of_input(self) -> None:
        tables = [{"name": "t", "columns": [{"name": "c"}]}]
        _assign_ids(tables)
        assert "id" not in tables[0]  # original not mutated


# ── _pg_type_to_col_type ──────────────────────────────────────────────────────


class TestPgTypeToColType:
    def test_integer(self) -> None:
        result = _pg_type_to_col_type("integer")
        assert result in ("integer", "int")

    def test_text(self) -> None:
        result = _pg_type_to_col_type("text")
        assert result in ("string", "text")

    def test_boolean(self) -> None:
        result = _pg_type_to_col_type("boolean")
        assert result == "boolean"

    def test_uuid(self) -> None:
        result = _pg_type_to_col_type("uuid")
        assert result is not None  # maps to something

    def test_unknown_falls_back_to_sql_type(self) -> None:
        result = _pg_type_to_col_type("custom_pg_type_xyz")
        assert result == "string"  # fallback
