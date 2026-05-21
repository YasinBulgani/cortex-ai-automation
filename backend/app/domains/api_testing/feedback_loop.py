"""
Execution Feedback Loop — Test çalışma sonuclarindan ogrenme ve zenginlestirme.

Bu modul her test kosusu sonrasinda:
  1. Başarısız testlerden hata paternleri cikarir → KnowledgeStore'a kaydeder
  2. Yavas yanıt veren endpoint'leri tespit eder → performans uyarisi uretir
  3. Tekrarlayan hatalari analiz eder → insight olarak depolar
  4. Yeni test uretiminde bu ogrenmeleri baglam olarak sunar

Kullanim:
  from app.domains.api_testing.feedback_loop import learn_from_execution, enrich_generation_prompt

  # Test kosusundan sonra (fire-and-forget):
  learn_from_execution(db, run_id, project_id)

  # Test uretimi oncesi:
  enrichment = enrich_generation_prompt(project_id, endpoints, mode)
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.domains.ai.knowledge_store import KnowledgeStore
from app.domains.api_testing.models import (
    ApiExecutionDetail,
    ApiTestCase,
)

logger = logging.getLogger(__name__)

# Yavas yanıt esigi (ms)
SLOW_RESPONSE_THRESHOLD_MS = 2000

# Tekrarlayan hata esigi — ayni endpoint'te kac kez fail olursa "recurring" sayilir
RECURRING_FAILURE_THRESHOLD = 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# A. LEARN FROM EXECUTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def learn_from_execution(
    db: Session,
    run_id: str,
    project_id: str,
) -> Dict[str, Any]:
    """
    Bir test kosusunun sonuclarindan ogen ve KnowledgeStore'a kaydet.

    Args:
        db: SQLAlchemy session
        run_id: Test kosusu ID'si (tspm_api_test_runs.id)
        project_id: Proje ID'si

    Returns:
        Özet istatistikler: {error_patterns, performance_warnings, recurring_failures, total_ingested}
    """
    try:
        store = KnowledgeStore(project_id=project_id)
    except Exception as exc:
        logger.warning("KnowledgeStore bağlantısı kurulamadi: %s", exc)
        return {"error": str(exc), "total_ingested": 0}

    # Tüm execution detail'leri yükle
    details = (
        db.query(ApiExecutionDetail)
        .filter(ApiExecutionDetail.run_id == run_id)
        .all()
    )

    if not details:
        logger.info("Run %s için execution detail bulunamadi", run_id)
        return {"error_patterns": 0, "performance_warnings": 0,
                "recurring_failures": 0, "total_ingested": 0}

    # Test case bilgilerini toplu yükle
    tc_ids = [d.test_case_id for d in details if d.test_case_id]
    test_cases_map = {}  # type: Dict[str, ApiTestCase]
    if tc_ids:
        tcs = db.query(ApiTestCase).filter(ApiTestCase.id.in_(tc_ids)).all()
        test_cases_map = {tc.id: tc for tc in tcs}

    ingested_count = 0
    error_pattern_count = 0
    performance_warning_count = 0

    # ── Başarısız testlerden hata paternleri ──────────────────────────
    failed_details = [d for d in details if not d.passed]
    for detail in failed_details:
        text = _build_failure_learning_text(detail, test_cases_map)
        if not text:
            continue

        metadata = {
            "run_id": run_id,
            "test_case_id": detail.test_case_id or "",
            "method": detail.actual_method,
            "path": _extract_path(detail.actual_url),
            "status_code": detail.status_code,
            "project_id": project_id,
        }

        try:
            store.ingest(text, source="error_pattern", metadata=metadata)
            ingested_count += 1
            error_pattern_count += 1
        except Exception as exc:
            logger.debug("error_pattern ingest hatasi: %s", exc)

    # ── Yavas yanitlar için performans uyarilari ──────────────────────
    passed_details = [d for d in details if d.passed]
    for detail in passed_details:
        if detail.total_ms and detail.total_ms > SLOW_RESPONSE_THRESHOLD_MS:
            tc = test_cases_map.get(detail.test_case_id) if detail.test_case_id else None
            title = tc.title if tc else "Unknown"
            path = _extract_path(detail.actual_url)

            text = (
                f"SLOW RESPONSE: {detail.actual_method} {path} - "
                f"{detail.total_ms:.0f}ms. "
                f"Test: {title}. "
                f"Consider adding performance test with stricter SLA."
            )
            metadata = {
                "type": "performance",
                "run_id": run_id,
                "test_case_id": detail.test_case_id or "",
                "method": detail.actual_method,
                "path": path,
                "total_ms": detail.total_ms,
                "project_id": project_id,
            }

            try:
                store.ingest(text, source="insight", metadata=metadata)
                ingested_count += 1
                performance_warning_count += 1
            except Exception as exc:
                logger.debug("performance insight ingest hatasi: %s", exc)

    # ── Tekrarlayan hatalari tespit et ────────────────────────────────
    recurring_count = _detect_and_store_recurring_failures(
        db, store, details, test_cases_map, project_id, run_id,
    )
    ingested_count += recurring_count

    # ── Endpoint bazinda pass rate ozeti ──────────────────────────────
    endpoint_stats = _calculate_endpoint_stats(details)
    if endpoint_stats:
        summary_text = _build_stats_summary(endpoint_stats, run_id)
        if summary_text:
            try:
                store.ingest(
                    summary_text,
                    source="insight",
                    metadata={
                        "type": "run_summary",
                        "run_id": run_id,
                        "project_id": project_id,
                    },
                )
                ingested_count += 1
            except Exception as exc:
                logger.debug("run_summary ingest hatasi: %s", exc)

    result = {
        "error_patterns": error_pattern_count,
        "performance_warnings": performance_warning_count,
        "recurring_failures": recurring_count,
        "total_ingested": ingested_count,
    }

    logger.info(
        "Feedback loop tamamlandi — run=%s, error_patterns=%d, perf_warnings=%d, recurring=%d",
        run_id, error_pattern_count, performance_warning_count, recurring_count,
    )

    return result


def _build_failure_learning_text(
    detail: ApiExecutionDetail,
    test_cases_map: Dict[str, "ApiTestCase"],
) -> Optional[str]:
    """Başarısız bir test için yapilandirilmis ogrenme metni oluştur."""
    tc = test_cases_map.get(detail.test_case_id) if detail.test_case_id else None
    title = tc.title if tc else "Unknown test"
    path = _extract_path(detail.actual_url)
    method = detail.actual_method

    parts = []  # type: List[str]
    parts.append(f"TEST FAILED: {method} {path}")

    # Beklenen vs gerçek status code
    if tc and tc.assertions:
        expected_status = _find_expected_status(tc.assertions)
        if expected_status and detail.status_code:
            parts.append(
                f"Expected {expected_status} got {detail.status_code}"
            )
    elif detail.status_code:
        parts.append(f"Status code: {detail.status_code}")

    # Error message
    if detail.error_message:
        # Uzun hata mesajlarini kisalt
        error_short = detail.error_message[:300]
        parts.append(f"Error: {error_short}")

    # Assertion failures
    if detail.assertion_results:
        failed_assertions = [
            a for a in detail.assertion_results
            if not a.get("passed", True)
        ]
        for fa in failed_assertions[:5]:  # En fazla 5 assertion
            a_type = fa.get("type", "unknown")
            expected = fa.get("expected", "?")
            actual = fa.get("actual", "?")
            parts.append(
                f"Assertion [{a_type}] failed: expected {expected}, actual {actual}"
            )

    # Root cause tahmini
    root_cause = _guess_root_cause(detail)
    if root_cause:
        parts.append(f"Root cause likely: {root_cause}")

    # Test title
    parts.append(f"Test: {title}")

    return ". ".join(parts) + "."


def _find_expected_status(assertions: List[dict]) -> Optional[int]:
    """Assertion listesinden beklenen status code'u bul."""
    for a in assertions:
        if a.get("type") == "status_code":
            expected = a.get("expected")
            if isinstance(expected, int):
                return expected
            if isinstance(expected, str) and expected.isdigit():
                return int(expected)
    return None


