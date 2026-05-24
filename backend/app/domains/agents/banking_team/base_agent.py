"""BaseAgent — tüm banking ekibi ajanlarinin ortak tabani."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.domains.agents.banking_team.circuit_breaker import ollama_breaker
from app.domains.agents.banking_team.errors import (
    LLMConnectionError, LLMResponseError, JSONParseError, ContextBuildError,
)

logger = logging.getLogger(__name__)

# ── LLM Retry Ayarlari ───────────────────────────────────────────────────────
MAX_LLM_RETRIES = 2       # model başına retry sayısı (fallback zinciri sayesinde 3→2)
RETRY_BACKOFF_BASE = 1.5  # saniye — exponential: 1.5, 2.25

# ── Proje Bağlam Cache (tüm ajanlar paylaşır, session boyunca geçerli) ──────
_project_context_cache: dict[str, Any] | None = None
_project_context_ts: float = 0.0
_PROJECT_CTX_TTL = 600  # 10 dakika — sonra yeniden oluştur

# ── Model Context Window Limitleri (karakter bazlı yaklaşık) ─────────────────
# 1 token ≈ 3.5 karakter (Türkçe için) — güvenli sınır olarak %70 hedefliyoruz
_MODEL_CTX_LIMITS: dict[str, int] = {
    # Ollama modelleri — num_ctx default'u modele göre değişir
    # qwen2.5:32b  → 32K context (Ollama num_ctx=32768) → ~112K char, güvenli: ~80K
    "qwen2.5:32b": 80000,
    # qwen2.5:14b  → 8K context → ~28K char, güvenli: ~20K
    "qwen2.5:14b": 20000,
    # mistral:latest → 32K context (Mistral 7B native) → ~112K char, güvenli: ~80K
    "mistral:latest": 80000,
    "mistral:7b": 80000,
    # Diğer Ollama modelleri → num_ctx=4096 default → ~14K char, güvenli: ~10K
    "llama3.1:8b": 10000,
    "qwen2.5-coder:7b": 10000,
    # OpenAI modelleri (128K token → ~448K char, güvenli: ~300K)
    "gpt-4o": 300000,
    "gpt-4o-mini": 300000,
    "gpt-4-turbo": 300000,
    # Anthropic modelleri (200K token → ~700K char, güvenli: ~500K)
    "claude-sonnet-4-20250514": 500000,
    "claude-3-5-sonnet-20241022": 500000,
}
_DEFAULT_CTX_LIMIT = 10000  # Bilinmeyen model → Ollama seviyesi

# ── Cached Anthropic client for BaseAgent ────────────────────────────
import threading as _threading
_anthropic_lock = _threading.Lock()
_anthropic_agent_client = None


def _get_anthropic_agent_client():
    global _anthropic_agent_client
    if _anthropic_agent_client is None:
        with _anthropic_lock:
            if _anthropic_agent_client is None:
                from app.domains.ai.service import _get_anthropic_client

                _anthropic_agent_client = _get_anthropic_client()
    return _anthropic_agent_client


def _allow_provider_fallback() -> bool:
    return bool(getattr(settings, "allow_provider_fallback", False))


def _resolve_effective_provider() -> str:
    provider = settings.ai_provider
    if provider == "anthropic":
        if settings.anthropic_api_key:
            return "anthropic"
        if _allow_provider_fallback() and settings.openai_api_key:
            logger.warning("BaseAgent provider fallback: anthropic secili ama ANTHROPIC_API_KEY yok; openai kullaniliyor")
            return "openai"
        raise RuntimeError(
            "AI provider 'anthropic' secili ama ANTHROPIC_API_KEY ayarlanmamis. "
            "Fallback icin ALLOW_PROVIDER_FALLBACK=true tanimlayin veya provider/config'i duzeltin."
        )

    if provider == "openai":
        if settings.openai_api_key:
            return "openai"
        if _allow_provider_fallback() and settings.anthropic_api_key:
            logger.warning("BaseAgent provider fallback: openai secili ama OPENAI_API_KEY yok; anthropic kullaniliyor")
            return "anthropic"
        raise RuntimeError(
            "AI provider 'openai' secili ama OPENAI_API_KEY ayarlanmamis. "
            "Fallback icin ALLOW_PROVIDER_FALLBACK=true tanimlayin veya provider/config'i duzeltin."
        )

    if provider == "ollama":
        return "ollama"

    raise RuntimeError(f"Desteklenmeyen AI provider: {provider}")


@dataclass
class AgentResult:
    agent_name: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: int = 0
    tokens_used: int = 0


class BaseAgent(ABC):
    """
    Tüm banking QA ajanlarinin temel sinifi.

    Her ajan:
      - Ollama'ya baglanir (OpenAI-compatible endpoint)
      - Kendi role ve model konfigurasyonunu tasir
      - KnowledgeStore'a ogrendiklerini yazar
      - Hata durumunda sessizce AgentResult(success=False) dondurur
      - LLM cagirilari exponential backoff ile retry edilir
      - Proje bağlamını otomatik olarak system prompt'a enjekte eder
      - Her LLM cagrisi otomatik olarak llm_traces tablosuna kaydedilir
    """

    name: str = "BaseAgent"
    model: str = ""          # Alt siniflar override eder
    # Temperature Rehberi (ajan bazinda):
    #   0.0  — ProjectScanner: Deterministik dosya tarami, yaraticilik gereksiz
    #   0.1  — QualityJudge, RegulationAgent, AutoHealer: Kural tabanlı, tutarli puanlama
    #   0.2  — DataAnalyst, CodeGenerator, AutomationDecision, DiscoveryAgent: Yapisal cikti
    #   0.3  — SelfImproving, DebateOrchestrator: Orta yaraticilik, oğrenme analizi
    #   0.4  — ScenarioGenerator: Yuksek yaraticilik, cesitli senaryo uretimi
    temperature: float = 0.3
    max_tokens: int = 4096
    # Alt sınıflar True yaparak proje bağlamını otomatik enjekte edebilir
    inject_project_context: bool = True

    # Model fallback zinciri — birincil model başarısız olursa sırayla dene.
    # Alt sınıflar kendi fallback listelerini tanımlayabilir.
    model_fallback: list[str] = []

    def __init__(self):
        self._client = None

    # ── LLM Bağlantısı ───────────────────────────────────────────────────────

    def _get_client(self):
        if self._client is None:
            effective_provider = _resolve_effective_provider()
            if effective_provider == "ollama":
                from app.domains.ai.service import _get_ollama_client

                self._client = _get_ollama_client()
            elif effective_provider == "anthropic":
                # Native Anthropic SDK kullan — OpenAI proxy'sine gerek yok
                self._client = "anthropic"  # sentinel, call() icinde handle edilir
            else:
                from app.domains.ai.service import _get_openai_client

                self._client = _get_openai_client()
        return self._client

    def _resolve_model(self) -> str:
        """Config'den model adini coz."""
        if self.model:
            return self.model
        effective_provider = _resolve_effective_provider()
        if effective_provider == "ollama":
            return settings.ollama_model_fast
        if effective_provider == "anthropic":
            return settings.anthropic_model
        return settings.openai_model

    def _get_model_chain(self) -> list[str]:
        """Birincil model + fallback'leri dondur.

        Sira:
          1. _resolve_model() → ajanin birincil modeli
          2. self.model_fallback → ajan bazinda tanimlanmis fallback listesi
          3. Global fallback (Ollama) → en hafif model her zaman son care
        Ayni model zincirde iki kez yer almaz.
        """
        primary = self._resolve_model()
        chain = [primary]

        # Ajanin kendi fallback listesi
        for fb in self.model_fallback:
            if fb not in chain:
                chain.append(fb)

        # Global fallback — en hafif model her zaman son care
        if _resolve_effective_provider() == "ollama":
            for fb in [settings.ollama_model_fast, settings.ollama_model_analyst]:
                if fb not in chain:
                    chain.append(fb)

        return chain

    # ── Proje Bağlam Enjeksiyonu ────────────────────────────────────────────────

    @classmethod
    def get_project_context(cls) -> dict[str, Any]:
        """
        Projenin güncel bağlamını oluştur veya cache'den al.
        Tüm ajanlar paylaşır — aynı pipeline içinde tek sefer hesaplanır.
        """
        global _project_context_cache, _project_context_ts
        now = time.time()
        if _project_context_cache and (now - _project_context_ts) < _PROJECT_CTX_TTL:
            return _project_context_cache

        ctx: dict[str, Any] = {}

        # 1. KnowledgeStore'dan proje hafızası
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            project_id = getattr(self, "_project_id", None)
            if not project_id:
                raise ValueError("project_id gerekli")
            store = KnowledgeStore(project_id=project_id)
            # Son başarılı insight'lar
            insights = store.retrieve(
                "proje yapısı test sonuçları hata kalıpları öğrenimler",
                top_k=8,
                sources=["insight", "error_pattern", "execution"],
                project_id=project_id,
            )
            if insights:
                ctx["knowledge"] = "\n".join([
                    f"[{c.source} | benzerlik:{c.similarity:.2f}] {c.content[:300]}"
                    for c in insights
                ])
        except Exception as exc:
            logger.debug("Proje bağlamı — knowledge store erişilemedi: %s", exc)

        # 2. ProjectScanner sonuçlarını kontrol et (önceki run'dan cache'lenmiş olabilir)
        try:
            from app.domains.agents.banking_team.project_scanner import ProjectScannerAgent
            scanner = ProjectScannerAgent()
            scan_result = scanner.safe_run({})
            if scan_result.success:
                data = scan_result.data
                ctx["db_schema"] = data.get("db_schema", "")[:2000]
                ctx["api_endpoints"] = data.get("api_docs", "")[:2000]
                ctx["existing_features"] = data.get("existing_features", "")[:1500]
                ctx["existing_tests"] = data.get("existing_tests", "")[:1500]
                ctx["recent_changes"] = data.get("recent_changes", "")[:800]
                ctx["description"] = data.get("description", "")
                ctx["regulations"] = data.get("regulations", [])
        except Exception as exc:
            logger.debug("Proje bağlamı — scanner erişilemedi: %s", exc)

        _project_context_cache = ctx
        _project_context_ts = now
        return ctx

    @classmethod
    def reset_project_context(cls) -> None:
        """Pipeline başlangıcında cache'i sıfırla — taze bağlam oluşturulsun."""
        global _project_context_cache, _project_context_ts
        _project_context_cache = None
        _project_context_ts = 0.0

    def _get_context_budget(self) -> int:
        """Bu ajanın modeli için kullanılabilir context window bütçesini hesapla (karakter)."""
        if settings.ai_gateway_required:
            return 80000
        model = self._resolve_model()
        limit = _MODEL_CTX_LIMITS.get(model, _DEFAULT_CTX_LIMIT)
        # Bütçenin %40'ı system prompt + context, %60'ı user prompt + response için ayrılır
        return int(limit * 0.40)

    def _enrich_system_prompt(self, system: str) -> str:
        """
        System prompt'u proje bağlamıyla zenginleştir.
        Her ajan otomatik olarak güncel proje bilgisini alır.
        Context window bütçesine göre otomatik truncation yapar.
        """
        if not self.inject_project_context:
            return system

        ctx = self.get_project_context()
        if not ctx:
            return system

        # Bütçe hesapla — system prompt zaten yer kaplıyor
        budget = self._get_context_budget() - len(system)
        if budget < 500:
            # Yeterli alan yok — context enjekte etme
            logger.debug("%s: Context budget yetersiz (%d), enjeksiyon atlanıyor", self.name, budget)
            return system

        # Öncelik sırasına göre section'ları ekle (en önemli → en az önemli)
        section_defs = [
            ("description",       "## Proje Tanımı",                200),
            ("db_schema",         "## Veritabanı Yapısı",           1200),
            ("api_endpoints",     "## API Endpoint'leri",           1200),
            ("existing_features", "## Mevcut BDD Senaryoları",      1000),
            ("existing_tests",    "## Mevcut E2E Testler",          800),
            ("knowledge",         "## Geçmiş Öğrenimler ve Hatalar", 1500),
            ("recent_changes",    "## Son Kod Değişiklikleri",       500),
        ]

        sections: list[str] = []
        used = 0
        header_footer_cost = 200  # ═══ PROJE BAĞLAMI başlık/bitiş maliyeti

        for key, label, max_len in section_defs:
            value = ctx.get(key, "")
            if not value:
                continue
            # Kalan bütçeye göre truncation
            available = budget - used - header_footer_cost
            if available < 100:
                break  # Bütçe doldu
            trunc = min(max_len, available)
            section_text = f"{label}\n{value[:trunc]}"
            sections.append(section_text)
            used += len(section_text) + 2  # +2 for \n\n separator

        if not sections:
            return system

        context_block = (
            "\n\n# ═══ PROJE BAĞLAMI (Otomatik Enjekte) ═══\n"
            "Aşağıdaki bilgiler GERÇEK proje verilerinden otomatik çıkarılmıştır.\n"
            "Kararlarını ve çıktılarını bu bağlama göre şekillendir.\n\n"
            + "\n\n".join(sections)
            + "\n# ═══ PROJE BAĞLAMI SONU ═══"
        )

        return system + context_block

    def _call_via_required_gateway(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool,
        extra_messages: list[dict] | None = None,
    ) -> str:
        from app.domains.ai.gateway_client import gateway_complete

        task_type = self._gateway_task_type(json_mode=json_mode)
        if extra_messages:
            rendered_messages = "\n\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')}"
                for m in extra_messages
            )
            user = f"{rendered_messages}\n\nuser: {user}"

        return gateway_complete(
            task_type=task_type,
            system_message=system,
            user_message=user,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            project_id=getattr(self, "_project_id", None),
            json_mode=json_mode,
            tenant_id=getattr(self, "_tenant_id", None),
        )

    def _gateway_task_type(self, *, json_mode: bool) -> str:
        raw = f"{getattr(self, '_phase', '')} {self.name}".lower()
        if "playwright" in raw or "code" in raw or "coder" in raw:
            return "generate_playwright"
        if "gherkin" in raw:
            return "generate_gherkin"
        if "scenario" in raw or "test case" in raw:
            return "generate_test_cases"
        if "debug" in raw or "heal" in raw or "repair" in raw:
            return "debug_test"
        if "analyst" in raw or "analysis" in raw or "scan" in raw:
            return "analyze_document"
        if json_mode:
            return "analyze_document"
        return "chat"

    # ── Temel LLM Cagrisi (Retry + Fallback + Trace Destekli) ─────────────────

    # Ollama num_ctx — model bazli context window (call icinde kullanilir)
    _OLLAMA_CTX: dict[str, int] = {
        "qwen2.5:32b": 16384,
        "qwen2.5:14b": 8192,
        "mistral:latest": 16384,
        "mistral:7b": 16384,
        "qwen2.5-coder:7b": 8192,
        "llama3.1:8b": 4096,
    }

    def call(
        self,
        system: str,
        user: str,
        json_mode: bool = False,
        extra_messages: list[dict] | None = None,
    ) -> str:
        """LLM'e istek gönder, ham yaniti dondur. Trace kaydeder.

        Fallback zinciri + exponential backoff ile retry:
          Model 1: retry 1 → retry 2 → FAIL → fallback
          Model 2: retry 1 → retry 2 → FAIL → fallback
          ...
        Tüm modeller başarısız olursa son hatayi raise eder.
        Her cagri (başarılı/başarısız) llm_traces tablosuna kaydedilir.
        """
        self._last_trace_id = None

        # Proje bağlamını otomatik enjekte et
        enriched_system = self._enrich_system_prompt(system)

        if settings.ai_gateway_required:
            return self._call_via_required_gateway(
                enriched_system,
                user,
                json_mode=json_mode,
                extra_messages=extra_messages,
            )

        effective_provider = _resolve_effective_provider()
        client = self._get_client()
        model_chain = self._get_model_chain()

        messages = [{"role": "system", "content": enriched_system}]
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({"role": "user", "content": user})

        # JSON mode için user mesajina ek talimat (Ollama'da)
        if json_mode and settings.ai_provider == "ollama":
            messages[-1]["content"] += "\n\nYALNIZCA gecerli JSON dondur. Baska aciklama yazma."

        last_error: Exception | None = None
        t0 = time.time()

        for model_idx, current_model in enumerate(model_chain):
            # ── Circuit breaker kontrolu (Ollama down ise atla) ──────────
            if effective_provider == "ollama" and not ollama_breaker.can_execute():
                logger.warning(
                    "%s circuit OPEN — %s atlaniyor, fallback deneniyor",
                    self.name, current_model,
                )
                continue

            # ── kwargs'i her model için yeniden hazırla ──────────────────
            kwargs: dict[str, Any] = {
                "model": current_model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            # Ollama için num_ctx — model bazli context window
            if settings.ai_provider == "ollama":
                num_ctx = self._OLLAMA_CTX.get(current_model, 4096)
                kwargs["extra_body"] = {"num_ctx": num_ctx}

            # Ollama json_mode destegi sinirli — sadece OpenAI'da aktif et
            if json_mode and effective_provider != "ollama":
                kwargs["response_format"] = {"type": "json_object"}

            if json_mode and effective_provider == "ollama":
                if "extra_body" not in kwargs:
                    kwargs["extra_body"] = {}
                kwargs["extra_body"]["format"] = "json"

            # ── Retry dongusu (bu model için) ────────────────────────────
            for attempt in range(1, MAX_LLM_RETRIES + 1):
                try:
                    if effective_provider == "anthropic":
                        anth_client = _get_anthropic_agent_client()
                        anth_messages = []
                        if extra_messages:
                            anth_messages.extend(extra_messages)
                        anth_messages.append({"role": "user", "content": user})
                        # JSON mode hint for Anthropic
                        if json_mode:
                            anth_messages[-1]["content"] += "\n\nYALNIZCA gecerli JSON dondur."
                        resp = anth_client.messages.create(
                            model=current_model,
                            max_tokens=self.max_tokens,
                            system=enriched_system,
                            messages=anth_messages,
                            temperature=self.temperature,
                        )
                        result = resp.content[0].text
                    else:
                        resp = client.chat.completions.create(**kwargs)
                        result = resp.choices[0].message.content or ""
                    latency_ms = int((time.time() - t0) * 1000)

                    # ── Trace kaydi (fire-and-forget) ──
                    try:
                        from app.domains.ai.llm_trace import log_llm_call
                        self._last_trace_id = log_llm_call(
                            agent_name=self.name,
                            model=current_model,
                            system_prompt=enriched_system,
                            user_prompt=user,
                            response=result,
                            latency_ms=latency_ms,
                            success=True,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens,
                            run_id=getattr(self, "_run_id", None),
                            phase=getattr(self, "_phase", None),
                            project_id=getattr(self, "_project_id", None),
                            user_id=getattr(self, "_user_id", None),
                            provider=effective_provider,
                            task_type=getattr(self, "_phase", None) or self.name,
                            fallback_used=model_idx > 0,
                            metadata={
                                "model_chain": model_chain,
                                "model_index": model_idx,
                            },
                        )
                    except Exception:
                        pass  # Trace asla pipeline'i kirmaz

                    if effective_provider == "ollama":
                        ollama_breaker.record_success()
                    return result
                except (ConnectionError, TimeoutError, OSError) as e:
                    last_error = e
                    if effective_provider == "ollama":
                        ollama_breaker.record_failure()
                    if attempt < MAX_LLM_RETRIES:
                        wait = RETRY_BACKOFF_BASE ** attempt
                        logger.warning(
                            "%s LLM connection retry %d/%d model=%s (%.1fs): %s",
                            self.name, attempt, MAX_LLM_RETRIES,
                            current_model, wait, str(e)[:100],
                        )
                        time.sleep(wait)
                except Exception as e:
                    last_error = e
                    if attempt < MAX_LLM_RETRIES:
                        wait = RETRY_BACKOFF_BASE ** attempt
                        logger.warning(
                            "%s LLM retry %d/%d model=%s (%.1fs bekleniyor): %s",
                            self.name, attempt, MAX_LLM_RETRIES,
                            current_model, wait, str(e)[:100],
                        )
                        time.sleep(wait)

            # Bu model tamamen başarısız — fallback'e gec
            next_model_idx = model_idx + 1
            if next_model_idx < len(model_chain):
                next_model = model_chain[next_model_idx]
                logger.warning(
                    "%s falling back from %s to %s",
                    self.name, current_model, next_model,
                )
            else:
                logger.error(
                    "%s tüm modeller başarısız (%s): %s",
                    self.name,
                    " → ".join(model_chain),
                    last_error,
                )

        # Başarısız cagriyi da trace'e kaydet
        latency_ms = int((time.time() - t0) * 1000)
        try:
            from app.domains.ai.llm_trace import log_llm_call
            self._last_trace_id = log_llm_call(
                agent_name=self.name,
                model=model_chain[-1] if model_chain else "unknown",
                system_prompt=enriched_system,
                user_prompt=user,
                response="",
                latency_ms=latency_ms,
                success=False,
                error_message=str(last_error)[:2000] if last_error else "",
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                run_id=getattr(self, "_run_id", None),
                phase=getattr(self, "_phase", None),
                project_id=getattr(self, "_project_id", None),
                user_id=getattr(self, "_user_id", None),
                provider=effective_provider,
                task_type=getattr(self, "_phase", None) or self.name,
                fallback_used=len(model_chain) > 1,
                metadata={
                    "model_chain": model_chain,
                    "failed_model_count": len(model_chain),
                },
            )
        except Exception:
            pass

        raise last_error  # type: ignore[misc]

    def call_json(self, system: str, user: str, extra_messages: list[dict] | None = None) -> dict:
        """JSON cikti bekleyen LLM cagrisi — gelismis JSON parse recovery + trace."""
        raw = self.call(system, user, json_mode=True, extra_messages=extra_messages)
        raw = raw.strip()

        # Markdown kod blogu varsa temizle
        if raw.startswith("```"):
            lines = raw.split("\n")
            # ```json veya ``` satir kontrolu
            start_idx = 1
            end_idx = len(lines)
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip().startswith("```"):
                    end_idx = i
                    break
            raw = "\n".join(lines[start_idx:end_idx]).strip()

        # 1. Dogrudan parse
        try:
            result = json.loads(raw)
            self._trace_json_parse(True)
            return result
        except json.JSONDecodeError:
            pass

        # 2. Gelismis JSON extraction — nested braces'leri dogru esle
        json_obj = self._extract_json_object(raw)
        if json_obj is not None:
            self._trace_json_parse(True)
            return json_obj

        # 3. JSON array olasiligi ([ ... ])
        json_arr = self._extract_json_array(raw)
        if json_arr is not None:
            self._trace_json_parse(True)
            return {"items": json_arr}

        logger.warning("%s JSON parse hatasi: %s...", self.name, raw[:200])
        self._trace_json_parse(False)
        return {"raw": raw, "parse_error": True}

    def _trace_json_parse(self, success: bool) -> None:
        """Son trace kaydinin json_parse_ok alanini guncelle (fire-and-forget)."""
        try:
            from app.domains.ai.llm_trace import update_json_parse_status
            update_json_parse_status(getattr(self, "_last_trace_id", None), success)
        except Exception:
            pass  # Trace asla pipeline'i kirmaz

    @staticmethod
    def _extract_json_object(text: str) -> dict | None:
        """Metinden JSON nesnesini cikart — nested braces destekli."""
        # Tüm { pozisyonlarini bul, en distandakini dene
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        return None
        return None

    @staticmethod
    def _extract_json_array(text: str) -> list | None:
        """Metinden JSON array'i cikart."""
        start = text.find("[")
        if start == -1:
            return None
        end = text.rfind("]") + 1
        if end <= start:
            return None
        try:
            result = json.loads(text[start:end])
            return result if isinstance(result, list) else None
        except json.JSONDecodeError:
            return None

    # ── KnowledgeStore Entegrasyonu ───────────────────────────────────────────

    def learn(self, text: str, metadata: dict | None = None) -> None:
        """Ogrenileni KnowledgeStore'a kaydet (sessiz hata)."""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            metadata = dict(metadata or {})
            project_id = metadata.get("project_id") or getattr(self, "_project_id", None)
            store = KnowledgeStore(project_id=project_id)
            store.ingest(
                text=text,
                source="insight",
                metadata={"agent": self.name, **metadata},
                project_id=project_id,
            )
        except Exception as exc:
            logger.debug("%s learn hatasi: %s", self.name, exc)

    # ── Async LLM Cagrisi ─────────────────────────────────────────────────────

    async def async_call(
        self,
        system: str,
        user: str,
        json_mode: bool = False,
        extra_messages: list[dict] | None = None,
    ) -> str:
        """Async LLM cagrisi — FastAPI endpoint'lerinden dogrudan await edilebilir."""
        import asyncio

        enriched_system = self._enrich_system_prompt(system)
        self._last_trace_id = None

        if settings.ai_gateway_required:
            return await asyncio.to_thread(
                self._call_via_required_gateway,
                enriched_system,
                user,
                json_mode=json_mode,
                extra_messages=extra_messages,
            )

        model_chain = self._get_model_chain()
        effective_provider = _resolve_effective_provider()

        messages = [{"role": "system", "content": enriched_system}]
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({"role": "user", "content": user})

        if json_mode and effective_provider == "ollama":
            messages[-1]["content"] += "\n\nYALNIZCA gecerli JSON dondur. Baska aciklama yazma."

        last_error = None
        t0 = time.time()

        for model_idx, current_model in enumerate(model_chain):
            # Circuit breaker check
            if effective_provider == "ollama" and not ollama_breaker.can_execute():
                continue

            for attempt in range(1, MAX_LLM_RETRIES + 1):
                try:
                    if effective_provider == "anthropic":
                        # Use async Anthropic client
                        from app.domains.ai.service import _get_async_anthropic_client
                        anth_client = await _get_async_anthropic_client()
                        anth_messages = []
                        if extra_messages:
                            anth_messages.extend(extra_messages)
                        anth_messages.append({"role": "user", "content": user})
                        if json_mode:
                            anth_messages[-1]["content"] += "\n\nYALNIZCA gecerli JSON dondur."
                        resp = await anth_client.messages.create(
                            model=current_model,
                            max_tokens=self.max_tokens,
                            system=enriched_system,
                            messages=anth_messages,
                            temperature=self.temperature,
                        )
                        result = resp.content[0].text
                    elif effective_provider == "ollama":
                        from app.domains.ai.service import _get_async_ollama_client
                        client = await _get_async_ollama_client()
                        kwargs: dict[str, Any] = {
                            "model": current_model,
                            "messages": messages,
                            "temperature": self.temperature,
                            "max_tokens": self.max_tokens,
                        }
                        num_ctx = self._OLLAMA_CTX.get(current_model, 4096)
                        kwargs["extra_body"] = {"num_ctx": num_ctx}
                        if json_mode:
                            kwargs["extra_body"]["format"] = "json"
                        resp = await client.chat.completions.create(**kwargs)
                        result = resp.choices[0].message.content or ""
                    else:
                        from app.domains.ai.service import _get_async_openai_client
                        client = await _get_async_openai_client()
                        kwargs = {
                            "model": current_model,
                            "messages": messages,
                            "temperature": self.temperature,
                            "max_tokens": self.max_tokens,
                        }
                        if json_mode:
                            kwargs["response_format"] = {"type": "json_object"}
                        resp = await client.chat.completions.create(**kwargs)
                        result = resp.choices[0].message.content or ""

                    # Trace (fire-and-forget)
                    latency_ms = int((time.time() - t0) * 1000)
                    try:
                        from app.domains.ai.llm_trace import log_llm_call
                        self._last_trace_id = log_llm_call(
                            agent_name=self.name, model=current_model,
                            system_prompt=enriched_system, user_prompt=user,
                            response=result, latency_ms=latency_ms, success=True,
                            temperature=self.temperature, max_tokens=self.max_tokens,
                            run_id=getattr(self, "_run_id", None),
                            phase=getattr(self, "_phase", None),
                            project_id=getattr(self, "_project_id", None),
                            user_id=getattr(self, "_user_id", None),
                            provider=effective_provider,
                            task_type=getattr(self, "_phase", None) or self.name,
                            fallback_used=model_idx > 0,
                            metadata={
                                "model_chain": model_chain,
                                "model_index": model_idx,
                            },
                        )
                    except Exception:
                        pass

                    if effective_provider == "ollama":
                        ollama_breaker.record_success()
                    return result

                except Exception as e:
                    last_error = e
                    if effective_provider == "ollama":
                        ollama_breaker.record_failure()
                    if attempt < MAX_LLM_RETRIES:
                        wait = RETRY_BACKOFF_BASE ** attempt
                        await asyncio.sleep(wait)

            # Fallback to next model
            next_model_idx = model_idx + 1
            if next_model_idx < len(model_chain):
                logger.warning(
                    "%s async falling back from %s to %s",
                    self.name, current_model, model_chain[next_model_idx],
                )

        # All models failed — trace and raise
        latency_ms = int((time.time() - t0) * 1000)
        try:
            from app.domains.ai.llm_trace import log_llm_call
            self._last_trace_id = log_llm_call(
                agent_name=self.name, model=model_chain[-1] if model_chain else "unknown",
                system_prompt=enriched_system, user_prompt=user,
                response="", latency_ms=latency_ms, success=False,
                error_message=str(last_error)[:2000] if last_error else "",
                temperature=self.temperature, max_tokens=self.max_tokens,
                project_id=getattr(self, "_project_id", None),
                user_id=getattr(self, "_user_id", None),
                provider=effective_provider,
                task_type=getattr(self, "_phase", None) or self.name,
                fallback_used=len(model_chain) > 1,
                metadata={
                    "model_chain": model_chain,
                    "failed_model_count": len(model_chain),
                },
            )
        except Exception:
            pass
        raise last_error  # type: ignore[misc]

    async def async_call_json(self, system: str, user: str, extra_messages: list[dict] | None = None) -> dict:
        """Async JSON cikti bekleyen LLM cagrisi."""
        raw = await self.async_call(system, user, json_mode=True, extra_messages=extra_messages)
        raw = raw.strip()
        # Same JSON parse logic as sync call_json
        if raw.startswith("```"):
            lines = raw.split("\n")
            start_idx = 1
            end_idx = len(lines)
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip().startswith("```"):
                    end_idx = i
                    break
            raw = "\n".join(lines[start_idx:end_idx]).strip()

        try:
            result = json.loads(raw)
            self._trace_json_parse(True)
            return result
        except json.JSONDecodeError:
            pass
        json_obj = self._extract_json_object(raw)
        if json_obj is not None:
            self._trace_json_parse(True)
            return json_obj
        json_arr = self._extract_json_array(raw)
        if json_arr is not None:
            self._trace_json_parse(True)
            return {"items": json_arr}
        self._trace_json_parse(False)
        return {"raw": raw, "parse_error": True}

    async def async_run(self, context: dict) -> AgentResult:
        """Async alt siniflar override eder."""
        # Default: sync run'i thread pool'da çalıştır
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run, context)

    async def async_safe_run(self, context: dict) -> AgentResult:
        """Async hata yakalanmis calistirma."""
        t0 = time.time()
        try:
            result = await self.async_run(context)
            result.duration_ms = int((time.time() - t0) * 1000)
            return result
        except Exception as exc:
            logger.error("%s async hatasi: %s", self.name, exc)
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(exc),
                duration_ms=int((time.time() - t0) * 1000),
            )

    # ── Calistirma ────────────────────────────────────────────────────────────

    @abstractmethod
    def run(self, context: dict) -> AgentResult:
        """Alt siniflar override eder."""

    def safe_run(self, context: dict) -> AgentResult:
        """Hata yakalanmis calistirma — pipeline'i asla kirmaz."""
        t0 = time.time()
        try:
            self._project_id = context.get("project_id") or getattr(self, "_project_id", None)
            self._user_id = context.get("user_id") or getattr(self, "_user_id", None)
            result = self.run(context)
            result.duration_ms = int((time.time() - t0) * 1000)
            return result
        except Exception as exc:
            logger.error("%s hatasi: %s", self.name, exc)
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(exc),
                duration_ms=int((time.time() - t0) * 1000),
            )
