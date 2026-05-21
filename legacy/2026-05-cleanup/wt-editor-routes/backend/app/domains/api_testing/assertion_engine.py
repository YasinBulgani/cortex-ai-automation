"""
API Testing Assertion Engine
============================

Desteklenen assertion tipleri:
  - status_code    : HTTP durum kodu kontrolu
  - json_path      : JSONPath ile deger karsilastirma
  - header         : Response header kontrolu
  - response_time  : Yanit suresi (ms) kontrolu
  - schema         : JSON Schema dogrulama
  - regex          : Regex pattern eslestirme
  - exists         : Alanin varligini kontrol etme
  - not_exists     : Alanin olmadigini kontrol etme
  - body_contains  : Response body icerik kontrolu
  - cookie         : Cookie degeri kontrolu
  - content_type   : Content-Type baslik kontrolu

Desteklenen operatorler:
  equals, not_equals, contains, not_contains,
  gt, lt, gte, lte, matches (regex), one_of,
  starts_with, ends_with, is_empty, is_not_empty,
  type_is (string, number, boolean, array, object, null)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AssertionResult:
    """Tek bir assertion'in sonucu."""
    index: int
    assertion_type: str
    passed: bool
    expected: Any = None
    actual: Any = None
    message: str = ""
    path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "type": self.assertion_type,
            "passed": self.passed,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class AssertionReport:
    """Tum assertion'larin toplu sonucu."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    results: List[AssertionResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.total > 0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "all_passed": self.all_passed,
            "results": [r.to_dict() for r in self.results],
        }


def _resolve_json_path(data: Any, path: str) -> Tuple[bool, Any]:
    """
    Basit JSON path cozumleyici.
    Desteklenen: $.field, $.nested.field, $.array[0], $.array[*].field

    Returns: (found: bool, value: Any)
    """
    if not path or not path.startswith("$"):
        return False, None

    parts = path.lstrip("$.").split(".")
    current = data

    for part in parts:
        if current is None:
            return False, None

        # Array index: field[0], field[*]
        match = re.match(r"^(\w+)\[(\d+|\*)]$", part)
        if match:
            field_name, idx = match.group(1), match.group(2)
            if isinstance(current, dict):
                current = current.get(field_name)
            if not isinstance(current, list):
                return False, None
            if idx == "*":
                # Tum elemanlari topla
                return True, current
            idx_int = int(idx)
            if idx_int >= len(current):
                return False, None
            current = current[idx_int]
        elif isinstance(current, dict):
            if part not in current:
                return False, None
            current = current[part]
        elif isinstance(current, list):
            # Array uzerinde field erisimu — her eleman icin
            results = []
            for item in current:
                if isinstance(item, dict) and part in item:
                    results.append(item[part])
            if results:
                current = results
            else:
                return False, None
        else:
            return False, None

    return True, current


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    """Operatore gore karsilastirma yap."""
    try:
        if operator == "equals":
            return actual == expected
        elif operator == "not_equals":
            return actual != expected
        elif operator == "contains":
            return expected in str(actual)
        elif operator == "not_contains":
            return expected not in str(actual)
        elif operator == "gt":
            return float(actual) > float(expected)
        elif operator == "lt":
            return float(actual) < float(expected)
        elif operator == "gte":
            return float(actual) >= float(expected)
        elif operator == "lte":
            return float(actual) <= float(expected)
        elif operator == "matches":
            return bool(re.search(str(expected), str(actual)))
        elif operator == "one_of":
            exp_list = expected if isinstance(expected, list) else [expected]
            return actual in exp_list
        elif operator == "starts_with":
            return str(actual).startswith(str(expected))
        elif operator == "ends_with":
            return str(actual).endswith(str(expected))
        elif operator == "is_empty":
            return actual is None or actual == "" or actual == [] or actual == {}
        elif operator == "is_not_empty":
            return actual is not None and actual != "" and actual != [] and actual != {}
        elif operator == "type_is":
            type_map = {
                "string": str, "number": (int, float), "boolean": bool,
                "array": list, "object": dict, "null": type(None),
            }
            return isinstance(actual, type_map.get(expected, type(None)))
        elif operator == "exists":
            return actual is not None
        else:
            return actual == expected
    except (TypeError, ValueError):
        return False


def evaluate_assertions(
    assertions: List[dict],
    *,
    status_code: Optional[int] = None,
    response_body: Any = None,
    response_headers: Optional[dict] = None,
    response_time_ms: Optional[float] = None,
    cookies: Optional[dict] = None,
) -> AssertionReport:
    """
    Assertion listesini degerlendir.

    Her assertion dict'i su alanlari icerir:
      type     : assertion tipi (status_code, json_path, header, ...)
      path     : json_path icin yol (opsiyonel)
      operator : karsilastirma operatoru (opsiyonel, default: equals)
      expected : beklenen deger
      message  : hata mesaji (opsiyonel)
    """
    report = AssertionReport()
    headers = response_headers or {}
    cookies = cookies or {}

    # Response body'yi parse et
    body_parsed: Any = None
    if isinstance(response_body, str):
        try:
            body_parsed = json.loads(response_body)
        except (json.JSONDecodeError, TypeError):
            body_parsed = response_body
    else:
        body_parsed = response_body

    for idx, assertion in enumerate(assertions):
        a_type = assertion.get("type", "")
        operator = assertion.get("operator", "equals")
        expected = assertion.get("expected")
        path = assertion.get("path")
        custom_msg = assertion.get("message", "")

        result = AssertionResult(
            index=idx,
            assertion_type=a_type,
            passed=False,
            expected=expected,
            path=path,
        )

        try:
            if a_type == "status_code":
                result.actual = status_code
                if operator == "one_of" or isinstance(expected, list):
                    result.passed = status_code in (expected if isinstance(expected, list) else [expected])
                else:
                    result.passed = _compare(status_code, operator, expected)
                result.message = custom_msg or (
                    f"Status {status_code} == {expected}" if result.passed
                    else f"Status {status_code} != {expected}"
                )

            elif a_type == "json_path":
                found, actual = _resolve_json_path(body_parsed, path or "")
                result.actual = actual
                if not found:
                    result.passed = False
                    result.message = custom_msg or f"JSON path '{path}' bulunamadi"
                else:
                    result.passed = _compare(actual, operator, expected)
                    result.message = custom_msg or (
                        f"[{path}] {actual} {operator} {expected}"
                    )

            elif a_type == "header":
                header_name = path or assertion.get("key", "")
                # Case-insensitive header lookup
                actual = None
                for k, v in headers.items():
                    if k.lower() == header_name.lower():
                        actual = v
                        break
                result.actual = actual
                if actual is None:
                    result.passed = False
                    result.message = custom_msg or f"Header '{header_name}' bulunamadi"
                else:
                    result.passed = _compare(actual, operator, expected)
                    result.message = custom_msg or f"Header[{header_name}] = {actual}"

            elif a_type == "response_time":
                result.actual = response_time_ms
                max_ms = float(expected) if expected else 0
                result.passed = (response_time_ms or 0) <= max_ms
                result.message = custom_msg or (
                    f"Response time {response_time_ms:.0f}ms <= {max_ms:.0f}ms" if result.passed
                    else f"Response time {response_time_ms:.0f}ms > {max_ms:.0f}ms (YAVAS)"
                )

            elif a_type == "schema":
                # JSON Schema dogrulama
                try:
                    import jsonschema as js
                    schema = expected if isinstance(expected, dict) else {}
                    js.validate(instance=body_parsed, schema=schema)
                    result.passed = True
                    result.actual = "schema uyumlu"
                    result.message = custom_msg or "Response schema gecerli"
                except ImportError:
                    result.passed = False
                    result.message = "jsonschema kutuphanesi yuklu degil"
                except Exception as exc:
                    result.passed = False
                    result.actual = str(exc)
                    result.message = custom_msg or f"Schema hatasi: {exc}"

            elif a_type == "regex":
                text = json.dumps(body_parsed) if not isinstance(body_parsed, str) else body_parsed
                pattern = str(expected or "")
                match = re.search(pattern, text)
                result.passed = match is not None
                result.actual = match.group(0) if match else None
                result.message = custom_msg or (
                    f"Regex '{pattern}' eslesti" if result.passed
                    else f"Regex '{pattern}' eslesmedi"
                )

            elif a_type == "exists":
                found, _ = _resolve_json_path(body_parsed, path or "")
                result.passed = found
                result.actual = found
                result.message = custom_msg or (
                    f"[{path}] mevcut" if found else f"[{path}] bulunamadi"
                )

            elif a_type == "not_exists":
                found, _ = _resolve_json_path(body_parsed, path or "")
                result.passed = not found
                result.actual = not found
                result.message = custom_msg or (
                    f"[{path}] beklendigi gibi yok" if not found
                    else f"[{path}] olmamasi gerekiyordu ama mevcut"
                )

            elif a_type == "body_contains":
                text = json.dumps(body_parsed) if not isinstance(body_parsed, str) else str(body_parsed)
                result.passed = str(expected) in text
                result.actual = f"body length={len(text)}"
                result.message = custom_msg or (
                    f"Body '{expected}' iceriyor" if result.passed
                    else f"Body '{expected}' icermiyor"
                )

            elif a_type == "cookie":
                cookie_name = path or ""
                result.actual = cookies.get(cookie_name)
                if result.actual is None:
                    result.passed = False
                    result.message = custom_msg or f"Cookie '{cookie_name}' bulunamadi"
                else:
                    result.passed = _compare(result.actual, operator, expected)
                    result.message = custom_msg or f"Cookie[{cookie_name}] = {result.actual}"

            elif a_type == "content_type":
                ct = headers.get("content-type", headers.get("Content-Type", ""))
                result.actual = ct
                result.passed = _compare(ct, operator or "contains", expected)
                result.message = custom_msg or f"Content-Type: {ct}"

            else:
                result.passed = False
                result.message = f"Bilinmeyen assertion tipi: {a_type}"

        except Exception as exc:
            result.passed = False
            result.message = f"Assertion hatasi: {exc}"
            logger.warning("Assertion[%d] error: %s", idx, exc)

        report.results.append(result)
        report.total += 1
        if result.passed:
            report.passed += 1
        else:
            report.failed += 1

    return report


def validate_contract(
    response_body: Any,
    expected_schema: dict,
) -> Tuple[bool, List[str]]:
    """
    Response body'nin JSON Schema'ya uygunlugunu kontrol et.
    Returns: (is_valid, errors)
    """
    try:
        import jsonschema as js
    except ImportError:
        return False, ["jsonschema kutuphanesi yuklu degil"]

    body = response_body
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return False, ["Response body JSON olarak parse edilemedi"]

    errors: List[str] = []
    validator = js.Draft7Validator(expected_schema)
    for error in validator.iter_errors(body):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"[{path}] {error.message}")

    return len(errors) == 0, errors


def infer_schema(response_body: Any) -> dict:
    """
    Response body'den JSON Schema cikar (genson).
    Spec yoksa gercek response'tan schema olusturmak icin kullanilir.
    """
    try:
        from genson import SchemaBuilder
    except ImportError:
        return {"type": "object"}

    body = response_body
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return {"type": "string"}

    builder = SchemaBuilder()
    builder.add_object(body)
    return builder.to_schema()
