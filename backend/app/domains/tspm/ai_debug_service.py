"""
Nexus QA — Faz 6: AI Debug Loop Service
Başarısız test sonuçlarını analiz eder, kök neden sınıflandırır,
AI ile düzeltme önerisi üretir ve Allure-uyumlu JSON çıktısı sağlar.

Pipeline:
  1. Başarısız TspmExecutionResult'ları topla
  2. RootCauseAnalyzer ile hızlı sınıflandır
  3. AI Gateway'e gönder → detaylı analiz + fix önerisi
  4. Allure JSON format'ına dönüştür
  5. Sonuçları döndür (DB kaydı opsiyonel)
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("nexusqa.ai_debug")

# ── System prompt ─────────────────────────────────────────────────────────────

_DEBUG_SYSTEM_PROMPT = """\
Sen kıdemli bir QA mühendisisin. Sana başarısız olan otomatik test sonuçları verilecek.
Her başarısız test için:
1. Kök nedeni sınıflandır (PRODUCT_BUG / TEST_ISSUE / ENVIRONMENT / AUTOMATION_DEBT / FLAKY / RACE_CONDITION)
2. Somut düzeltme adımlarını listele
3. Benzer testlerin de başarısız olup olmayacağını tahmin et
4. Risk seviyesi ata

Kategori rehberi:
- PRODUCT_BUG: Uygulama kodundan kaynaklanan gerçek hata
- TEST_ISSUE: Stale locator, yanlış assertion, kırık test kodu
- ENVIRONMENT: Servis kapalı, config hatası, ağ sorunu
- AUTOMATION_DEBT: Bakımsız test altyapısı, güncel olmayan bağımlılık
- FLAKY: Tutarsız sonuç veren test — bazen geçer bazen geçmez (timing, async, test izolasyon eksikliği)
- RACE_CONDITION: Eş zamanlı işlem çakışması — double-spend, concurrent write, deadlock (bankacılık testlerinde kritik)

MUTLAKA şu JSON formatında yanıt ver:
{
  "analyses": [
    {
      "test_id": "string",
      "root_cause_category": "PRODUCT_BUG|TEST_ISSUE|ENVIRONMENT|AUTOMATION_DEBT|FLAKY|RACE_CONDITION",
      "root_cause_subcategory": "string",
      "confidence": 0.0-1.0,
      "fix_steps": ["adım 1", "adım 2"],
      "estimated_fix_time": "30 dakika",
      "risk_level": "critical|high|medium|low",
      "similar_tests_at_risk": ["test başlığı"],
      "explanation": "Türkçe kısa açıklama"
    }
  ],
  "overall_health": "healthy|at_risk|critical",
  "key_patterns": ["pattern 1", "pattern 2"],
  "recommended_actions": ["aksiyon 1", "aksiyon 2"]
}"""


# ── Prompt builder ─────────────────────────────────────────────────────────────

def _build_debug_prompt(failed_results: list[dict[str, Any]]) -> str:
    entries = []
    for r in failed_results[:10]:  # max 10 başarısız test
        error_info = ""
        if r.get("error_message"):
            error_info = f"  Hata: {r['error_message'][:300]}"
        if r.get("error_type"):
            error_info = f"  Hata Türü: {r['error_type']}\n" + error_info

        if r.get("stack_trace"):
            error_info += f"\n  Stack Trace (ilk 200 kar.): {r['stack_trace'][:200]}"

        steps_info = ""
        if r.get("failed_step"):
            steps_info = f"  Başarısız Adım: {r['failed_step']}"

        entries.append(
            f"Test ID: {r.get('test_id','?')}\n"
            f"  Başlık: {r.get('title','?')}\n"
            f"  Modül: {r.get('module','?')}\n"
            f"  Öncelik: {r.get('severity','medium')}\n"
            f"{error_info}\n"
            f"{steps_info}"
        )

    prompt_body = "\n\n".join(entries)
    return f"Aşağıdaki {len(failed_results)} başarısız test sonucunu analiz et:\n\n{prompt_body}"


# ── Allure JSON builder ───────────────────────────────────────────────────────

def build_allure_results(
    execution_id: str,
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Test sonuçlarından Allure-uyumlu JSON nesneleri üretir.
    Her nesne allure-results/ klasörüne {uuid}-result.json olarak yazılabilir.
    """
    allure_results = []

    for r in results:
        status = r.get("status", "unknown")
        # Allure status mapping
        allure_status = {
            "passed": "passed",
            "failed": "failed",
            "skipped": "skipped",
            "broken": "broken",
        }.get(status, "unknown")

        steps = []
        for step in r.get("steps", []):
            step_status = "passed" if step.get("status") in ("passed", "pass") else "failed"
            steps.append({
                "name": step.get("action") or step.get("text") or f"Adım {step.get('order', '?')}",
                "status": step_status,
                "stage": "finished",
                "start": r.get("start_ms", 0),
                "stop": r.get("start_ms", 0) + step.get("duration_ms", 0),
                "parameters": [],
            })

        labels = [
            {"name": "suite", "value": r.get("module", "default")},
            {"name": "severity", "value": r.get("severity", "medium")},
            {"name": "framework", "value": "NexusQA"},
        ]
        for tag in r.get("tags", []):
            labels.append({"name": "tag", "value": tag})

        status_details: dict[str, Any] = {}
        if r.get("error_message"):
            status_details = {
                "message": r["error_message"][:500],
                "trace": r.get("stack_trace", ""),
            }

        result_uuid = str(uuid.uuid4())
        allure_obj: dict[str, Any] = {
            "uuid": result_uuid,
            "historyId": f"{execution_id}_{r.get('test_id', result_uuid)}",
            "testCaseId": r.get("scenario_id") or r.get("test_id", result_uuid),
            "fullName": f"{r.get('module','')}.{r.get('title','')}",
            "name": r.get("title", "Unnamed Test"),
            "status": allure_status,
            "stage": "finished",
            "start": r.get("start_ms", int(datetime.now(timezone.utc).timestamp() * 1000)),
            "stop": r.get("stop_ms", int(datetime.now(timezone.utc).timestamp() * 1000)),
            "labels": labels,
            "links": [],
            "parameters": [],
            "steps": steps,
            "statusDetails": status_details,
            "description": r.get("description", ""),
        }
        allure_results.append(allure_obj)

    return allure_results


