"""CoverUp parser'ları için ünite testleri.

Amaç: istanbul / cobertura / nyc formatlarının gerçekten parse edildiğini
doğrula. Daha önce bu formatlar `_parse_generic` ile boş liste dönüyordu,
UI "0 dosya" gösteriyordu.
"""

from __future__ import annotations

import json

from app.domains.coverup.parsers import (
    parse_cobertura,
    parse_istanbul,
    parse_nyc,
)


# ── Cobertura ──────────────────────────────────────────────────────────────
COBERTURA_SAMPLE = """<?xml version="1.0"?>
<coverage line-rate="0.75" branch-rate="0.5">
  <packages>
    <package name="app">
      <classes>
        <class filename="src/auth.py" line-rate="0.66">
          <methods>
            <method name="login" signature="()">
              <lines>
                <line number="10" hits="3"/>
                <line number="11" hits="3"/>
              </lines>
            </method>
            <method name="logout" signature="()">
              <lines>
                <line number="20" hits="0"/>
              </lines>
            </method>
          </methods>
          <lines>
            <line number="10" hits="3" branch="false"/>
            <line number="11" hits="3" branch="false"/>
            <line number="20" hits="0" branch="false"/>
            <line number="25" hits="1" branch="true" condition-coverage="50% (1/2)"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""


def test_cobertura_parser_extracts_lines_and_branches() -> None:
    files = parse_cobertura(COBERTURA_SAMPLE)
    assert len(files) == 1
    f = files[0]
    assert f["file_path"] == "src/auth.py"
    assert sorted(f["lines_hit"]) == [10, 11, 25]
    assert sorted(f["lines_missed"]) == [20]
    assert f["branches_total"] == 2
    assert f["branches_hit"] == 1
    assert f["functions_total"] == 2
    assert f["functions_hit"] == 1


def test_cobertura_parser_handles_malformed_xml() -> None:
    assert parse_cobertura("<not-xml>") == []
    assert parse_cobertura("") == []


# ── Istanbul ───────────────────────────────────────────────────────────────
ISTANBUL_SAMPLE = json.dumps({
    "src/a.js": {
        "path": "src/a.js",
        "statementMap": {
            "0": {"start": {"line": 1, "column": 0}, "end": {"line": 1, "column": 10}},
            "1": {"start": {"line": 2, "column": 0}, "end": {"line": 2, "column": 10}},
            "2": {"start": {"line": 5, "column": 0}, "end": {"line": 5, "column": 10}},
        },
        "s": {"0": 3, "1": 0, "2": 1},
        "branchMap": {"0": {"line": 2, "type": "if"}},
        "b": {"0": [1, 0]},
        "fnMap": {"0": {"name": "foo"}, "1": {"name": "bar"}},
        "f": {"0": 2, "1": 0},
    }
})


def test_istanbul_parser_maps_statements_and_branches() -> None:
    files = parse_istanbul(ISTANBUL_SAMPLE)
    assert len(files) == 1
    f = files[0]
    assert f["file_path"] == "src/a.js"
    assert 1 in f["lines_hit"]
    assert 5 in f["lines_hit"]
    assert 2 in f["lines_missed"]
    assert f["branches_total"] == 2
    assert f["branches_hit"] == 1
    assert f["functions_total"] == 2
    assert f["functions_hit"] == 1


def test_istanbul_parser_handles_empty() -> None:
    assert parse_istanbul("{}") == []
    assert parse_istanbul("invalid") == []


# ── nyc ────────────────────────────────────────────────────────────────────
NYC_SUMMARY = json.dumps({
    "total": {
        "lines": {"total": 10, "covered": 7, "skipped": 0, "pct": 70},
        "statements": {"total": 10, "covered": 7, "skipped": 0, "pct": 70},
        "functions": {"total": 4, "covered": 3, "skipped": 0, "pct": 75},
        "branches": {"total": 6, "covered": 4, "skipped": 0, "pct": 66},
    },
    "src/b.js": {
        "lines": {"total": 10, "covered": 7, "skipped": 0, "pct": 70},
        "statements": {"total": 10, "covered": 7, "skipped": 0, "pct": 70},
        "functions": {"total": 4, "covered": 3, "skipped": 0, "pct": 75},
        "branches": {"total": 6, "covered": 4, "skipped": 0, "pct": 66},
    },
})


def test_nyc_summary_parser_uses_aggregate_counts() -> None:
    files = parse_nyc(NYC_SUMMARY)
    assert len(files) == 1
    f = files[0]
    assert f["file_path"] == "src/b.js"
    assert len(f["lines_hit"]) == 7
    assert len(f["lines_missed"]) == 3
    assert f["branches_total"] == 6
    assert f["branches_hit"] == 4
    assert f["functions_total"] == 4
    assert f["functions_hit"] == 3


def test_nyc_delegates_to_istanbul_for_final_json() -> None:
    """nyc `coverage-final.json` yapısı istanbul ile birebir aynı — delegate etmeli."""
    files = parse_nyc(ISTANBUL_SAMPLE)
    assert len(files) == 1
    assert files[0]["file_path"] == "src/a.js"
