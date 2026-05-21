"""
CoverUp — Coverage rapor parser'ları.

Desteklenen formatlar:
  - LCOV (lcov.info) — Playwright/Jest/Vitest default
  - Istanbul JSON (coverage-final.json) — NYC/Istanbul
  - Cobertura XML (coverage.xml) — Python coverage, Java JaCoCo
  - Coverage.py JSON — Python coverage.py json output
"""
from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from typing import Any

logger = logging.getLogger(__name__)


class CoverageParser:
    """Multi-format coverage report parser."""

    # ------------------------------------------------------------------
    # Public dispatch
    # ------------------------------------------------------------------

    @staticmethod
    def parse(fmt: str, data: str) -> dict[str, Any]:
        """Ana dispatch — format'a göre doğru parser'ı çağır."""
        fmt = fmt.strip().lower()
        parsers: dict[str, Any] = {
            "lcov": CoverageParser.parse_lcov,
            "istanbul": CoverageParser.parse_istanbul,
            "nyc": CoverageParser.parse_istanbul,  # NYC = Istanbul wrapper
            "cobertura": CoverageParser.parse_cobertura,
            "coveragepy": CoverageParser.parse_coveragepy,
        }
        parser_fn = parsers.get(fmt)
        if parser_fn is None:
            raise ValueError(
                f"Desteklenmeyen coverage formatı: {fmt!r}. "
                f"Desteklenen: {', '.join(sorted(parsers))}"
            )
        return parser_fn(data)

    @staticmethod
    def detect_format(data: str) -> str:
        """Auto-detect format from content."""
        stripped = data.strip()

        # LCOV: starts with TN: or SF:
        if stripped.startswith("TN:") or stripped.startswith("SF:"):
            return "lcov"

        # XML-based (Cobertura)
        if stripped.startswith("<?xml") or stripped.startswith("<coverage"):
            return "cobertura"

        # JSON-based — Istanbul vs Coverage.py
        if stripped.startswith("{"):
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                raise ValueError("JSON parse hatası — format tespit edilemedi")

            # Coverage.py JSON has a "meta" key with "version"
            if "meta" in obj and "files" in obj:
                return "coveragepy"

            # Istanbul JSON: top-level keys are file paths, values have "s" dict
            first_val = next(iter(obj.values()), None)
            if isinstance(first_val, dict) and "s" in first_val:
                return "istanbul"

            raise ValueError("JSON formatı tanınamadı (istanbul veya coveragepy değil)")

        raise ValueError("Coverage rapor formatı tespit edilemedi")

    # ------------------------------------------------------------------
    # LCOV parser
    # ------------------------------------------------------------------

    @staticmethod
    def parse_lcov(data: str) -> dict[str, Any]:
        """Parse LCOV format (lcov.info).

        Supported records:
          SF:<file>  — source file
          DA:<line>,<hit>  — line data
          BRDA:<line>,<block>,<branch>,<taken>  — branch data
          FN:<line>,<name>  — function definition
          FNDA:<hits>,<name>  — function hit data
          FNF:<count>  — functions found
          FNH:<count>  — functions hit
          LF:<count>  — lines found
          LH:<count>  — lines hit
          end_of_record
        """
        files: list[dict[str, Any]] = []
        current_file: str | None = None
        line_hits: dict[int, int] = {}
        branch_data: list[tuple[int, int, int, int]] = []  # line, block, branch, taken
        fn_defs: dict[str, int] = {}  # name -> start_line
        fn_hits: dict[str, int] = {}  # name -> hit_count
        fn_found = 0
        fn_hit = 0

        def _flush() -> None:
            nonlocal current_file, line_hits, branch_data, fn_defs, fn_hits
            nonlocal fn_found, fn_hit
            if current_file is None:
                return

            total_lines = len(line_hits)
            covered_lines = sum(1 for h in line_hits.values() if h > 0)
            missed_lines = total_lines - covered_lines
            missed_line_numbers = sorted(ln for ln, h in line_hits.items() if h == 0)

            total_branches = len(branch_data)
            covered_branches = sum(1 for _, _, _, t in branch_data if t > 0)
            missed_branch_lines = sorted(
                {ln for ln, _, _, t in branch_data if t == 0}
            )

            uncovered_fns = [
                name for name, hits in fn_hits.items() if hits == 0
            ]

            line_rate = covered_lines / total_lines if total_lines else 0.0
            branch_rate = (
                covered_branches / total_branches if total_branches else 0.0
            )

            files.append(
                {
                    "file_path": current_file,
                    "total_lines": total_lines,
                    "covered_lines": covered_lines,
                    "missed_lines": missed_lines,
                    "line_rate": round(line_rate, 4),
                    "branch_rate": round(branch_rate, 4),
                    "total_branches": total_branches,
                    "covered_branches": covered_branches,
                    "total_functions": fn_found or len(fn_defs),
                    "covered_functions": fn_hit
                    or sum(1 for h in fn_hits.values() if h > 0),
                    "missed_line_numbers": missed_line_numbers,
                    "missed_branch_lines": missed_branch_lines,
                    "uncovered_functions": uncovered_fns,
                }
            )

            # reset
            current_file = None
            line_hits = {}
            branch_data = []
            fn_defs = {}
            fn_hits = {}
            fn_found = 0
            fn_hit = 0

        for raw_line in data.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("TN:"):
                continue

            if line.startswith("SF:"):
                _flush()
                current_file = line[3:]
                continue

            if line == "end_of_record":
                _flush()
                continue

            if line.startswith("DA:"):
                parts = line[3:].split(",")
                if len(parts) >= 2:
                    try:
                        ln = int(parts[0])
                        hits = int(parts[1])
                        line_hits[ln] = hits
                    except ValueError:
                        pass
                continue

            if line.startswith("BRDA:"):
                parts = line[5:].split(",")
                if len(parts) >= 4:
                    try:
                        ln = int(parts[0])
                        block = int(parts[1])
                        branch = int(parts[2])
                        taken = 0 if parts[3] == "-" else int(parts[3])
                        branch_data.append((ln, block, branch, taken))
                    except ValueError:
                        pass
                continue

            if line.startswith("FN:"):
                parts = line[3:].split(",", 1)
                if len(parts) == 2:
                    try:
                        start = int(parts[0])
                        fn_defs[parts[1]] = start
                    except ValueError:
                        pass
                continue

            if line.startswith("FNDA:"):
                parts = line[5:].split(",", 1)
                if len(parts) == 2:
                    try:
                        hits = int(parts[0])
                        fn_hits[parts[1]] = hits
                    except ValueError:
                        pass
                continue

            if line.startswith("FNF:"):
                try:
                    fn_found = int(line[4:])
                except ValueError:
                    pass
                continue

            if line.startswith("FNH:"):
                try:
                    fn_hit = int(line[4:])
                except ValueError:
                    pass
                continue

        # flush last record if no end_of_record
        _flush()

        return CoverageParser._build_result(files)

    # ------------------------------------------------------------------
    # Istanbul JSON parser
    # ------------------------------------------------------------------

    @staticmethod
    def parse_istanbul(data: str) -> dict[str, Any]:
        """Parse Istanbul / NYC JSON coverage (coverage-final.json).

        Structure per file:
          {
            "s": {"0": 5, "1": 0, ...},        # statement hits
            "b": {"0": [1, 0], ...},            # branch hits
            "f": {"0": 5, "1": 0, ...},         # function hits
            "statementMap": {"0": {"start": {"line": 1}, "end": {"line": 1}}, ...},
            "branchMap": {"0": {"loc": {...}, "type": "if", "locations": [...]}, ...},
            "fnMap": {"0": {"name": "login", "loc": {...}}, ...}
          }
        """
        obj = json.loads(data)
        files: list[dict[str, Any]] = []

        for file_path, cov in obj.items():
            if not isinstance(cov, dict):
                continue

            statements = cov.get("s", {})
            statement_map = cov.get("statementMap", {})
            branches = cov.get("b", {})
            branch_map = cov.get("branchMap", {})
            functions = cov.get("f", {})
            fn_map = cov.get("fnMap", {})

            # Lines covered/missed via statementMap
            line_hits: dict[int, int] = {}
            for sid, hits in statements.items():
                mapping = statement_map.get(sid, {})
                start = mapping.get("start", {})
                start_line = start.get("line")
                if start_line is not None:
                    # keep highest hit count per line
                    prev = line_hits.get(start_line, 0)
                    line_hits[start_line] = max(prev, int(hits))

            total_lines = len(line_hits)
            covered_lines = sum(1 for h in line_hits.values() if h > 0)
            missed_lines = total_lines - covered_lines
            missed_line_numbers = sorted(
                ln for ln, h in line_hits.items() if h == 0
            )

            # Branches
            total_branches = 0
            covered_branches = 0
            missed_branch_lines_set: set[int] = set()
            for bid, hits_list in branches.items():
                if not isinstance(hits_list, list):
                    continue
                bmap = branch_map.get(bid, {})
                loc = bmap.get("loc", {})
                branch_line = loc.get("start", {}).get("line")
                for h in hits_list:
                    total_branches += 1
                    if int(h) > 0:
                        covered_branches += 1
                    elif branch_line is not None:
                        missed_branch_lines_set.add(branch_line)

            # Functions
            total_functions = len(functions)
            covered_functions = sum(1 for h in functions.values() if int(h) > 0)
            uncovered_fns: list[str] = []
            for fid, hits in functions.items():
                if int(hits) == 0:
                    fm = fn_map.get(fid, {})
                    name = fm.get("name", f"anonymous_{fid}")
                    uncovered_fns.append(name)

            line_rate = covered_lines / total_lines if total_lines else 0.0
            branch_rate = (
                covered_branches / total_branches if total_branches else 0.0
            )

            files.append(
                {
                    "file_path": file_path,
                    "total_lines": total_lines,
                    "covered_lines": covered_lines,
                    "missed_lines": missed_lines,
                    "line_rate": round(line_rate, 4),
                    "branch_rate": round(branch_rate, 4),
                    "total_branches": total_branches,
                    "covered_branches": covered_branches,
                    "total_functions": total_functions,
                    "covered_functions": covered_functions,
                    "missed_line_numbers": missed_line_numbers,
                    "missed_branch_lines": sorted(missed_branch_lines_set),
                    "uncovered_functions": uncovered_fns,
                }
            )

        return CoverageParser._build_result(files)

    # ------------------------------------------------------------------
    # Cobertura XML parser
    # ------------------------------------------------------------------

    @staticmethod
    def parse_cobertura(data: str) -> dict[str, Any]:
        """Parse Cobertura XML (coverage.xml).

        Typical structure:
          <coverage line-rate="0.85" branch-rate="0.7" ...>
            <packages>
              <package name="..." line-rate="..." branch-rate="..." complexity="...">
                <classes>
                  <class name="..." filename="..." line-rate="..." branch-rate="..." complexity="...">
                    <methods>
                      <method name="..." ... hits="...">
                        <lines><line number="..." hits="..."/></lines>
                      </method>
                    </methods>
                    <lines>
                      <line number="1" hits="1" branch="false"/>
                      <line number="5" hits="0" branch="true" condition-coverage="50% (1/2)"/>
                    </lines>
                  </class>
                </classes>
              </package>
            </packages>
          </coverage>
        """
        root = ET.fromstring(data)
        files: list[dict[str, Any]] = []

        for package in root.iter("package"):
            for cls in package.iter("class"):
                filename = cls.get("filename", "")
                if not filename:
                    continue

                complexity_str = cls.get("complexity")
                complexity = float(complexity_str) if complexity_str else None

                # Parse methods for function coverage
                method_names: list[str] = []
                covered_method_names: list[str] = []
                for method in cls.iter("method"):
                    mname = method.get("name", "")
                    if mname:
                        method_names.append(mname)
                        # check if method has any hits
                        has_hit = False
                        for mline in method.iter("line"):
                            if int(mline.get("hits", "0")) > 0:
                                has_hit = True
                                break
                        if has_hit:
                            covered_method_names.append(mname)

                # Parse lines (from the class-level <lines> block)
                line_hits: dict[int, int] = {}
                total_branches = 0
                covered_branches = 0
                missed_branch_lines: list[int] = []

                for line_el in cls.iter("line"):
                    ln = int(line_el.get("number", "0"))
                    hits = int(line_el.get("hits", "0"))
                    line_hits[ln] = hits

                    is_branch = line_el.get("branch", "false").lower() == "true"
                    if is_branch:
                        cond_cov = line_el.get("condition-coverage", "")
                        # Parse "50% (1/2)" format
                        if "(" in cond_cov and "/" in cond_cov:
                            inner = cond_cov.split("(")[1].rstrip(")")
                            parts = inner.split("/")
                            try:
                                b_covered = int(parts[0])
                                b_total = int(parts[1])
                                total_branches += b_total
                                covered_branches += b_covered
                                if b_covered < b_total:
                                    missed_branch_lines.append(ln)
                            except (ValueError, IndexError):
                                pass

                total_lines = len(line_hits)
                covered_lines = sum(1 for h in line_hits.values() if h > 0)
                missed_lines = total_lines - covered_lines
                missed_line_numbers = sorted(
                    ln for ln, h in line_hits.items() if h == 0
                )

                total_functions = len(method_names)
                covered_functions = len(covered_method_names)
                uncovered_fns = [
                    n for n in method_names if n not in covered_method_names
                ]

                line_rate = covered_lines / total_lines if total_lines else 0.0
                branch_rate = (
                    covered_branches / total_branches if total_branches else 0.0
                )

                files.append(
                    {
                        "file_path": filename,
                        "total_lines": total_lines,
                        "covered_lines": covered_lines,
                        "missed_lines": missed_lines,
                        "line_rate": round(line_rate, 4),
                        "branch_rate": round(branch_rate, 4),
                        "total_branches": total_branches,
                        "covered_branches": covered_branches,
                        "total_functions": total_functions,
                        "covered_functions": covered_functions,
                        "missed_line_numbers": missed_line_numbers,
                        "missed_branch_lines": sorted(set(missed_branch_lines)),
                        "uncovered_functions": uncovered_fns,
                        "complexity": complexity,
                    }
                )

        return CoverageParser._build_result(files)

    # ------------------------------------------------------------------
    # Coverage.py JSON parser
    # ------------------------------------------------------------------

    @staticmethod
    def parse_coveragepy(data: str) -> dict[str, Any]:
        """Parse Python coverage.py JSON output.

        Structure:
          {
            "meta": {"version": "...", ...},
            "files": {
              "src/module.py": {
                "executed_lines": [1, 2, 3, ...],
                "missing_lines": [10, 11, ...],
                "excluded_lines": [...],
                "summary": {
                  "num_statements": N,
                  "covered_lines": N,
                  "missing_lines": N,
                  "percent_covered": 85.0,
                  "num_branches": N,
                  "covered_branches": N,
                  "missing_branches": N,
                  ...
                }
              }
            },
            "totals": {...}
          }
        """
        obj = json.loads(data)
        file_data = obj.get("files", {})
        files: list[dict[str, Any]] = []

        for file_path, info in file_data.items():
            if not isinstance(info, dict):
                continue

            executed = info.get("executed_lines", [])
            missing = info.get("missing_lines", [])
            summary = info.get("summary", {})

            total_lines = summary.get(
                "num_statements", len(executed) + len(missing)
            )
            covered_lines = summary.get("covered_lines", len(executed))
            missed_lines = summary.get("missing_lines", len(missing))
            missed_line_numbers = sorted(missing)

            total_branches = summary.get("num_branches", 0)
            covered_branches_count = summary.get("covered_branches", 0)
            missing_branches = info.get("missing_branches", [])

            # missing_branches is list of [from_line, to_line] pairs
            missed_branch_lines_set: set[int] = set()
            for br in missing_branches:
                if isinstance(br, (list, tuple)) and len(br) >= 1:
                    missed_branch_lines_set.add(int(br[0]))

            line_rate = covered_lines / total_lines if total_lines else 0.0
            branch_rate = (
                covered_branches_count / total_branches
                if total_branches
                else 0.0
            )

            # Coverage.py doesn't provide function-level data in the JSON
            # output by default; set to 0
            files.append(
                {
                    "file_path": file_path,
                    "total_lines": total_lines,
                    "covered_lines": covered_lines,
                    "missed_lines": missed_lines,
                    "line_rate": round(line_rate, 4),
                    "branch_rate": round(branch_rate, 4),
                    "total_branches": total_branches,
                    "covered_branches": covered_branches_count,
                    "total_functions": 0,
                    "covered_functions": 0,
                    "missed_line_numbers": missed_line_numbers,
                    "missed_branch_lines": sorted(missed_branch_lines_set),
                    "uncovered_functions": [],
                }
            )

        return CoverageParser._build_result(files)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_result(files: list[dict[str, Any]]) -> dict[str, Any]:
        """Build the unified result dict with summary + files."""
        total_lines = sum(f["total_lines"] for f in files)
        covered_lines = sum(f["covered_lines"] for f in files)
        missed_lines = sum(f["missed_lines"] for f in files)
        total_branches = sum(f.get("total_branches", 0) for f in files)
        covered_branches = sum(f.get("covered_branches", 0) for f in files)
        total_functions = sum(f.get("total_functions", 0) for f in files)
        covered_functions = sum(f.get("covered_functions", 0) for f in files)

        line_rate = covered_lines / total_lines if total_lines else 0.0
        branch_rate = (
            covered_branches / total_branches if total_branches else 0.0
        )
        function_rate = (
            covered_functions / total_functions if total_functions else 0.0
        )

        return {
            "summary": {
                "total_files": len(files),
                "total_lines": total_lines,
                "covered_lines": covered_lines,
                "missed_lines": missed_lines,
                "line_rate": round(line_rate, 4),
                "branch_rate": round(branch_rate, 4),
                "function_rate": round(function_rate, 4),
                "total_functions": total_functions,
                "covered_functions": covered_functions,
            },
            "files": files,
        }
