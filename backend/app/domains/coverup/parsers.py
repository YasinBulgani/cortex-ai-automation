"""CoverUp — Coverage rapor parser'ları.

Desteklenen formatlar:
    - lcov (`_parse_lcov`)
    - coveragepy JSON (`_parse_coveragepy`)
    - cobertura XML (`parse_cobertura`)
    - istanbul JSON summary (`parse_istanbul`)
    - nyc JSON (`parse_nyc`)

Tüm parser'lar aynı schema'yı döndürür:

    {
        "file_path": str,
        "lines_hit":       list[int],   # coverage >0 olan satır numaraları
        "lines_missed":    list[int],   # coverage 0 olan satır numaraları
        "branches_hit":    int,
        "branches_total":  int,
        "functions_hit":   int,
        "functions_total": int,
    }

Parse başarısız olursa boş liste döner; router 400 ile yanıt verir.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from xml.etree import ElementTree as ET

_logger = logging.getLogger(__name__)


# ── lcov ───────────────────────────────────────────────────────────────────
def _parse_lcov(raw: str) -> list[dict[str, Any]]:
    """LCOV format parser (DA/BRDA/FNDA satırları)."""
    files: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("SF:"):
            fpath = line[3:]
            current = files.setdefault(fpath, {
                "file_path": fpath,
                "lines_hit": [],
                "lines_missed": [],
                "branches_hit": 0,
                "branches_total": 0,
                "functions_hit": 0,
                "functions_total": 0,
            })
        elif line.startswith("DA:") and current is not None:
            parts = line[3:].split(",")
            try:
                num, hits = int(parts[0]), int(parts[1])
                if hits > 0:
                    current["lines_hit"].append(num)
                else:
                    current["lines_missed"].append(num)
            except (ValueError, IndexError):
                pass
        elif line.startswith("BRDA:") and current is not None:
            parts = line[5:].split(",")
            try:
                current["branches_total"] += 1
                if parts[3] != "-" and int(parts[3]) > 0:
                    current["branches_hit"] += 1
            except (ValueError, IndexError):
                pass
        elif line.startswith("FNDA:") and current is not None:
            parts = line[5:].split(",")
            try:
                current["functions_total"] += 1
                if int(parts[0]) > 0:
                    current["functions_hit"] += 1
            except (ValueError, IndexError):
                pass
        elif line == "end_of_record":
            current = None
    return list(files.values())


# ── coverage.py JSON ───────────────────────────────────────────────────────
def _parse_coveragepy(raw: str) -> list[dict[str, Any]]:
    """Coverage.py `coverage json` çıktısı."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        _logger.warning("coverage.py JSON parse hatası: %s", exc)
        return []
    files: list[dict[str, Any]] = []
    for fpath, info in (data.get("files") or {}).items():
        summary = (info.get("summary") or {})
        files.append({
            "file_path": fpath,
            "lines_hit": list(info.get("executed_lines") or []),
            "lines_missed": list(info.get("missing_lines") or []),
            "branches_hit": int(summary.get("covered_branches") or 0),
            "branches_total": int(summary.get("num_branches") or 0),
            "functions_hit": 0,
            "functions_total": 0,
        })
    return files


# ── cobertura XML ──────────────────────────────────────────────────────────
def parse_cobertura(raw: str) -> list[dict[str, Any]]:
    """Cobertura XML çıktısını dosya bazında parse eder.

    Beklenen yapı:
        <coverage>
          <packages>
            <package>
              <classes>
                <class filename="src/a.py" line-rate="0.8">
                  <lines>
                    <line number="1" hits="3" branch="false"/>
                    <line number="2" hits="0"/>
                    <line number="3" hits="1" branch="true" condition-coverage="50%"/>
                  </lines>
                  <methods>...</methods>
                </class>
              </classes>
            </package>
          </packages>
        </coverage>
    """
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        _logger.warning("cobertura parse hatası: %s", exc)
        return []

    files: dict[str, dict[str, Any]] = {}

    for cls in root.iter("class"):
        fpath = cls.get("filename") or ""
        if not fpath:
            continue
        entry = files.setdefault(
            fpath,
            {
                "file_path": fpath,
                "lines_hit": [],
                "lines_missed": [],
                "branches_hit": 0,
                "branches_total": 0,
                "functions_hit": 0,
                "functions_total": 0,
            },
        )

        # Satırlar — yalnızca class seviyesindeki doğrudan <lines> bloğunu say;
        # method içindeki `<lines>` aynı satırları tekrarlar.
        class_lines = cls.find("lines")
        line_iter = class_lines.iter("line") if class_lines is not None else cls.iter("line")
        seen_line_nums: set[int] = set()
        for line in line_iter:
            try:
                line_num = int(line.get("number") or "0")
                hits = int(line.get("hits") or "0")
            except ValueError:
                continue
            if line_num <= 0 or line_num in seen_line_nums:
                continue
            seen_line_nums.add(line_num)
            if hits > 0:
                entry["lines_hit"].append(line_num)
            else:
                entry["lines_missed"].append(line_num)

            # Branch — condition-coverage="50% (1/2)" formatı
            if (line.get("branch") or "").lower() == "true":
                cond = line.get("condition-coverage", "")
                # "50% (1/2)" → hit=1 total=2
                if "(" in cond and "/" in cond:
                    try:
                        hit_s, total_s = cond.split("(")[1].split(")")[0].split("/")
                        entry["branches_hit"] += int(hit_s)
                        entry["branches_total"] += int(total_s)
                    except (ValueError, IndexError):
                        pass
                else:
                    # Branch var ama detay yok — 1/1 say
                    entry["branches_total"] += 1
                    if hits > 0:
                        entry["branches_hit"] += 1

        # Metodlar
        for method in cls.iter("method"):
            entry["functions_total"] += 1
            # Method içindeki ilk satır hit > 0 ise "kapsandı"
            any_hit = False
            for line in method.iter("line"):
                try:
                    if int(line.get("hits") or "0") > 0:
                        any_hit = True
                        break
                except ValueError:
                    continue
            if any_hit:
                entry["functions_hit"] += 1

    return list(files.values())