def _guess_root_cause(detail: ApiExecutionDetail) -> Optional[str]:
    """Başarısız test için olasi root cause tahmini."""
    sc = detail.status_code
    error = (detail.error_message or "").lower()

    if sc == 401:
        return "authentication failure — expired or invalid token"
    elif sc == 403:
        return "authorization failure — insufficient permissions"
    elif sc == 404:
        return "endpoint not found — path may have changed or resource does not exist"
    elif sc == 409:
        return "conflict — possibly missing idempotency key or duplicate request"
    elif sc == 422:
        return "validation error — request body has invalid or missing fields"
    elif sc == 429:
        return "rate limit exceeded — too many requests in time window"
    elif sc == 500:
        return "server-side error — internal server error, check backend logs"
    elif sc == 502 or sc == 503:
        return "service unavailable — backend may be down or overloaded"
    elif sc is None and "timeout" in error:
        return "request timeout — endpoint did not respond in time"
    elif sc is None and ("connection" in error or "refused" in error):
        return "connection error — service may be unreachable"
    return None


def _extract_path(url: str) -> str:
    """URL'den path kismini cikar."""
    if not url:
        return "/"
    # http://host:port/path?query -> /path
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.path or "/"
    except Exception:
        # Basit fallback
        idx = url.find("://")
        if idx >= 0:
            rest = url[idx + 3:]
            slash_idx = rest.find("/")
            if slash_idx >= 0:
                return rest[slash_idx:].split("?")[0]
        return url


