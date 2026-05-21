"""
API Request Executor
====================

Async httpx tabanli HTTP istek calistirici.
Ozellikler:
  - Async/concurrent çalışma
  - Timing breakdown (DNS/TCP/TLS/TTFB/Download)
  - Variable resolution ({{var}} syntax)
  - Assertion evaluation
  - Schema validation (contract testing)
  - Variable extraction (chain için)
  - Response diff (regression detection)
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from app.domains.api_testing.assertion_engine import (
    AssertionReport,
    evaluate_assertions,
    validate_contract,
)
from app.domains.api_testing.environment import resolve_dict, resolve_string
from app.domains.api_testing.network_security import UnsafeTargetError, validate_outbound_url

logger = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────
DEFAULT_TIMEOUT = 30.0  # saniye
MAX_RESPONSE_BODY_SIZE = 500_000  # ~500KB — daha buyuk response'lar kesilir


@dataclass
class TimingBreakdown:
    """HTTP istek zamanlama detayi (milisaniye)."""
    total_ms: float = 0.0
    # Detay (httpx event hooks ile mevcut degil, toplam sure uzerinden)
    # Gelecekte httpx transport-level hooks veya curl_cffi ile ayrintili olabilir

    def to_dict(self) -> dict:
        return {
            "total_ms": round(self.total_ms, 2),
        }


@dataclass
class ExecutionResult:
    """Tek bir HTTP istek calismasinin sonucu."""
    # Request (gonderilen)
    method: str = ""
    url: str = ""
    headers_sent: dict = field(default_factory=dict)
    body_sent: Any = None

    # Response
    status_code: Optional[int] = None
    response_headers: dict = field(default_factory=dict)
    response_body: Optional[str] = None
    response_body_parsed: Any = None
    response_size_bytes: int = 0

    # Timing
    timing: TimingBreakdown = field(default_factory=TimingBreakdown)

    # Assertions
    assertion_report: Optional[AssertionReport] = None

    # Contract validation
    schema_valid: Optional[bool] = None
    schema_errors: List[str] = field(default_factory=list)

    # Extracted variables (sonraki chain adimlari için)
    extracted_variables: Dict[str, str] = field(default_factory=dict)

    # Errors
    error: Optional[str] = None
    success: bool = False

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "url": self.url,
            "headers_sent": self.headers_sent,
            "body_sent": self.body_sent,
            "status_code": self.status_code,
            "response_headers": self.response_headers,
            "response_body": (
                self.response_body[:MAX_RESPONSE_BODY_SIZE]
                if self.response_body and len(self.response_body) > MAX_RESPONSE_BODY_SIZE
                else self.response_body
            ),
            "response_size_bytes": self.response_size_bytes,
            "timing": self.timing.to_dict(),
            "assertion_report": self.assertion_report.to_dict() if self.assertion_report else None,
            "schema_valid": self.schema_valid,
            "schema_errors": self.schema_errors,
            "extracted_variables": self.extracted_variables,
            "error": self.error,
            "success": self.success,
        }


def _resolve_json_path_simple(data: Any, path: str) -> Any:
    """Basit JSON path cozumleyici (extraction için)."""
    if not path or not path.startswith("$"):
        return None

    parts = path.lstrip("$.").split(".")
    current = data

    for part in parts:
        if current is None:
            return None

        idx_match = re.match(r"^(\w+)\[(\d+)]$", part)
        if idx_match:
            field_name, idx = idx_match.group(1), int(idx_match.group(2))
            if isinstance(current, dict):
                current = current.get(field_name)
            if isinstance(current, list) and idx < len(current):
                current = current[idx]
            else:
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None

    return current


async def execute_request(
    *,
    method: str,
    url: str,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    body: Any = None,
    variables: Optional[Dict[str, str]] = None,
    assertions: Optional[List[dict]] = None,
    expected_schema: Optional[dict] = None,
    extract_rules: Optional[List[dict]] = None,
    timeout: float = DEFAULT_TIMEOUT,
    follow_redirects: bool = True,
    verify_ssl: bool = True,
) -> ExecutionResult:
    """
    Tek bir HTTP istegi çalıştır.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        url: Tam URL (degiskenler cozulmus veya cozulmemis)
        headers: Request headers
        params: Query parameters
        body: Request body (dict veya string)
        variables: {{variable}} cozumleme için degisken mapping'i
        assertions: Degerlendirilecek assertion listesi
        expected_schema: Contract testing için beklenen JSON Schema
        extract_rules: Variable extraction kurallari
            [{name: "auth_token", json_path: "$.access_token"}]
        timeout: Saniye cinsinden timeout
        follow_redirects: 3xx redirect'leri takip et
        verify_ssl: SSL sertifika dogrulamasi

    Returns:
        ExecutionResult
    """
    result = ExecutionResult()
    vars_dict = variables or {}

    # 1. Variable resolution
    resolved_url = resolve_string(url, vars_dict)
    resolved_headers = resolve_dict(headers or {}, vars_dict)
    resolved_params = resolve_dict(params or {}, vars_dict)
    resolved_body = resolve_dict(body, vars_dict) if body else None

    try:
        validate_outbound_url(resolved_url)
    except UnsafeTargetError as exc:
        result.method = method.upper()
        result.url = resolved_url
        result.headers_sent = resolved_headers
        result.body_sent = resolved_body
        result.error = f"Guvensiz hedef URL: {exc}"
        return result

    result.method = method.upper()
    result.url = resolved_url
    result.headers_sent = resolved_headers
    result.body_sent = resolved_body

    # 2. HTTP istegi gönder
    t_start = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=follow_redirects,
            verify=verify_ssl,
        ) as client:
            # Body hazırla
            kwargs: Dict[str, Any] = {
                "method": result.method,
                "url": resolved_url,
                "headers": resolved_headers,
                "params": resolved_params if resolved_params else None,
            }

            if resolved_body is not None:
                if isinstance(resolved_body, (dict, list)):
                    kwargs["json"] = resolved_body
                else:
                    kwargs["content"] = str(resolved_body).encode("utf-8")

            response = await client.request(**kwargs)

    except httpx.TimeoutException as exc:
        result.error = f"Timeout ({timeout}s): {exc}"
        result.timing.total_ms = (time.monotonic() - t_start) * 1000
        return result
    except httpx.ConnectError as exc:
        result.error = f"Bağlantı hatasi: {exc}"
        result.timing.total_ms = (time.monotonic() - t_start) * 1000
        return result
    except Exception as exc:
        result.error = f"HTTP hatasi: {type(exc).__name__}: {exc}"
        result.timing.total_ms = (time.monotonic() - t_start) * 1000
        return result

    t_end = time.monotonic()
    result.timing.total_ms = (t_end - t_start) * 1000

    # 3. Response parse
    result.status_code = response.status_code
    result.response_headers = dict(response.headers)
    result.response_size_bytes = len(response.content)

    try:
        result.response_body = response.text
    except Exception:
        result.response_body = response.content.decode("utf-8", errors="replace")

    # JSON parse dene
    try:
        result.response_body_parsed = response.json()
    except (json.JSONDecodeError, ValueError):
        result.response_body_parsed = result.response_body

    result.success = True  # HTTP istegi başarılı (assertion sonucu degil)

    # 4. Variable extraction (chain için)
    if extract_rules:
        for rule in extract_rules:
            var_name = rule.get("name", "")
            json_path = rule.get("json_path", "")
            value = _resolve_json_path_simple(result.response_body_parsed, json_path)
            if value is not None:
                result.extracted_variables[var_name] = str(value)
                logger.debug("Extracted %s = %s from %s", var_name, str(value)[:50], json_path)

    # 5. Assertions
    if assertions:
        result.assertion_report = evaluate_assertions(
            assertions,
            status_code=result.status_code,
            response_body=result.response_body_parsed,
            response_headers=result.response_headers,
            response_time_ms=result.timing.total_ms,
        )

    # 6. Contract validation (schema)
    if expected_schema:
        is_valid, errors = validate_contract(
            result.response_body_parsed,
            expected_schema,
        )
        result.schema_valid = is_valid
        result.schema_errors = errors

    return result


async def execute_collection(
    requests: List[dict],
    *,
    base_url: str = "",
    base_headers: Optional[dict] = None,
    variables: Optional[Dict[str, str]] = None,
    stop_on_failure: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> List[ExecutionResult]:
    """
    Bir koleksiyondaki tüm istekleri sirasiyla çalıştır.

    Args:
        requests: Request listesi, her biri:
            {method, path, headers, params, body, assertions, extract_rules, expected_schema}
        base_url: Collection base URL
        base_headers: Collection-level default headers
        variables: Ortam degiskenleri
        stop_on_failure: Ilk hatada dur
        timeout: Her istek için timeout

    Returns:
        ExecutionResult listesi
    """
    results: List[ExecutionResult] = []
    chain_vars = dict(variables or {})
    merged_headers = dict(base_headers or {})

    for req in requests:
        method = req.get("method", "GET")
        path = req.get("path", "")

        # URL oluştur
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}" if base_url else path

        # Headers birlesitir (collection → request)
        req_headers = {**merged_headers, **(req.get("headers") or {})}

        result = await execute_request(
            method=method,
            url=url,
            headers=req_headers,
            params=req.get("params"),
            body=req.get("body"),
            variables=chain_vars,
            assertions=req.get("assertions", []),
            expected_schema=req.get("expected_schema"),
            extract_rules=req.get("extract_rules", []),
            timeout=timeout,
        )

        results.append(result)

        # Extracted variables'i sonraki istekler için ekle
        if result.extracted_variables:
            chain_vars.update(result.extracted_variables)

        # Stop on failure
        if stop_on_failure and result.error:
            break
        if stop_on_failure and result.assertion_report and not result.assertion_report.all_passed:
            break

    return results