def build_allure_environment(
    project_name: str,
    base_url: str,
    browser: str = "chromium",
    extra: Optional[dict] = None,
) -> str:
    """Allure environment.properties içeriği üretir."""
    lines = [
        f"Project={project_name}",
        f"Base.URL={base_url}",
        f"Browser={browser}",
        f"Generated.At={datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "Framework=NexusQA",
    ]
    if extra:
        for k, v in extra.items():
            lines.append(f"{k}={v}")
    return "\n".join(lines)


def build_allure_executor(
    execution_id: str,
    execution_name: str,
    project_id: str,
) -> dict[str, Any]:
    """Allure executor.json içeriği üretir."""
    return {
        "name": "NexusQA",
        "type": "nexusqa",
        "url": f"/p/{project_id}/runs",
        "buildOrder": 1,
        "buildName": execution_name,
        "buildUrl": f"/p/{project_id}/executions/{execution_id}",
        "reportName": f"NexusQA Execution {execution_id[:8]}",
    }


# ── AI Debug Analysis ──────────────────────────────────────────────────────────

def analyze_failed_tests_with_ai(
    failed_results: list[dict[str, Any]],
    project_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Başarısız testleri AI Gateway ile analiz et.
    Returns: {
        analyses: [{test_id, root_cause_category, fix_steps, ...}],
        overall_health: str,
        key_patterns: [str],
        recommended_actions: [str],
        ai_provider: str,
        fallback_used: bool,
    }
    """
    if not failed_results:
        return {
            "analyses": [],
            "overall_health": "healthy",
            "key_patterns": [],
            "recommended_actions": [],
            "ai_provider": "none",
            "fallback_used": False,
        }

    prompt = _build_debug_prompt(failed_results)

    # Try AI Gateway
    try:
        from app.domains.ai.gateway_client import gateway_complete, gateway_is_available
        if gateway_is_available():
            raw = gateway_complete(
                task_type="debug_test",
                user_message=prompt,
                system_message=_DEBUG_SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=4000,
                project_id=project_id,
            )
            parsed = _parse_debug_response(raw)
            parsed["ai_provider"] = "gateway"
            parsed["fallback_used"] = False
            logger.info(f"AI debug analizi tamamlandı: {len(parsed.get('analyses', []))} sonuç")
            return parsed
    except Exception as e:
        logger.warning(f"AI Gateway debug analizi başarısız: {e}")

    # Fallback: rule-based classification
    logger.info("Kural tabanlı debug analizi kullanılıyor")
    return _rule_based_analysis(failed_results)


def _parse_debug_response(raw: str) -> dict[str, Any]:
    """AI yanıtından JSON parse et."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError("AI yanıtı geçerli JSON değil")

    return {
        "analyses": data.get("analyses", []),
        "overall_health": data.get("overall_health", "at_risk"),
        "key_patterns": data.get("key_patterns", []),
        "recommended_actions": data.get("recommended_actions", []),
    }


def _rule_based_analysis(
    failed_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    AI unavailable fallback: kural tabanlı hata sınıflandırması.
    RootCauseAnalyzer mantığını yeniden kullanır.
    """
    from app.domains.tspm.reporting import RootCauseAnalyzer, TestStatus, TestResult, ErrorInfo

    _FLAKY_KEYWORDS = ("flaky", "intermittent", "sporadic", "sometimes", "random", "non-deterministic")
    _RACE_KEYWORDS = ("race condition", "concurrent", "deadlock", "double-spend", "double spend",
                      "concurrentmodification", "optimistic lock", "transaction conflict", "serialization failure")

    analyses = []
    for r in failed_results:
        error_msg = r.get("error_message", "").lower()
        error_type = r.get("error_type", "").lower()
        combined = f"{error_msg} {error_type}"

        if any(kw in combined for kw in _RACE_KEYWORDS):
            category, subcategory = "RACE_CONDITION", "concurrent_write"
            confidence, explanation = 0.75, "Hata mesajında eş zamanlı işlem belirtisi tespit edildi"
        elif any(kw in combined for kw in _FLAKY_KEYWORDS):
            category, subcategory = "FLAKY", "timing"
            confidence, explanation = 0.70, "Hata mesajında tutarsız/intermittent test belirtisi tespit edildi"
        else:
            rc = RootCauseAnalyzer.classify(r.get("error_message", ""), r.get("error_type", ""))
            category, subcategory = rc.category.value, rc.subcategory
            confidence, explanation = 0.6, rc.description

        fix_steps = _default_fix_steps(category, subcategory)
        analyses.append({
            "test_id": r.get("test_id", "?"),
            "root_cause_category": category,
            "root_cause_subcategory": subcategory,
            "confidence": confidence,
            "fix_steps": fix_steps,
            "estimated_fix_time": "15-30 dakika",
            "risk_level": r.get("severity", "medium"),
            "similar_tests_at_risk": [],
            "explanation": explanation,
        })

    # Determine overall health
    critical_count = sum(1 for a in analyses if a["root_cause_category"] == "PRODUCT_BUG")
    env_count = sum(1 for a in analyses if a["root_cause_category"] == "ENVIRONMENT")
    total = len(analyses)

    if total == 0:
        overall_health = "healthy"
    elif critical_count / total > 0.5:
        overall_health = "critical"
    elif env_count / total > 0.3:
        overall_health = "at_risk"
    else:
        overall_health = "at_risk"

    # Key patterns
    categories: dict[str, int] = {}
    for a in analyses:
        cat = a["root_cause_category"]
        categories[cat] = categories.get(cat, 0) + 1

    patterns = [f"{count} test '{cat}' kategorisinde" for cat, count in sorted(categories.items(), key=lambda x: -x[1])]

    return {
        "analyses": analyses,
        "overall_health": overall_health,
        "key_patterns": patterns,
        "recommended_actions": _default_recommended_actions(categories),
        "ai_provider": "rule_based",
        "fallback_used": True,
    }


def _default_fix_steps(category: str, subcategory: str) -> list[str]:
    fixes: dict[tuple[str, str], list[str]] = {
        ("PRODUCT_BUG", "functional"): [
            "Hata mesajını ve stack trace'i incele",
            "İlgili uygulama kodunu kontrol et",
            "Geliştiriciye bug raporu oluştur",
            "Düzeltme sonrası regression testini çalıştır",
        ],
        ("TEST_ISSUE", "stale_locator"): [
            "Başarısız olan selector'ı tarayıcıda manuel kontrol et",
            "data-testid veya getByRole kullanacak şekilde güncelle",
            "Testi yerel ortamda çalıştır ve doğrula",
        ],
        ("TEST_ISSUE", "timing"): [
            "Bekleme süresini artır (waitForSelector, waitForTimeout)",
            "Sabit beklemeler yerine koşullu bekleme kullan",
            "Network isteklerinin tamamlanmasını bekle",
        ],
        ("ENVIRONMENT", "infra_down"): [
            "Servis durumunu kontrol et (docker ps / kubectl get pods)",
            "Log dosyalarını incele",
            "Servisi yeniden başlat",
            "Ortam değişkenlerini doğrula",
        ],
        ("ENVIRONMENT", "config"): [
            ".env dosyasını kontrol et",
            "Ortam değişkenlerinin set edildiğini doğrula",
            "CI/CD pipeline konfigürasyonunu gözden geçir",
        ],
        ("FLAKY", "timing"): [
            "Testi 3 kez arka arkaya çalıştır, tutarsızlığı belgele",
            "Sabit sleep() çağrılarını waitForCondition ile değiştir",
            "Test izolasyonunu kontrol et: önceki test state'i temizleniyor mu?",
            "CI'da retry mekanizması ekle (maksimum 2 retry)",
        ],
        ("FLAKY", "async"): [
            "Async işlemlerin tamamlandığını bekleyen assertion ekle",
            "Promise/Future resolve olmadan assertion yapılmıyor mu kontrol et",
            "Network mock veya stub kullanımını değerlendir",
        ],
        ("RACE_CONDITION", "concurrent_write"): [
            "Eş zamanlı işlemleri seri hale getiren lock mekanizması ekle",
            "DB transaction isolation level'ı kontrol et (SERIALIZABLE önerilir)",
            "İşlem öncesi ve sonrası balance/state kontrolü yap",
            "Concurrent test senaryosunu tek thread'de çalıştır ve sonucu doğrula",
        ],
        ("RACE_CONDITION", "double_spend"): [
            "İdempotency key implementasyonunu kontrol et",
            "Optimistic lock (version field) veya pessimistic lock var mı doğrula",
            "Aynı işlemi 2 eş zamanlı request ile tekrar test et",
            "BDDK çift ödeme önleme kurallarına uygunluğu değerlendir",
        ],
    }
    default = ["Hatayı incele", "Gerekli düzeltmeyi yap", "Testi yeniden çalıştır"]
    return fixes.get((category, subcategory), default)


def _default_recommended_actions(categories: dict[str, int]) -> list[str]:
    actions = []
    if categories.get("PRODUCT_BUG", 0) > 0:
        actions.append(f"{categories['PRODUCT_BUG']} ürün hatası için geliştiriciye jira ticket aç")
    if categories.get("TEST_ISSUE", 0) > 0:
        actions.append(f"{categories['TEST_ISSUE']} test kodunu güncelle (locator/timing)")
    if categories.get("ENVIRONMENT", 0) > 0:
        actions.append("Ortam bileşenlerini kontrol et ve servisleri sağlıklı duruma getir")
    if categories.get("AUTOMATION_DEBT", 0) > 0:
        actions.append("Otomasyon borç sprint'i planla")
    if categories.get("FLAKY", 0) > 0:
        actions.append(f"{categories['FLAKY']} flaky test için retry + izolasyon analizi yap")
    if categories.get("RACE_CONDITION", 0) > 0:
        actions.append(f"{categories['RACE_CONDITION']} race condition testi için concurrent senaryo planı oluştur ve DB lock stratejisini gözden geçir")
    if not actions:
        actions.append("Hataları tek tek inceleyerek uygun aksiyonları al")
    return actions


# ── Main Faz 6 Entry Point ─────────────────────────────────────────────────────

def run_debug_loop(
    execution_id: str,
    project_id: str,
    results: list[dict[str, Any]],
    generate_allure: bool = True,
) -> dict[str, Any]:
    """
    Faz 6 ana pipeline:
      1. Başarısız testleri filtrele
      2. AI debug analizi
      3. Allure JSON üret
      4. Sonuçları döndür

    Args:
        execution_id: TspmExecution.id
        project_id: TspmProject.id
        results: [{test_id, title, module, status, error_message, error_type, steps, tags, severity, ...}]
        generate_allure: Allure JSON üretilsin mi?

    Returns:
        {
            execution_id, project_id,
            debug_analysis: {...},
            allure_results: [...] (eğer generate_allure=True),
            summary: {total, failed, pass_rate, health},
        }
    """
    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "passed")
    failed = sum(1 for r in results if r.get("status") == "failed")
    skipped = total - passed - failed
    pass_rate = round(passed / total * 100, 1) if total > 0 else 0.0

    failed_results = [r for r in results if r.get("status") == "failed"]

    # 1. AI Debug Analysis
    debug_analysis = analyze_failed_tests_with_ai(failed_results, project_id=project_id)

    # 2. Allure JSON
    allure_data: list[dict[str, Any]] = []
    if generate_allure:
        allure_data = build_allure_results(execution_id, results)

    return {
        "execution_id": execution_id,
        "project_id": project_id,
        "debug_analysis": debug_analysis,
        "allure_results": allure_data,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": pass_rate,
            "health": debug_analysis.get("overall_health", "unknown"),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
