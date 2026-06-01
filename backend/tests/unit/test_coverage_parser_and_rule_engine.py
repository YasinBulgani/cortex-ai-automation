"""Unit tests for coverup.coverage_parser and ai_synthetic_data.platform.rule_engine.

Tests are fully self-contained: no DB, no HTTP, no pandas.
Covers:
  - CoverageParser.detect_format: LCOV, Cobertura XML, Istanbul JSON, Coverage.py JSON
  - CoverageParser.parse: dispatch to correct sub-parser, unknown format raises
  - CoverageParser.parse_lcov: line/branch/function coverage extraction
  - CoverageParser.parse_istanbul: statement/branch/function from NYC/Istanbul JSON
  - CoverageParser.parse_cobertura: Cobertura XML line+branch parsing
  - CoverageParser.parse_coveragepy: coverage.py JSON format
  - RuleEngine.infer_rules: faker passthrough, range, enum, sequential, datetime, string
  - RuleEngine._infer_temporal_rules: created_at/updated_at pair detection
"""
from __future__ import annotations

import json
import pytest

try:
    from app.domains.coverup.coverage_parser import CoverageParser
    _PARSER_OK = True
except ImportError:
    _PARSER_OK = False

try:
    from app.domains.ai_synthetic_data.platform.rule_engine import RuleEngine
    _RULE_OK = True
except ImportError:
    _RULE_OK = False


# ---------------------------------------------------------------------------
# Helpers — sample coverage data
# ---------------------------------------------------------------------------

_LCOV_SAMPLE = """TN:
SF:src/app.js
FN:1,login
FNDA:5,login
FNF:1
FNH:1
DA:1,5
DA:2,3
DA:3,0
BRDA:2,0,0,2
BRDA:2,0,1,0
LF:3
LH:2
end_of_record
"""

_ISTANBUL_SAMPLE = json.dumps({
    "src/login.js": {
        "s": {"0": 5, "1": 3, "2": 0},
        "statementMap": {
            "0": {"start": {"line": 1}, "end": {"line": 1}},
            "1": {"start": {"line": 2}, "end": {"line": 2}},
            "2": {"start": {"line": 3}, "end": {"line": 3}},
        },
        "b": {"0": [2, 0]},
        "branchMap": {
            "0": {"type": "if", "loc": {"start": {"line": 2}}}
        },
        "f": {"0": 5, "1": 0},
        "fnMap": {
            "0": {"name": "login"},
            "1": {"name": "logout"},
        },
    }
})

