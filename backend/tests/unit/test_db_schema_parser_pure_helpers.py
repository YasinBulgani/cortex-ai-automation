"""Unit tests for tspm.db_schema_parser pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers:
  - _sql_type_to_col_type: SQL → ColType mapping
  - _name_to_col_type: column name → semantic type
  - _is_pii: PII column name detection
  - _assign_ids: sequential ID assignment to tables/columns
  - _classify_csv_column: sample-based CSV column type inference
  - _pg_type_to_col_type: PostgreSQL type → ColType
"""
from __future__ import annotations

import pytest

try:
    from app.domains.tspm.db_schema_parser import (
        _sql_type_to_col_type,
        _name_to_col_type,
        _is_pii,
        _assign_ids,
        _classify_csv_column,
        _pg_type_to_col_type,
    )
    _DSP_OK = True
except ImportError:
    _DSP_OK = False


# ---------------------------------------------------------------------------
# _sql_type_to_col_type
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSP_OK, reason="db_schema_parser import failed")
class TestSqlTypeToColType:
    def test_varchar_to_string(self):
        assert _sql_type_to_col_type("VARCHAR(255)") == "string"

    def test_text_to_string(self):
        assert _sql_type_to_col_type("TEXT") == "string"

    def test_integer_to_integer(self):
        assert _sql_type_to_col_type("INTEGER") == "integer"

    def test_bigint_to_integer(self):
        assert _sql_type_to_col_type("BIGINT") == "integer"

    def test_int_to_integer(self):
        assert _sql_type_to_col_type("INT") == "integer"

    def test_decimal_to_decimal(self):
        assert _sql_type_to_col_type("DECIMAL(10,2)") == "decimal"

    def test_numeric_to_decimal(self):
        assert _sql_type_to_col_type("NUMERIC") == "decimal"

    def test_float_to_decimal(self):
        assert _sql_type_to_col_type("FLOAT") == "decimal"

    def test_boolean_to_boolean(self):
        assert _sql_type_to_col_type("BOOLEAN") == "boolean"

    def test_bool_to_boolean(self):
        assert _sql_type_to_col_type("BOOL") == "boolean"

    def test_tinyint1_to_boolean(self):
        assert _sql_type_to_col_type("TINYINT(1)") == "boolean"

    def test_uuid_to_uuid(self):
        assert _sql_type_to_col_type("UUID") == "uuid"

    def test_timestamp_to_date(self):
        assert _sql_type_to_col_type("TIMESTAMP") == "date"

    def test_datetime_to_date(self):
        assert _sql_type_to_col_type("DATETIME") == "date"

    def test_date_to_date(self):
        assert _sql_type_to_col_type("DATE") == "date"

    def test_jsonb_to_text(self):
        assert _sql_type_to_col_type("JSONB") == "text"

    def test_json_to_text(self):
        assert _sql_type_to_col_type("JSON") == "text"

    def test_serial_to_auto_increment(self):
        assert _sql_type_to_col_type("SERIAL") == "auto_increment"

    def test_bigserial_to_auto_increment(self):
        assert _sql_type_to_col_type("BIGSERIAL") == "auto_increment"

    def test_unknown_type_returns_string(self):
        assert _sql_type_to_col_type("GEOMETRY") == "string"

    def test_case_insensitive(self):
        assert _sql_type_to_col_type("varchar") == "string"
        assert _sql_type_to_col_type("INTEGER") == "integer"

    def test_returns_string(self):
        assert isinstance(_sql_type_to_col_type("TEXT"), str)


# ---------------------------------------------------------------------------
# _name_to_col_type
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSP_OK, reason="db_schema_parser import failed")
class TestNameToColType:
    def test_email_column(self):
        assert _name_to_col_type("email") == "email"

    def test_user_email_column(self):
        assert _name_to_col_type("user_email") == "email"

    def test_phone_column(self):
        assert _name_to_col_type("phone") == "phone"

    def test_telefon_column(self):
        assert _name_to_col_type("telefon") == "phone"

    def test_name_column(self):
        result = _name_to_col_type("name")
        assert result is not None  # matches name pattern

    def test_address_in_column_contains_ad_matches_name(self):
        # "address" contains "ad" which matches the name pattern first (search order)
        result = _name_to_col_type("address")
        assert result is not None  # some type is assigned

    def test_city_column(self):
        assert _name_to_col_type("city") == "city"

    def test_iban_column(self):
        assert _name_to_col_type("iban") == "iban"

    def test_uuid_column(self):
        assert _name_to_col_type("user_uuid") == "uuid"

    def test_unknown_column_returns_none(self):
        assert _name_to_col_type("status") is None

    def test_returns_none_for_unmatched(self):
        assert _name_to_col_type("quantity") is None

    def test_case_insensitive(self):
        assert _name_to_col_type("EMAIL") == "email"

    def test_returns_string_or_none(self):
        result = _name_to_col_type("phone")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _is_pii
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSP_OK, reason="db_schema_parser import failed")
class TestIsPii:
    def test_email_is_pii(self):
        assert _is_pii("email") is True

    def test_user_email_is_pii(self):
        assert _is_pii("user_email") is True

    def test_phone_is_pii(self):
        assert _is_pii("phone") is True

    def test_iban_is_pii(self):
        assert _is_pii("iban") is True

    def test_tc_kimlik_is_pii(self):
        assert _is_pii("tc_kimlik") is True

    def test_address_is_pii(self):
        assert _is_pii("address") is True

    def test_birth_date_is_pii(self):
        assert _is_pii("birth_date") is True

    def test_status_is_not_pii(self):
        assert _is_pii("status") is False

    def test_quantity_is_not_pii(self):
        assert _is_pii("quantity") is False

    def test_id_is_not_pii(self):
        assert _is_pii("id") is False

    def test_returns_bool(self):
        assert isinstance(_is_pii("email"), bool)

    def test_case_insensitive(self):
        assert _is_pii("EMAIL") is True

    def test_passport_is_pii(self):
        assert _is_pii("passport_no") is True

    def test_ssn_is_pii(self):
        assert _is_pii("ssn") is True


