"""Nexus Repo — LLM Senaryo Üreticisi.

Ollama (yerel) veya OpenAI/Anthropic ile repo analizi yapılmış veriyi
manuel / servis / otomasyon test senaryolarına dönüştürür.

Akış:
  1. CrawlJob → dosya özetleri + endpoint listesi DB'den çekilir
  2. Bağlam penceresi oluşturulur (token limiti korunur)
  3. LLM'e senaryo üretim isteği gönderilir (JSON formatı)
  4. Yanıt parse edilir → NexusScenario + NexusCase kayıtları
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

from sqlalchemy.orm import Session

from app.infra.database import SessionLocal
from .models import (
    NexusCrawlJob,
    NexusEndpoint,
    NexusFile,
    NexusLLMLog,
    NexusProject,
    NexusScenario,
    NexusCase,
)

_log = logging.getLogger(__name__)

# Bağlam penceresine sığdırılacak maksimum karakter
_MAX_CONTEXT_CHARS = 12_000

# Bir istekte üretilecek maksimum senaryo sayısı
_DEFAULT_MAX_SCENARIOS = 20


# ── Prompt Şablonları ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT_TR = """Sen kıdemli bir yazılım test mühendisisin.
Sana bir yazılım projesine ait kaynak kodu özeti ve API endpoint listesi verilecek.

Görevin: Bu bilgileri kullanarak kapsamlı test senaryoları üret.

ÇIKTI KURALLARI:
- Yanıtın YALNIZCA geçerli JSON olmalı, başka metin içermemeli.
- Üst seviye anahtar: "scenarios" (dizi)
- Her senaryo şu alanlara sahip olmalı:
  {
    "title": "kısa, açıklayıcı başlık",
    "type": "manual" | "service" | "automation",
    "feature_area": "ilgili modül/özellik adı",
    "priority": "low" | "medium" | "high" | "critical",
    "gherkin": "Feature: ...\n  Scenario: ...\n    Given ...\n    When ...\n    Then ...",
    "notes": "varsa ek açıklama",
    "cases": [
      {
        "name": "test case adı",
        "preconditions": "ön koşullar",
        "steps": [
          {"type": "given|when|then", "step": "adım metni", "expected": "beklenen sonuç"}
        ],
        "expected_result": "genel beklenen sonuç",
        "test_data": {"alan": "örnek değer"}
      }
    ]
  }

Senaryo tipleri:
- manual: İnsan tarafından elle yürütülen; adımlar net ve anlaşılır olmalı
- service: API/backend servisi testi; HTTP metod, endpoint, istek/yanıt gövdesi belirtilmeli
- automation: UI otomasyon; Playwright/Selenium adımları; locator ipuçları eklenebilir

Mutlaka pozitif (happy path), negatif (hata durumu) ve sınır değer testlerini dahil et.
Türkçe yaz."""

_SYSTEM_PROMPT_EN = """You are a senior software test engineer.
You will be given a summary of a software project's source code and API endpoint list.

Your task: Generate comprehensive test scenarios from this information.

OUTPUT RULES:
- Your response MUST be valid JSON only, no other text.
- Top-level key: "scenarios" (array)
- Each scenario must have:
  {
    "title": "short descriptive title",
    "type": "manual" | "service" | "automation",
    "feature_area": "related module/feature name",
    "priority": "low" | "medium" | "high" | "critical",
    "gherkin": "Feature: ...\n  Scenario: ...\n    Given ...\n    When ...\n    Then ...",
    "notes": "optional notes",
    "cases": [
      {
        "name": "test case name",
        "preconditions": "preconditions",
        "steps": [
          {"type": "given|when|then", "step": "step text", "expected": "expected result"}
        ],
        "expected_result": "overall expected result",
        "test_data": {"field": "example value"}
      }
    ]
  }