def _detect_and_store_recurring_failures(
    db: Session,
    store: KnowledgeStore,
    current_details: List[ApiExecutionDetail],
    test_cases_map: Dict[str, "ApiTestCase"],
    project_id: str,
    run_id: str,
) -> int:
    """
    Tekrarlayan hatalari tespit et: Bir endpoint için fail_count >= RECURRING_FAILURE_THRESHOLD
    olan test case'leri incele.
    """
    ingested = 0

    # Endpoint bazinda gruplandir (method + path)
    endpoint_failures = defaultdict(list)  # type: Dict[str, List[dict]]
    for detail in current_details:
        if not detail.passed:
            path = _extract_path(detail.actual_url)
            key = f"{detail.actual_method} {path}"
            tc = test_cases_map.get(detail.test_case_id) if detail.test_case_id else None
            endpoint_failures[key].append({
                "detail": detail,
                "test_case": tc,
            })

    for endpoint_key, failures in endpoint_failures.items():
        # Bu endpoint için mevcut run'daki failure sayisi
        current_fail_count = len(failures)

        # Test case'lerin kumulatif fail_count'una bak
        total_fail_count = 0
        total_run_count = 0
        for f in failures:
            tc = f.get("test_case")
            if tc:
                total_fail_count += tc.fail_count
                total_run_count += tc.run_count

        # Tekrarlayan hata mi?
        if total_fail_count >= RECURRING_FAILURE_THRESHOLD or current_fail_count >= RECURRING_FAILURE_THRESHOLD:
            # Yaygin hata mesajlarini topla
            common_errors = []  # type: List[str]
            status_codes = []  # type: List[int]
            for f in failures:
                d = f["detail"]
                if d.error_message:
                    common_errors.append(d.error_message[:100])
                if d.status_code:
                    status_codes.append(d.status_code)

            # En sik status code
            most_common_status = max(set(status_codes), key=status_codes.count) if status_codes else None

            # Ayni endpoint'te gecen testleri say
            passed_in_endpoint = sum(
                1 for d in current_details
                if d.passed and _extract_path(d.actual_url) == _extract_path(failures[0]["detail"].actual_url)
                and d.actual_method == failures[0]["detail"].actual_method
            )
            total_in_endpoint = current_fail_count + passed_in_endpoint

            text = (
                f"RECURRING FAILURE: {endpoint_key} consistently fails. "
                f"{current_fail_count} of {total_in_endpoint} test cases failed in this run. "
                f"Cumulative fail count: {total_fail_count}. "
            )

            if most_common_status:
                text += f"Common status code: {most_common_status}. "

            if common_errors:
                # En sik hata mesajı
                unique_errors = list(set(common_errors))[:3]
                text += f"Common errors: {'; '.join(unique_errors)}"

            metadata = {
                "type": "recurring_failure",
                "run_id": run_id,
                "project_id": project_id,
                "endpoint": endpoint_key,
                "fail_count": current_fail_count,
                "cumulative_fail_count": total_fail_count,
                "common_status_code": most_common_status,
            }

            try:
                store.ingest(text, source="insight", metadata=metadata)
                ingested += 1
            except Exception as exc:
                logger.debug("recurring_failure ingest hatasi: %s", exc)

    return ingested