_COBERTURA_SAMPLE = """<?xml version="1.0" ?>
<coverage line-rate="0.8" branch-rate="0.5">
  <packages>
    <package name="app" line-rate="0.8" branch-rate="0.5">
      <classes>
        <class name="login" filename="src/login.py" line-rate="0.8" branch-rate="0.5">
          <methods>
            <method name="login_user" signature="">
              <lines><line number="1" hits="5"/></lines>
            </method>
            <method name="logout_user" signature="">
              <lines><line number="10" hits="0"/></lines>
            </method>
          </methods>
          <lines>
            <line number="1" hits="5" branch="false"/>
            <line number="2" hits="3" branch="true" condition-coverage="50% (1/2)"/>
            <line number="3" hits="0" branch="false"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""

_COVERAGEPY_SAMPLE = json.dumps({
    "meta": {"version": "7.0"},
    "files": {
        "src/login.py": {
            "executed_lines": [1, 2],
            "missing_lines": [3],
            "missing_branches": [[2, 4]],
            "summary": {
                "num_statements": 3,
                "covered_lines": 2,
                "missing_lines": 1,
                "num_branches": 2,
                "covered_branches": 1,
            },
        }
    },
    "totals": {},
})


# ---------------------------------------------------------------------------
# CoverageParser.detect_format
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PARSER_OK, reason="coverage_parser import failed")
class TestDetectFormat:
    def test_lcov_starts_with_tn(self):
        assert CoverageParser.detect_format("TN:\nSF:src/app.js") == "lcov"

    def test_lcov_starts_with_sf(self):
        assert CoverageParser.detect_format("SF:src/app.js\nDA:1,1") == "lcov"

    def test_cobertura_starts_with_xml(self):
        assert CoverageParser.detect_format("<?xml version='1.0'?><coverage") == "cobertura"

    def test_cobertura_starts_with_coverage_tag(self):
        assert CoverageParser.detect_format("<coverage line-rate='1.0'>") == "cobertura"

    def test_istanbul_format(self):
        assert CoverageParser.detect_format(_ISTANBUL_SAMPLE) == "istanbul"

    def test_coveragepy_format(self):
        assert CoverageParser.detect_format(_COVERAGEPY_SAMPLE) == "coveragepy"

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            CoverageParser.detect_format("plain text no format")


# ---------------------------------------------------------------------------
# CoverageParser.parse dispatch
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PARSER_OK, reason="coverage_parser import failed")
class TestParseDispatch:
    def test_lcov_dispatch(self):
        result = CoverageParser.parse("lcov", _LCOV_SAMPLE)
        assert "summary" in result
        assert "files" in result

    def test_istanbul_dispatch(self):
        result = CoverageParser.parse("istanbul", _ISTANBUL_SAMPLE)
        assert "files" in result

    def test_nyc_alias_dispatch(self):
        # nyc is an alias for istanbul
        result = CoverageParser.parse("nyc", _ISTANBUL_SAMPLE)
        assert "files" in result

    def test_cobertura_dispatch(self):
        result = CoverageParser.parse("cobertura", _COBERTURA_SAMPLE)
        assert "files" in result

    def test_coveragepy_dispatch(self):
        result = CoverageParser.parse("coveragepy", _COVERAGEPY_SAMPLE)
        assert "files" in result

    def test_unknown_format_raises(self):
        with pytest.raises(ValueError):
            CoverageParser.parse("junit", "<testsuite/>")

    def test_case_insensitive(self):
        result = CoverageParser.parse("LCOV", _LCOV_SAMPLE)
        assert "files" in result

    def test_strips_whitespace(self):
        result = CoverageParser.parse("  lcov  ", _LCOV_SAMPLE)
        assert "files" in result


# ---------------------------------------------------------------------------
# CoverageParser.parse_lcov
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PARSER_OK, reason="coverage_parser import failed")
class TestParseLcov:
    def _parsed(self):
        return CoverageParser.parse_lcov(_LCOV_SAMPLE)

    def test_returns_summary_and_files(self):
        result = self._parsed()
        assert "summary" in result
        assert "files" in result

    def test_file_count(self):
        result = self._parsed()
        assert result["summary"]["total_files"] == 1

    def test_file_path(self):
        result = self._parsed()
        assert result["files"][0]["file_path"] == "src/app.js"

    def test_total_lines(self):
        # DA:1, DA:2, DA:3 → 3 lines
        result = self._parsed()
        assert result["files"][0]["total_lines"] == 3

    def test_covered_lines(self):
        # DA:1,5 and DA:2,3 → 2 covered
        result = self._parsed()
        assert result["files"][0]["covered_lines"] == 2

    def test_missed_lines(self):
        result = self._parsed()
        assert result["files"][0]["missed_lines"] == 1

    def test_missed_line_numbers(self):
        result = self._parsed()
        assert 3 in result["files"][0]["missed_line_numbers"]

    def test_total_branches(self):
        # BRDA:2,0,0,2 and BRDA:2,0,1,0 → 2 branches
        result = self._parsed()
        assert result["files"][0]["total_branches"] == 2

    def test_covered_branches(self):
        # BRDA:2,0,0,2 (taken=2 → covered), BRDA:2,0,1,0 (taken=0 → missed)
        result = self._parsed()
        assert result["files"][0]["covered_branches"] == 1

    def test_line_rate(self):
        result = self._parsed()
        assert result["files"][0]["line_rate"] == pytest.approx(2 / 3, rel=1e-3)

    def test_summary_aggregates(self):
        result = self._parsed()
        s = result["summary"]
        assert s["total_lines"] == 3
        assert s["covered_lines"] == 2

    def test_empty_lcov(self):
        result = CoverageParser.parse_lcov("")
        assert result["summary"]["total_files"] == 0
        assert result["files"] == []


# ---------------------------------------------------------------------------
# CoverageParser.parse_istanbul
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PARSER_OK, reason="coverage_parser import failed")
class TestParseIstanbul:
    def _parsed(self):
        return CoverageParser.parse_istanbul(_ISTANBUL_SAMPLE)

    def test_file_count(self):
        result = self._parsed()
        assert result["summary"]["total_files"] == 1

    def test_file_path(self):
        result = self._parsed()
        assert result["files"][0]["file_path"] == "src/login.js"

    def test_covered_lines(self):
        # statements 0 and 1 have hits > 0
        result = self._parsed()
        assert result["files"][0]["covered_lines"] == 2

    def test_missed_lines(self):
        # statement 2 has 0 hits
        result = self._parsed()
        assert result["files"][0]["missed_lines"] == 1

    def test_total_branches(self):
        # b: {"0": [2, 0]} → 2 branches
        result = self._parsed()
        assert result["files"][0]["total_branches"] == 2

    def test_covered_branches(self):
        # first branch hit=2, second=0 → 1 covered
        result = self._parsed()
        assert result["files"][0]["covered_branches"] == 1

    def test_total_functions(self):
        # f: {"0": 5, "1": 0} → 2 functions
        result = self._parsed()
        assert result["files"][0]["total_functions"] == 2

    def test_covered_functions(self):
        # function 0 has hits=5, function 1 has hits=0
        result = self._parsed()
        assert result["files"][0]["covered_functions"] == 1

    def test_uncovered_functions(self):
        result = self._parsed()
        assert "logout" in result["files"][0]["uncovered_functions"]

    def test_returns_dict(self):
        result = self._parsed()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# CoverageParser.parse_cobertura
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PARSER_OK, reason="coverage_parser import failed")
class TestParseCobertura:
    def _parsed(self):
        return CoverageParser.parse_cobertura(_COBERTURA_SAMPLE)

    def test_file_count(self):
        result = self._parsed()
        assert result["summary"]["total_files"] == 1

    def test_file_path(self):
        result = self._parsed()
        assert result["files"][0]["file_path"] == "src/login.py"

    def test_total_lines(self):
        # iter("line") collects method lines (1, 10) + class lines (1, 2, 3)
        # Unique line numbers: {1, 2, 3, 10} → 4 total
        result = self._parsed()
        assert result["files"][0]["total_lines"] == 4

    def test_covered_lines(self):
        # line 1=5 hits, line 2=3 hits → 2 covered (3=0 hits, 10=0 hits)
        result = self._parsed()
        assert result["files"][0]["covered_lines"] == 2

    def test_missed_lines(self):
        # lines 3 and 10 have 0 hits
        result = self._parsed()
        assert result["files"][0]["missed_lines"] == 2

    def test_branch_data_parsed(self):
        # line 2 has condition-coverage="50% (1/2)" → total=2, covered=1
        result = self._parsed()
        f = result["files"][0]
        assert f["total_branches"] == 2
        assert f["covered_branches"] == 1

    def test_function_coverage(self):
        # login_user has hit, logout_user has 0 hits
        result = self._parsed()
        f = result["files"][0]
        assert f["total_functions"] == 2
        assert f["covered_functions"] == 1

    def test_uncovered_functions(self):
        result = self._parsed()
        assert "logout_user" in result["files"][0]["uncovered_functions"]


# ---------------------------------------------------------------------------
# CoverageParser.parse_coveragepy
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PARSER_OK, reason="coverage_parser import failed")
class TestParseCoveragepy:
    def _parsed(self):
        return CoverageParser.parse_coveragepy(_COVERAGEPY_SAMPLE)

    def test_file_count(self):
        result = self._parsed()
        assert result["summary"]["total_files"] == 1

    def test_file_path(self):
        result = self._parsed()
        assert result["files"][0]["file_path"] == "src/login.py"

    def test_covered_lines(self):
        result = self._parsed()
        assert result["files"][0]["covered_lines"] == 2

    def test_missed_lines(self):
        result = self._parsed()
        assert result["files"][0]["missed_lines"] == 1

    def test_missing_line_numbers(self):
        result = self._parsed()
        assert 3 in result["files"][0]["missed_line_numbers"]

    def test_branch_data(self):
        result = self._parsed()
        f = result["files"][0]
        assert f["total_branches"] == 2
        assert f["covered_branches"] == 1

    def test_missed_branch_line(self):
        # missing_branches = [[2, 4]] → branch starts at line 2
        result = self._parsed()
        assert 2 in result["files"][0]["missed_branch_lines"]

    def test_no_function_data(self):
        # Coverage.py JSON has no function-level data by default
        result = self._parsed()
        assert result["files"][0]["total_functions"] == 0
        assert result["files"][0]["covered_functions"] == 0


# ---------------------------------------------------------------------------
# RuleEngine.infer_rules — faker passthrough
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RULE_OK, reason="rule_engine import failed")
class TestRuleEngineFaker:
    def test_faker_rule_when_faker_config_present(self):
        engine = RuleEngine()
        schema = {
            "columns": [{
                "name": "email",
                "faker_config": {"provider": "email"},
                "classification": "pii_email",
            }]
        }
        rules = engine.infer_rules(schema)
        faker_rules = [r for r in rules if r["rule_type"] == "faker"]
        assert len(faker_rules) == 1

    def test_faker_rule_column_name(self):
        engine = RuleEngine()
        schema = {
            "columns": [{
                "name": "email",
                "faker_config": {"provider": "email"},
            }]
        }
        rules = engine.infer_rules(schema)
        assert rules[0]["column_name"] == "email"

    def test_faker_rule_config_preserved(self):
        engine = RuleEngine()
        cfg = {"provider": "name", "locale": "tr_TR"}
        schema = {"columns": [{"name": "full_name", "faker_config": cfg}]}
        rules = engine.infer_rules(schema)
        assert rules[0]["rule_config"] == cfg

    def test_faker_short_circuits_other_rules(self):
        # When faker_config present, min/max stats should NOT produce range rule
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "amount",
            "faker_config": {"provider": "pydecimal"},
            "stats": {"min": 0, "max": 100},
        }]}
        rules = engine.infer_rules(schema)
        types = [r["rule_type"] for r in rules]
        assert "range" not in types
        assert "faker" in types


# ---------------------------------------------------------------------------
# RuleEngine.infer_rules — range
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RULE_OK, reason="rule_engine import failed")
class TestRuleEngineRange:
    def test_range_rule_when_min_max_present(self):
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "amount",
            "stats": {"min": 10, "max": 1000},
        }]}
        rules = engine.infer_rules(schema)
        range_rules = [r for r in rules if r["rule_type"] == "range"]
        assert len(range_rules) == 1

    def test_range_uniform_when_no_mean_std(self):
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "score",
            "stats": {"min": 0, "max": 100},
        }]}
        rules = engine.infer_rules(schema)
        r = next(r for r in rules if r["rule_type"] == "range")
        assert r["rule_config"]["distribution"] == "uniform"

    def test_range_normal_when_mean_std_present(self):
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "age",
            "stats": {"min": 18, "max": 80, "mean": 40.0, "std": 12.0},
        }]}
        rules = engine.infer_rules(schema)
        r = next(r for r in rules if r["rule_type"] == "range")
        assert r["rule_config"]["distribution"] == "normal"
        assert r["rule_config"]["mean"] == pytest.approx(40.0)

    def test_range_min_max_in_config(self):
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "price",
            "stats": {"min": 5, "max": 500},
        }]}
        rules = engine.infer_rules(schema)
        r = next(r for r in rules if r["rule_type"] == "range")
        assert r["rule_config"]["min"] == 5
        assert r["rule_config"]["max"] == 500


# ---------------------------------------------------------------------------
# RuleEngine.infer_rules — enum
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RULE_OK, reason="rule_engine import failed")
class TestRuleEngineEnum:
    def test_enum_rule_for_classification(self):
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "status",
            "classification": "enum",
            "stats": {"top_values": {"active": 80, "inactive": 20}},
        }]}
        rules = engine.infer_rules(schema)
        enum_rules = [r for r in rules if r["rule_type"] == "enum"]
        assert len(enum_rules) == 1

    def test_enum_values_and_weights(self):
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "status",
            "classification": "enum",
            "stats": {"top_values": {"active": 80, "inactive": 20}},
        }]}
        rules = engine.infer_rules(schema)
        r = next(r for r in rules if r["rule_type"] == "enum")
        assert "active" in r["rule_config"]["values"]
        assert 80 in r["rule_config"]["weights"]


# ---------------------------------------------------------------------------
# RuleEngine.infer_rules — sequential (ID)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RULE_OK, reason="rule_engine import failed")
class TestRuleEngineSequential:
    def test_sequential_rule_for_id_classification(self):
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "user_id",
            "classification": "id",
            "stats": {"min": 1},
        }]}
        rules = engine.infer_rules(schema)
        seq_rules = [r for r in rules if r["rule_type"] == "sequential"]
        assert len(seq_rules) == 1

    def test_sequential_start_from_min(self):
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "id",
            "classification": "id",
            "stats": {"min": 100},
        }]}
        rules = engine.infer_rules(schema)
        r = next(r for r in rules if r["rule_type"] == "sequential")
        assert r["rule_config"]["start"] == 100
        assert r["rule_config"]["step"] == 1


# ---------------------------------------------------------------------------
# RuleEngine.infer_rules — datetime
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RULE_OK, reason="rule_engine import failed")
class TestRuleEngineDateTime:
    def test_date_range_rule_for_datetime(self):
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "created_at",
            "classification": "datetime",
            "stats": {"min_date": "2022-01-01", "max_date": "2024-12-31"},
        }]}
        rules = engine.infer_rules(schema)
        date_rules = [r for r in rules if r["rule_type"] == "date_range"]
        assert len(date_rules) == 1

    def test_date_range_config(self):
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "txn_date",
            "classification": "datetime",
            "stats": {"min_date": "2023-01-01", "max_date": "2024-06-30"},
        }]}
        rules = engine.infer_rules(schema)
        r = next(r for r in rules if r["rule_type"] == "date_range")
        assert r["rule_config"]["start_date"] == "2023-01-01"
        assert r["rule_config"]["end_date"] == "2024-06-30"


# ---------------------------------------------------------------------------
# RuleEngine.infer_rules — nullable
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RULE_OK, reason="rule_engine import failed")
class TestRuleEngineNullable:
    def test_nullable_rule_added_when_null_ratio_gt_zero(self):
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "notes",
            "null_ratio": 0.3,
            "stats": {"min_length": 0, "max_length": 200},
        }]}
        rules = engine.infer_rules(schema)
        null_rules = [r for r in rules if r["rule_type"] == "nullable"]
        assert len(null_rules) == 1
        assert null_rules[0]["rule_config"]["null_ratio"] == pytest.approx(0.3)

    def test_no_nullable_rule_when_zero_ratio(self):
        engine = RuleEngine()
        schema = {"columns": [{
            "name": "email",
            "null_ratio": 0,
            "stats": {"min": 1, "max": 100},
        }]}
        rules = engine.infer_rules(schema)
        null_rules = [r for r in rules if r["rule_type"] == "nullable"]
        assert len(null_rules) == 0


# ---------------------------------------------------------------------------
# RuleEngine.infer_rules — temporal order
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RULE_OK, reason="rule_engine import failed")
class TestRuleEngineTemporalOrder:
    def test_temporal_rule_for_created_updated(self):
        engine = RuleEngine()
        schema = {"columns": [
            {"name": "created_at", "classification": "datetime", "stats": {}},
            {"name": "updated_at", "classification": "datetime", "stats": {}},
        ]}
        rules = engine.infer_rules(schema)
        temporal_rules = [r for r in rules if r["rule_type"] == "temporal_order"]
        assert len(temporal_rules) == 1

    def test_temporal_rule_column_name_is_after(self):
        engine = RuleEngine()
        schema = {"columns": [
            {"name": "created_at", "classification": "datetime", "stats": {}},
            {"name": "updated_at", "classification": "datetime", "stats": {}},
        ]}
        rules = engine.infer_rules(schema)
        r = next(r for r in rules if r["rule_type"] == "temporal_order")
        assert r["column_name"] == "updated_at"
        assert r["rule_config"]["after_column"] == "created_at"

    def test_no_temporal_rule_if_only_one_datetime(self):
        engine = RuleEngine()
        schema = {"columns": [
            {"name": "created_at", "classification": "datetime", "stats": {}},
        ]}
        rules = engine.infer_rules(schema)
        temporal_rules = [r for r in rules if r["rule_type"] == "temporal_order"]
        assert len(temporal_rules) == 0

    def test_open_close_date_pair(self):
        engine = RuleEngine()
        schema = {"columns": [
            {"name": "open_date", "classification": "datetime", "stats": {}},
            {"name": "close_date", "classification": "datetime", "stats": {}},
        ]}
        rules = engine.infer_rules(schema)
        temporal_rules = [r for r in rules if r["rule_type"] == "temporal_order"]
        assert len(temporal_rules) == 1
        assert temporal_rules[0]["rule_config"]["after_column"] == "open_date"

    def test_empty_schema_returns_empty_rules(self):
        engine = RuleEngine()
        rules = engine.infer_rules({"columns": []})
        assert rules == []

    def test_rules_is_list(self):
        engine = RuleEngine()
        result = engine.infer_rules({"columns": []})
        assert isinstance(result, list)
