"""
AI Root-Cause Analizi (Test Failure RCA)
═══════════════════════════════════════════════════════════════════════════

mabl / Testsigma tarzı: bir test fail olduğunda **neden** başarısız olduğunu
otomatik açıklar ve sınıflandırır. Bir test sonucundan değil, ham hata
sinyallerinden (mesaj, stack, adım, DOM, console) çalışır.

Taksonomi backend ile birebir hizalı:
``backend/app/domains/tspm/reporting.py::RootCauseCategory``
  PRODUCT_BUG · TEST_ISSUE · ENVIRONMENT · AUTOMATION_DEBT · UNKNOWN

İki katman:
  1. **Heuristik sınıflandırma** (LLM'siz) — hata desenlerinden hızlı, deterministik
     kategori + güven. LLM erişimi yoksa tek başına kullanılır.
  2. **LLM zenginleştirme** — gateway varsa açıklama (TR), kanıt ve önerilen
     düzeltme üretir; heuristik kategoriyi doğrular/düzeltir.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

CATEGORIES = ("PRODUCT_BUG", "TEST_ISSUE", "ENVIRONMENT", "AUTOMATION_DEBT", "UNKNOWN")

# ── Heuristik desenler (regex → kategori, açıklama) ──────────────────────────
# Sıra önemli: ilk eşleşen kazanır. Spesifikten genele.
_HEURISTICS: list[tuple[str, str, str]] = [
    (r"econnrefused|connection refused|connection reset|getaddrinfo|"
     r"net::err|dns|ssl|certificate|503 service|502 bad gateway|504 gateway",
     "ENVIRONMENT", "Ağ/altyapı erişim hatası (servis ayakta değil veya erişilemiyor)"),
    (r"timeout|timed out|waiting for selector|exceeded.*ms|navigation timeout",
     "AUTOMATION_DEBT", "Element/sayfa beklenen sürede gelmedi — zayıf bekleme veya kararsız locator"),
    (r"no element|element not found|not visible|not attached|"
     r"locator.*resolved to|selector.*did not|stale element|no node found",
     "AUTOMATION_DEBT", "Locator artık eşleşmiyor — UI değişmiş olabilir (self-healing adayı)"),
    (r"assert|expected.*but.*got|to equal|to contain|to be visible|"
     r"tohavetext|tobe\b|mismatch|beklenen",
     "PRODUCT_BUG", "Beklenen ile gerçek çıktı uyuşmuyor — uygulama davranışı hatalı olabilir"),
    (r"undefined is not|typeerror|referenceerror|nullpointer|"
     r"keyerror|attributeerror|traceback|syntaxerror|importerror",
     "TEST_ISSUE", "Test kodu/otomasyon hatası (kod istisnası)"),
    (r"401|403|unauthorized|forbidden|login failed|invalid credentials|oturum",
     "ENVIRONMENT", "Kimlik/oturum sorunu (test verisi veya ortam credential'ı)"),
]


def heuristic_classify(error_message: str, stack_trace: str = "") -> dict:
    """Hata metninden hızlı, deterministik kategori tahmini (LLM'siz)."""
    blob = f"{error_message}\n{stack_trace}".lower()
    for pattern, category, reason in _HEURISTICS:
        if re.search(pattern, blob):
            return {"category": category, "confidence": 0.6, "reason": reason, "source": "heuristic"}
    return {"category": "UNKNOWN", "confidence": 0.2,
            "reason": "Bilinen bir desene uymadı", "source": "heuristic"}


def _build_prompt(ctx: dict) -> str:
    parts = [f"Test adı: {ctx.get('test_name') or '(bilinmiyor)'}"]
    if ctx.get("failed_step"):
        parts.append(f"Başarısız adım: {ctx['failed_step']}")
    parts.append(f"Hata mesajı:\n{ctx.get('error_message') or '(yok)'}")
    if ctx.get("stack_trace"):
        parts.append(f"Stack trace (kısaltılmış):\n{ctx['stack_trace'][:1500]}")
    if ctx.get("html_snippet"):
        parts.append(f"DOM parçası:\n{ctx['html_snippet'][:1200]}")
    if ctx.get("console_logs"):
        logs = ctx["console_logs"]
        if isinstance(logs, list):
            logs = "\n".join(str(x) for x in logs[:15])
        parts.append(f"Console logları:\n{str(logs)[:1000]}")
    return "\n\n".join(parts)


def analyze_failure(
    test_name: str = "",
    error_message: str = "",
    stack_trace: str = "",
    failed_step: str = "",
    html_snippet: str = "",
    console_logs=None,
    use_llm: bool = True,
) -> dict:
    """Tek bir test başarısızlığının kök nedenini üretir.

    Dönüş::

        {
          "category": "AUTOMATION_DEBT",
          "confidence": 0.0-1.0,
          "explanation": "<TR açıklama>",
          "evidence": ["..."],
          "suggested_fix": "<TR öneri>",
          "source": "llm" | "heuristic" | "llm+heuristic"
        }
    """
    ctx = {
        "test_name": test_name, "error_message": error_message,
        "stack_trace": stack_trace, "failed_step": failed_step,
        "html_snippet": html_snippet, "console_logs": console_logs,
    }
    heur = heuristic_classify(error_message, stack_trace)

    if not use_llm:
        return {
            "category": heur["category"], "confidence": heur["confidence"],
            "explanation": heur["reason"], "evidence": [], "suggested_fix": "",
            "source": "heuristic",
        }

    try:
        from services import get_llm_gateway
        from core.auto_discovery import _extract_json

        gw = get_llm_gateway()
        if not gw.available:
            raise RuntimeError("LLM gateway erişilemez")

        system = (
            "Sen kıdemli bir QA/SDET uzmanısın. Bir başarısız testin sinyallerini "
            "okuyup KÖK NEDENİ sınıflandırırsın. Kategoriler: "
            "PRODUCT_BUG (uygulama hatası), TEST_ISSUE (test kodu/veri hatası), "
            "ENVIRONMENT (altyapı/ağ/ortam), AUTOMATION_DEBT (kararsız locator/bekleme), "
            "UNKNOWN. Türkçe, kısa ve teknik yaz."
        )
        user = f"""Aşağıdaki başarısız test için kök neden analizi yap.

{_build_prompt(ctx)}

Heuristik ön-tahmin: {heur['category']} ({heur['reason']}). Katılıyorsan kullan, katılmıyorsan düzelt.

SADECE şu JSON'u döndür:
{{
  "category": "PRODUCT_BUG|TEST_ISSUE|ENVIRONMENT|AUTOMATION_DEBT|UNKNOWN",
  "confidence": 0.0-1.0,
  "explanation": "Neden bu kategori — 1-3 cümle TR",
  "evidence": ["mesajdan/stack'ten alıntılanan kısa kanıtlar"],
  "suggested_fix": "Somut düzeltme önerisi TR"
}}"""

        resp = gw.complete(
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.1, max_tokens=800,
        )
        data = _extract_json(resp.content)
        category = str(data.get("category", "")).strip().upper()
        if category not in CATEGORIES:
            category = heur["category"]
        try:
            confidence = float(data.get("confidence", heur["confidence"]))
        except (TypeError, ValueError):
            confidence = heur["confidence"]
        evidence = data.get("evidence") or []
        if not isinstance(evidence, list):
            evidence = [str(evidence)]
        return {
            "category": category,
            "confidence": max(0.0, min(1.0, confidence)),
            "explanation": str(data.get("explanation", "")).strip() or heur["reason"],
            "evidence": [str(e) for e in evidence][:6],
            "suggested_fix": str(data.get("suggested_fix", "")).strip(),
            "source": "llm+heuristic",
        }
    except Exception as exc:
        logger.warning("RCA LLM adımı başarısız, heuristik'e düşülüyor: %s", exc)
        return {
            "category": heur["category"], "confidence": heur["confidence"],
            "explanation": heur["reason"], "evidence": [], "suggested_fix": "",
            "source": "heuristic",
        }


def analyze_batch(failures: list[dict], use_llm: bool = True) -> dict:
    """Birden çok başarısızlığı analiz eder ve kategori dağılımını özetler.

    ``failures`` her biri analyze_failure parametrelerini içeren dict listesi.
    """
    results = []
    for f in failures:
        res = analyze_failure(
            test_name=f.get("test_name", ""),
            error_message=f.get("error_message", ""),
            stack_trace=f.get("stack_trace", ""),
            failed_step=f.get("failed_step", ""),
            html_snippet=f.get("html_snippet", ""),
            console_logs=f.get("console_logs"),
            use_llm=use_llm,
        )
        res["test_name"] = f.get("test_name", "")
        results.append(res)

    distribution: dict[str, int] = {}
    for r in results:
        distribution[r["category"]] = distribution.get(r["category"], 0) + 1

    return {
        "results": results,
        "total": len(results),
        "distribution": distribution,
        "dominant_category": max(distribution, key=distribution.get) if distribution else None,
    }