def _calculate_endpoint_stats(
    details: List[ApiExecutionDetail],
) -> Dict[str, Dict[str, Any]]:
    """Endpoint bazinda pass/fail istatistikleri hesapla."""
    stats = defaultdict(lambda: {"passed": 0, "failed": 0, "total_ms": 0.0, "count": 0})

    for d in details:
        path = _extract_path(d.actual_url)
        key = f"{d.actual_method} {path}"
        stats[key]["count"] += 1
        if d.passed:
            stats[key]["passed"] += 1
        else:
            stats[key]["failed"] += 1
        stats[key]["total_ms"] += (d.total_ms or 0.0)

    return dict(stats)


def _build_stats_summary(
    endpoint_stats: Dict[str, Dict[str, Any]],
    run_id: str,
) -> Optional[str]:
    """Endpoint istatistiklerinden özet metin oluştur."""
    lines = [f"RUN SUMMARY (run_id={run_id}):"]

    for endpoint, stats in sorted(endpoint_stats.items()):
        count = stats["count"]
        passed = stats["passed"]
        failed = stats["failed"]
        avg_ms = stats["total_ms"] / count if count > 0 else 0.0
        pass_rate = (passed / count * 100) if count > 0 else 0.0

        line = f"  {endpoint}: {pass_rate:.0f}% pass rate ({passed}/{count}), avg {avg_ms:.0f}ms"
        lines.append(line)

    return "\n".join(lines) if len(lines) > 1 else None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# B. GET LEARNING CONTEXT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_learning_context(
    project_id: str,
    endpoints: Optional[List[str]] = None,
    mode: Optional[str] = None,
) -> str:
    """
    KnowledgeStore'dan ilgili ogrenimleri al ve formatli metin olarak don.

    Args:
        project_id: Proje ID'si
        endpoints: Filtrelenecek endpoint path listesi (orn: ["/api/v1/transfers"])
        mode: Çalışma modu — "test_generation" hata paternleri alir,
              "security_audit" guvenlik bulgularini alir

    Returns:
        Formatli ogrenme metni (bos string eger ogrenme yoksa)
    """
    try:
        store = KnowledgeStore(project_id=project_id)
    except Exception as exc:
        logger.warning("KnowledgeStore bağlantısı kurulamadi: %s", exc)
        return ""

    sections = []  # type: List[str]

    # ── Hata paternleri ──────────────────────────────────────────────
    error_patterns = _retrieve_error_patterns(store, project_id, endpoints)
    if error_patterns:
        lines = ["### Hata Paternleri (Son 30 gun)"]
        for pattern in error_patterns:
            lines.append(f"- {pattern}")
        sections.append("\n".join(lines))

    # ── Performans uyarilari ─────────────────────────────────────────
    perf_warnings = _retrieve_performance_warnings(store, project_id, endpoints)
    if perf_warnings:
        lines = ["### Performans Uyarilari"]
        for warning in perf_warnings:
            lines.append(f"- {warning}")
        sections.append("\n".join(lines))

    # ── Tekrarlayan sorunlar ─────────────────────────────────────────
    recurring = _retrieve_recurring_failures(store, project_id, endpoints)
    if recurring:
        lines = ["### Tekrarlayan Sorunlar"]
        for issue in recurring:
            lines.append(f"- {issue}")
        sections.append("\n".join(lines))

    # ── Mode bazinda ek bilgiler ─────────────────────────────────────
    if mode == "security_audit":
        security_findings = _retrieve_security_findings(store, project_id, endpoints)
        if security_findings:
            lines = ["### Guvenlik Bulgulari"]
            for finding in security_findings:
                lines.append(f"- {finding}")
            sections.append("\n".join(lines))

    if not sections:
        return ""

    return "\n\n".join(sections)