# ── istanbul / nyc JSON ────────────────────────────────────────────────────
def parse_istanbul(raw: str) -> list[dict[str, Any]]:
    """istanbul `coverage-final.json` formatı.

    Yapı (her dosya için):
        {
            "path": "src/a.js",
            "statementMap": { "0": {"start": {"line": 1}, "end": {...}}, ... },
            "s": { "0": 3, "1": 0, ... },         // statement hit counts
            "branchMap": { "0": {"line": 5, ...}, ... },
            "b": { "0": [3, 0], "1": [1, 1] },    // per-branch hit arrays
            "fnMap": { "0": {"line": 10, ...}, ... },
            "f": { "0": 2, "1": 0, ... }          // function hit counts
        }
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        _logger.warning("istanbul JSON parse hatası: %s", exc)
        return []

    # Nested tek kök ("coverageMap") olabilir
    if isinstance(data, dict) and "files" not in data and "path" in next(iter(data.values()), {}):
        file_entries = data
    elif isinstance(data, dict):
        file_entries = data
    else:
        return []

    files: list[dict[str, Any]] = []
    for _key, info in file_entries.items():
        if not isinstance(info, dict):
            continue
        fpath = info.get("path") or _key
        statement_map = info.get("statementMap") or {}
        s_hits = info.get("s") or {}
        b_counts = info.get("b") or {}
        f_counts = info.get("f") or {}
        fn_map = info.get("fnMap") or {}

        lines_hit: set[int] = set()
        lines_missed: set[int] = set()
        for sid, meta in statement_map.items():
            start = (meta or {}).get("start") or {}
            line_num = int(start.get("line") or 0)
            if line_num <= 0:
                continue
            hit = int(s_hits.get(sid) or 0)
            if hit > 0:
                lines_hit.add(line_num)
            else:
                lines_missed.add(line_num)

        # Çakışan satırlar (aynı satırda hem hit hem missed statement varsa hit say)
        lines_missed -= lines_hit

        branches_hit = 0
        branches_total = 0
        for _bid, arr in b_counts.items():
            if isinstance(arr, list):
                branches_total += len(arr)
                branches_hit += sum(1 for v in arr if isinstance(v, int) and v > 0)

        functions_total = len(fn_map)
        functions_hit = sum(1 for v in f_counts.values() if isinstance(v, int) and v > 0)

        files.append(
            {
                "file_path": fpath,
                "lines_hit": sorted(lines_hit),
                "lines_missed": sorted(lines_missed),
                "branches_hit": branches_hit,
                "branches_total": branches_total,
                "functions_hit": functions_hit,
                "functions_total": functions_total,
            }
        )
    return files


def parse_nyc(raw: str) -> list[dict[str, Any]]:
    """nyc `coverage-summary.json` veya `coverage-final.json` formatı.

    nyc iki varyant üretir:
      1. `coverage-final.json`: istanbul ile aynı yapı → delegate.
      2. `coverage-summary.json`: her dosya için {statements,branches,functions,lines}
         agregat değerler içerir; satır numarası yoktur.

    Summary varyantında `lines_hit`/`lines_missed` numerik array olarak doldurulamaz
    (satır numaraları yok); yerine `total`-`hit` kadar sentetik index üretilir.
    Bu, toplam kapsam metriği için yeterlidir.
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        _logger.warning("nyc JSON parse hatası: %s", exc)
        return []

    # Heuristik: values'ın ilki istanbul yapısına uyuyorsa delegate
    if isinstance(data, dict) and data:
        first_value = next(iter(data.values()))
        if isinstance(first_value, dict) and ("statementMap" in first_value or "s" in first_value):
            return parse_istanbul(raw)

    files: list[dict[str, Any]] = []
    for fpath, info in (data or {}).items():
        if fpath == "total" or not isinstance(info, dict):
            continue
        stmt = info.get("statements") or {}
        branches = info.get("branches") or {}
        funcs = info.get("functions") or {}
        lines = info.get("lines") or {}

        total_lines = int(lines.get("total") or 0)
        covered_lines = int(lines.get("covered") or 0)
        missed_lines = max(total_lines - covered_lines, 0)

        files.append(
            {
                "file_path": fpath,
                # Summary'de satır numarası olmadığı için sentetik doldur;
                # downstream `_build_file_coverage` yalnızca uzunlukları kullanır.
                "lines_hit": list(range(1, covered_lines + 1)),
                "lines_missed": list(range(covered_lines + 1, covered_lines + missed_lines + 1)),
                "branches_hit": int(branches.get("covered") or 0),
                "branches_total": int(branches.get("total") or 0),
                "functions_hit": int(funcs.get("covered") or 0),
                "functions_total": int(funcs.get("total") or 0),
            }
        )
    return files