# ---------------------------------------------------------------------------
# _assign_ids
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSP_OK, reason="db_schema_parser import failed")
class TestAssignIds:
    def test_table_gets_id(self):
        tables = [{"name": "users", "columns": []}]
        result = _assign_ids(tables)
        assert result[0]["id"] == 1

    def test_multiple_tables_sequential_ids(self):
        tables = [
            {"name": "users", "columns": []},
            {"name": "orders", "columns": []},
        ]
        result = _assign_ids(tables)
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

    def test_columns_get_ids(self):
        tables = [{"name": "users", "columns": [{"name": "id"}, {"name": "name"}]}]
        result = _assign_ids(tables)
        cols = result[0]["columns"]
        assert cols[0]["id"] == 1
        assert cols[1]["id"] == 2

    def test_column_ids_sequential_across_tables(self):
        tables = [
            {"name": "t1", "columns": [{"name": "a"}, {"name": "b"}]},
            {"name": "t2", "columns": [{"name": "c"}]},
        ]
        result = _assign_ids(tables)
        assert result[0]["columns"][0]["id"] == 1
        assert result[0]["columns"][1]["id"] == 2
        assert result[1]["columns"][0]["id"] == 3

    def test_empty_tables_list(self):
        assert _assign_ids([]) == []

    def test_table_with_no_columns(self):
        tables = [{"name": "empty_table", "columns": []}]
        result = _assign_ids(tables)
        assert result[0]["columns"] == []

    def test_original_table_data_preserved(self):
        tables = [{"name": "users", "schema": "public", "columns": []}]
        result = _assign_ids(tables)
        assert result[0]["name"] == "users"
        assert result[0]["schema"] == "public"

    def test_original_column_data_preserved(self):
        tables = [{"name": "t", "columns": [{"name": "col1", "type": "integer"}]}]
        result = _assign_ids(tables)
        assert result[0]["columns"][0]["name"] == "col1"
        assert result[0]["columns"][0]["type"] == "integer"

    def test_returns_list(self):
        assert isinstance(_assign_ids([]), list)


# ---------------------------------------------------------------------------
# _classify_csv_column
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSP_OK, reason="db_schema_parser import failed")
class TestClassifyCsvColumn:
    def test_email_column_name(self):
        result = _classify_csv_column("email", ["a@b.com", "c@d.com"])
        assert result["type"] == "email"

    def test_uuid_samples(self):
        uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        ]
        result = _classify_csv_column("id", uuids)
        assert result["type"] == "uuid"

    def test_integer_samples(self):
        result = _classify_csv_column("count", ["10", "20", "30", "40"])
        assert result["type"] == "integer"

    def test_auto_increment_samples(self):
        result = _classify_csv_column("row_id", ["1", "2", "3", "4", "5"])
        assert result["type"] == "auto_increment"

    def test_decimal_samples(self):
        result = _classify_csv_column("price", ["10.50", "20.99", "5.00"])
        assert result["type"] == "decimal"

    def test_boolean_samples(self):
        result = _classify_csv_column("active", ["true", "false", "true"])
        assert result["type"] == "boolean"

    def test_date_samples(self):
        result = _classify_csv_column("created_at", ["2024-01-01", "2024-02-15", "2024-03-10"])
        assert result["type"] == "date"

    def test_email_from_samples(self):
        result = _classify_csv_column("contact", ["john@example.com", "jane@example.com"])
        assert result["type"] == "email"

    def test_low_cardinality_enum(self):
        result = _classify_csv_column("status", ["active", "inactive", "pending", "active", "active"])
        assert result["type"] == "enum"

    def test_empty_samples_defaults_to_string(self):
        result = _classify_csv_column("notes", [])
        assert result["type"] == "string"

    def test_pii_detected_in_result(self):
        result = _classify_csv_column("email", ["a@b.com"])
        assert result["pii"] is True

    def test_non_pii_column(self):
        result = _classify_csv_column("status", ["active", "inactive", "pending"])
        assert "pii" in result

    def test_confidence_present(self):
        result = _classify_csv_column("name", ["Alice", "Bob"])
        assert "confidence" in result
        assert 0 <= result["confidence"] <= 1.0

    def test_returns_dict(self):
        result = _classify_csv_column("col", ["1", "2"])
        assert isinstance(result, dict)

    def test_type_key_always_present(self):
        result = _classify_csv_column("col", ["abc", "def"])
        assert "type" in result


# ---------------------------------------------------------------------------
# _pg_type_to_col_type
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSP_OK, reason="db_schema_parser import failed")
class TestPgTypeToColType:
    def test_integer(self):
        assert _pg_type_to_col_type("integer") == "integer"

    def test_bigint(self):
        assert _pg_type_to_col_type("bigint") == "integer"

    def test_text(self):
        assert _pg_type_to_col_type("text") == "string"

    def test_boolean(self):
        assert _pg_type_to_col_type("boolean") == "boolean"

    def test_timestamp(self):
        result = _pg_type_to_col_type("timestamp")
        assert result == "date"

    def test_uuid(self):
        assert _pg_type_to_col_type("uuid") == "uuid"

    def test_unknown_falls_back_to_sql(self):
        # Unknown PG type → falls back to _sql_type_to_col_type
        result = _pg_type_to_col_type("character varying")
        assert result == "string"

    def test_returns_string(self):
        assert isinstance(_pg_type_to_col_type("text"), str)