def _retrieve_error_patterns(
    store: KnowledgeStore,
    project_id: str,
    endpoints: Optional[List[str]] = None,
) -> List[str]:
    """KnowledgeStore'dan hata paternlerini al."""
    query = f"error patterns for project {project_id}"
    if endpoints:
        query += " endpoints: " + ", ".join(endpoints[:5])

    try:
        chunks = store.retrieve(
            query=query,
            top_k=10,
            sources=["error_pattern"],
            min_similarity=0.20,
        )
    except Exception:
        return []

    results = []  # type: List[str]
    for chunk in chunks:
        meta = chunk.metadata or {}
        # Proje filtresi — metadata'da project_id varsa kontrol et
        chunk_project = meta.get("project_id", "")
        if chunk_project and chunk_project != project_id:
            continue
        # Endpoint filtresi
        if endpoints:
            chunk_path = meta.get("path", "")
            if chunk_path and not any(ep in chunk_path for ep in endpoints):
                continue

        # Özet metin
        content = chunk.content
        if len(content) > 200:
            content = content[:200] + "..."
        results.append(content)

    return results[:10]


def _retrieve_performance_warnings(
    store: KnowledgeStore,
    project_id: str,
    endpoints: Optional[List[str]] = None,
) -> List[str]:
    """KnowledgeStore'dan performans uyarilarini al."""
    query = f"slow response performance warning project {project_id}"
    if endpoints:
        query += " " + " ".join(endpoints[:3])

    try:
        chunks = store.retrieve(
            query=query,
            top_k=5,
            sources=["insight"],
            min_similarity=0.20,
        )
    except Exception:
        return []

    results = []  # type: List[str]
    for chunk in chunks:
        meta = chunk.metadata or {}
        if meta.get("type") != "performance":
            continue
        chunk_project = meta.get("project_id", "")
        if chunk_project and chunk_project != project_id:
            continue
        if endpoints:
            chunk_path = meta.get("path", "")
            if chunk_path and not any(ep in chunk_path for ep in endpoints):
                continue

        content = chunk.content
        if len(content) > 200:
            content = content[:200] + "..."
        results.append(content)

    return results[:5]


def _retrieve_recurring_failures(
    store: KnowledgeStore,
    project_id: str,
    endpoints: Optional[List[str]] = None,
) -> List[str]:
    """KnowledgeStore'dan tekrarlayan hatalari al."""
    query = f"recurring failure consistently fails project {project_id}"
    if endpoints:
        query += " " + " ".join(endpoints[:3])

    try:
        chunks = store.retrieve(
            query=query,
            top_k=5,
            sources=["insight"],
            min_similarity=0.20,
        )
    except Exception:
        return []

    results = []  # type: List[str]
    for chunk in chunks:
        meta = chunk.metadata or {}
        if meta.get("type") != "recurring_failure":
            continue
        chunk_project = meta.get("project_id", "")
        if chunk_project and chunk_project != project_id:
            continue
        if endpoints:
            chunk_endpoint = meta.get("endpoint", "")
            if chunk_endpoint and not any(ep in chunk_endpoint for ep in endpoints):
                continue

        content = chunk.content
        if len(content) > 200:
            content = content[:200] + "..."
        results.append(content)

    return results[:5]