Include positive (happy path), negative (error cases), and boundary value tests."""


# ── LLM Çağrısı ──────────────────────────────────────────────────────────────

def _build_context(
    project: NexusProject,
    endpoints: list[NexusEndpoint],
    files: list[NexusFile],
    language: str,
) -> str:
    """LLM için bağlam metni oluştur."""
    lines: list[str] = [
        f"PROJE: {project.name}",
        f"REPO: {project.repo_url} (dal: {project.branch})",
        "",
        f"TARAMA SONUCU: {len(files)} kaynak dosya, {len(endpoints)} API endpoint",
        "",
    ]

    # Endpoint listesi
    if endpoints:
        lines.append("── API ENDPOINT'LERİ ──")
        for ep in endpoints[:80]:  # En fazla 80 endpoint
            auth_hint = " [AUTH]" if ep.auth_required else ""
            lines.append(f"  {ep.method:6} {ep.path}{auth_hint}  ({ep.source_file or ''}:{ep.source_line or ''})")
        if len(endpoints) > 80:
            lines.append(f"  ... ve {len(endpoints) - 80} endpoint daha")
        lines.append("")

    # Dosya özeti
    if files:
        lines.append("── KAYNAK DOSYALAR ──")
        by_lang: dict[str, int] = {}
        for f in files:
            lang = f.language or "diğer"
            by_lang[lang] = by_lang.get(lang, 0) + 1
        for lang, count in sorted(by_lang.items(), key=lambda x: -x[1]):
            lines.append(f"  {lang}: {count} dosya")
        lines.append("")

        # Dosya özetleri (varsa)
        for f in files[:20]:
            if f.summary:
                lines.append(f"  [{f.path}] {f.summary}")

    text = "\n".join(lines)
    # Token limiti koru
    if len(text) > _MAX_CONTEXT_CHARS:
        text = text[:_MAX_CONTEXT_CHARS] + "\n...[bağlam kısaltıldı]"
    return text


def _call_gateway(
    system_prompt: str,
    user_prompt: str,
) -> tuple[str, int, int, int]:
    """AI Gateway üzerinden senaryo üret. (yanıt, prompt_token, completion_token, latency_ms) döndür.

    Gateway fallback zincirini (vLLM→Ollama→Groq→Gemini) yönetir; PII redaction,
    semantik cache ve rate-limit izleme otomatik olarak uygulanır.
    Token sayıları gateway yanıtında raporlanmadığından karakter/4 yaklaşımıyla tahmin edilir.
    """
    from app.domains.ai.gateway_client import gateway_complete

    start = time.time()
    raw = gateway_complete(
        task_type="scenario_generation",
        user_message=user_prompt,
        system_message=system_prompt,
        temperature=0.3,
        max_tokens=6000,
        json_mode=True,
    )
    latency_ms = int((time.time() - start) * 1000)
    prompt_tokens = (len(system_prompt) + len(user_prompt)) // 4
    completion_tokens = len(raw) // 4
    return raw, prompt_tokens, completion_tokens, latency_ms


def _parse_scenarios(raw: str) -> list[dict]:
    """LLM yanıtından senaryo listesi parse et."""
    text = raw.strip()
    # Markdown fence temizle
    fence = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Kırpılmış JSON kurtarma denemesi
        last_brace = text.rfind("}")
        if last_brace > 0:
            try:
                data = json.loads(text[: last_brace + 1] + "}")
            except Exception:
                return []
        else:
            return []

    if isinstance(data, dict):
        scenarios = data.get("scenarios", [])
    elif isinstance(data, list):
        scenarios = data
    else:
        return []
    return scenarios if isinstance(scenarios, list) else []


# ── Ana İş Fonksiyonu ─────────────────────────────────────────────────────────

def run_generate_job(
    project_id: str,
    crawl_job_id: str,
    scenario_types: Optional[list[str]] = None,
    max_scenarios: int = _DEFAULT_MAX_SCENARIOS,
    language: str = "tr",
) -> None:
    """Arka planda çalıştırılacak senaryo üretim fonksiyonu."""
    db: Session = SessionLocal()
    try:
        project: Optional[NexusProject] = db.query(NexusProject).filter(NexusProject.id == project_id).first()
        if not project:
            _log.error("Proje bulunamadı: %s", project_id)
            return

        crawl_job: Optional[NexusCrawlJob] = db.query(NexusCrawlJob).filter(
            NexusCrawlJob.id == crawl_job_id,
            NexusCrawlJob.project_id == project_id,
        ).first()
        if not crawl_job or crawl_job.status != "done":
            _log.warning("CrawlJob hazır değil: %s (durum: %s)", crawl_job_id, getattr(crawl_job, "status", "?"))
            return

        endpoints = db.query(NexusEndpoint).filter(NexusEndpoint.crawl_job_id == crawl_job_id).all()
        files = db.query(NexusFile).filter(NexusFile.crawl_job_id == crawl_job_id).all()

        # Sistem ve kullanıcı promptu hazırla
        system_prompt = _SYSTEM_PROMPT_TR if language == "tr" else _SYSTEM_PROMPT_EN
        context = _build_context(project, endpoints, files, language)
        types_str = ", ".join(scenario_types or ["manual", "service", "automation"])
        user_prompt = (
            f"{context}\n\n"
            f"Lütfen bu proje için en fazla {max_scenarios} adet test senaryosu üret.\n"
            f"Senaryo tipleri: {types_str}\n"
            "Sonucu JSON formatında döndür."
        )

        # LLM çağrısı
        raw_response = ""
        prompt_tokens = completion_tokens = latency_ms = 0
        success = True
        error_msg: Optional[str] = None

        try:
            raw_response, prompt_tokens, completion_tokens, latency_ms = _call_gateway(
                system_prompt, user_prompt,
            )

        except Exception as exc:
            _log.exception("LLM çağrısı başarısız: %s", exc)
            success = False
            error_msg = str(exc)

        # LLM log kaydı
        llm_log = NexusLLMLog(
            project_id=project_id,
            operation="scenario_gen",
            model=project.llm_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            success=success,
            error=error_msg,
        )
        db.add(llm_log)
        db.flush()

        if not success or not raw_response:
            db.commit()
            return

        # Yanıtı parse et ve kaydet
        scenarios_data = _parse_scenarios(raw_response)
        saved = 0

        for s_data in scenarios_data[:max_scenarios]:
            if not isinstance(s_data, dict):
                continue
            s_type = s_data.get("type", "manual")
            if scenario_types and s_type not in scenario_types:
                continue

            scenario = NexusScenario(
                project_id=project_id,
                title=str(s_data.get("title", "Adsız Senaryo"))[:500],
                type=s_type if s_type in ("manual", "service", "automation") else "manual",
                feature_area=str(s_data.get("feature_area", ""))[:200] or None,
                priority=s_data.get("priority", "medium"),
                status="draft",
                gherkin=s_data.get("gherkin"),
                notes=s_data.get("notes"),
                llm_model=project.llm_model,
                llm_prompt_tokens=prompt_tokens,
                llm_completion_tokens=completion_tokens,
            )
            db.add(scenario)
            db.flush()

            # Test case'leri kaydet
            for i, c_data in enumerate(s_data.get("cases", [])[:10]):
                if not isinstance(c_data, dict):
                    continue
                case = NexusCase(
                    scenario_id=scenario.id,
                    name=str(c_data.get("name", f"Test Case {i+1}"))[:500],
                    preconditions=c_data.get("preconditions"),
                    steps=c_data.get("steps"),
                    expected_result=c_data.get("expected_result"),
                    test_data=c_data.get("test_data"),
                    order=i,
                )
                db.add(case)

            saved += 1

        db.commit()
        _log.info("GenerateJob tamamlandı: proje=%s, %d senaryo kaydedildi", project_id, saved)

    except Exception as exc:
        _log.exception("GenerateJob başarısız: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()