def _retrieve_security_findings(
    store: KnowledgeStore,
    project_id: str,
    endpoints: Optional[List[str]] = None,
) -> List[str]:
    """KnowledgeStore'dan guvenlik bulgularini al."""
    query = f"security vulnerability OWASP attack project {project_id}"
    if endpoints:
        query += " " + " ".join(endpoints[:3])

    try:
        chunks = store.retrieve(
            query=query,
            top_k=5,
            sources=["error_pattern", "insight"],
            min_similarity=0.20,
        )
    except Exception:
        return []

    results = []  # type: List[str]
    for chunk in chunks:
        meta = chunk.metadata or {}
        chunk_project = meta.get("project_id", "")
        if chunk_project and chunk_project != project_id:
            continue
        # Guvenlik ile ilgili icerikleri filtrele
        content_lower = chunk.content.lower()
        if any(kw in content_lower for kw in ["security", "owasp", "auth", "injection", "xss", "401", "403"]):
            content = chunk.content
            if len(content) > 200:
                content = content[:200] + "..."
            results.append(content)

    return results[:5]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# C. ENRICH GENERATION PROMPT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def enrich_generation_prompt(
    project_id: str,
    endpoints: Optional[List[dict]] = None,
    mode: Optional[str] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Test uretimi oncesi AI agent'a verilecek zenginlestirilmis baglam oluştur.

    Args:
        project_id: Proje ID'si
        endpoints: Endpoint dict listesi ([{method, path, ...}])
        mode: Çalışma modu (test_generation, security_audit, vb.)
        db: SQLAlchemy session (mevcut test sayisi hesabi için)

    Returns:
        {
            "learnings": str,
            "failure_patterns": List[str],
            "performance_baselines": List[str],
            "previously_generated_count": int,
        }
    """
    # Endpoint path'lerini cikar
    endpoint_paths = []  # type: List[str]
    if endpoints:
        for ep in endpoints:
            path = ep.get("path", "")
            if path:
                endpoint_paths.append(path)

    # Ogrenme baglamini al
    learnings = ""
    failure_patterns = []  # type: List[str]
    performance_baselines = []  # type: List[str]

    try:
        learnings = get_learning_context(
            project_id=project_id,
            endpoints=endpoint_paths if endpoint_paths else None,
            mode=mode,
        )

        # Failure patterns'i ayri olarak al
        store = KnowledgeStore(project_id=project_id)
        query = "test failure error pattern"
        if endpoint_paths:
            query += " " + " ".join(endpoint_paths[:3])

        try:
            error_chunks = store.retrieve(
                query=query,
                top_k=10,
                sources=["error_pattern"],
                min_similarity=0.20,
            )
            for chunk in error_chunks:
                meta = chunk.metadata or {}
                chunk_project = meta.get("project_id", "")
                if chunk_project and chunk_project != project_id:
                    continue
                if endpoint_paths:
                    chunk_path = meta.get("path", "")
                    if chunk_path and not any(ep in chunk_path for ep in endpoint_paths):
                        continue
                content = chunk.content
                if len(content) > 150:
                    content = content[:150] + "..."
                failure_patterns.append(content)
        except Exception:
            pass

        # Performance baselines
        try:
            perf_chunks = store.retrieve(
                query="slow response performance baseline",
                top_k=5,
                sources=["insight"],
                min_similarity=0.20,
            )
            for chunk in perf_chunks:
                meta = chunk.metadata or {}
                if meta.get("type") != "performance":
                    continue
                chunk_project = meta.get("project_id", "")
                if chunk_project and chunk_project != project_id:
                    continue
                path = meta.get("path", "unknown")
                total_ms = meta.get("total_ms", 0)
                performance_baselines.append(f"{meta.get('method', '?')} {path}: {total_ms:.0f}ms")
        except Exception:
            pass

    except Exception as exc:
        logger.warning("enrich_generation_prompt ogrenme hatasi: %s", exc)

    # Mevcut test sayisi
    previously_generated_count = 0
    if db and endpoint_paths:
        try:
            count = (
                db.query(ApiTestCase)
                .filter(
                    ApiTestCase.project_id == project_id,
                    ApiTestCase.request_path.in_(endpoint_paths),
                )
                .count()
            )
            previously_generated_count = count
        except Exception as exc:
            logger.debug("Mevcut test sayisi sorgu hatasi: %s", exc)

    return {
        "learnings": learnings,
        "failure_patterns": failure_patterns[:10],
        "performance_baselines": performance_baselines[:5],
        "previously_generated_count": previously_generated_count,
    }
