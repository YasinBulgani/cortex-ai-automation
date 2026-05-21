"""
ServiceTestAgent — AI-Powered API/Service Test Intelligence
============================================================

4 calisma modu:
  1. SPEC_ANALYSIS       → OpenAPI spec analizi + endpoint risk degerlendirmesi
  2. TEST_GENERATION     → AI ile test case uretimi (9 tip: positive/negative/boundary/...)
  3. SECURITY_AUDIT      → OWASP API Top 10 + BDDK/KVKK/PCI-DSS guvenlik testleri
  4. CHAIN_BUILDER       → API call chaining + veri bagimliligi cozumleme

Entegrasyonlar:
  - FewShotBank:      Her mod icin bankacilik domain few-shot ornekleri
  - SmartModelRouter: Gorev tipine ve endpoint ozelliklerine gore optimal model secimi

Kullanim:
  agent = ServiceTestAgent()
  result = agent.safe_run({
      "mode": "test_generation",
      "endpoints": [...],
      "regulations": ["BDDK", "KVKK"],
  })
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, List, Optional

from app.config import settings
from app.domains.agents.banking_team.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


# ── System Prompt'lar ─────────────────────────────────────────────────

_SPEC_ANALYSIS_PROMPT = """Sen kidemli bir API Guvenligi ve Mimari Uzmanisin. Turkce yanit ver.
Verilen OpenAPI/Swagger endpoint listesini derinlemesine analiz et.

Her endpoint icin:
1. Risk seviyesi belirle (critical/high/medium/low)
2. Hassas veri (PII) icerip icermedigini tespit et
3. Finansal islem olup olmadigini belirle
4. Uyumluluk gereksinimlerini listele (BDDK, KVKK, PCI-DSS, MASAK)
5. Endpoint'ler arasi bagimliliklari cikar (hangi endpoint hangi veriye ihtiyac duyar)
6. Potansiyel guvenlik zafiyetlerini isle

BANKACILIK DOMAIN BILGISI:
- Para transferi endpoint'leri HER ZAMAN critical seviyedir
- IBAN, TCKN, kart numarasi iceren alanlar KVKK + PCI-DSS kapsamindadir
- Auth/login endpoint'leri critical seviyedir — brute-force korumasi kontrol edilmeli
- GET endpoint'leri bile hassas veri donduruyorsa "high" risk'tir
- Batch/toplu islem endpoint'leri rate-limit ve idempotency kontrolu gerektirir

JSON formatinda yanit ver:
{
  "risk_summary": {"critical": N, "high": N, "medium": N, "low": N},
  "high_risk_endpoints": [{"method": "...", "path": "...", "risk": "...", "reason": "..."}],
  "pii_endpoints": [{"method": "...", "path": "...", "pii_fields": ["..."]}],
  "financial_endpoints": [{"method": "...", "path": "...", "type": "..."}],
  "compliance_requirements": [{"regulation": "BDDK/KVKK/...", "endpoints": [...], "requirement": "..."}],
  "dependency_graph": [{"from": "POST /auth/login", "to": "GET /accounts", "data": "auth_token"}],
  "security_concerns": [{"endpoint": "...", "concern": "...", "severity": "..."}]
}"""

_TEST_GENERATION_PROMPT = """Sen bankacilik sektorunde 15+ yil deneyime sahip kidemli bir API QA Muhendisisin. Turkce yanit ver.

Verilen endpoint listesi icin KAPSAMLI test senaryolari uret. Her endpoint icin en az 5-8 test case olustur.

TEST KATEGORILERI:
1. POSITIVE — Gecerli parametrelerle basarili cagri (happy path)
2. NEGATIVE — Zorunlu alan eksik, gecersiz tip, bos deger, null
3. BOUNDARY — Min/max sinir degerleri, zero, overflow, underflow
4. SECURITY — Yetkisiz erisim, BOLA, injection, auth bypass
5. COMPLIANCE — BDDK tutar limitleri, KVKK veri maskeleme, PCI-DSS kart verisi
6. PERFORMANCE — Response time SLA (bankacilik: max 3sn), throughput
7. EDGE_CASE — Race condition, idempotency, encoding (UTF-8/Turkish chars), concurrent
8. REGRESSION — Onceki hatalardan ogrenilenler (varsa)
9. CONTRACT — Response schema uygunlugu

BANKACILIK OZEL TEST PATIRNLERI:
- Para transferi: Negatif tutar, sinir degerleri (0.01, 50000, 999999.99), kendi hesabina transfer
- Kimlik dogrulama: Brute-force (5 yanlis deneme sonrasi kilit), token suresi, refresh rotation
- IBAN dogrulama: Gecersiz format, uzunluk, checksum, farkli ulke IBAN'i
- Idempotency: Ayni islem tekrarinda duplicate olmamali (Idempotency-Key header)
- Concurrent: Ayni anda 2 transfer → toplam bakiye tutarli olmali (double-spending onleme)
- KVKK: Response'ta TCKN/IBAN maskelenmis olmali (TR**...**1326 formati)
- Rate limit: Dakikada N istek siniri asildinda 429 donmeli

JSON formatinda yanit ver:
{
  "test_cases": [
    {
      "id": "API-XXX-001",
      "title": "Aciklayici test basligi",
      "description": "Detayli aciklama",
      "test_type": "positive|negative|boundary|security|compliance|performance|edge_case|regression|contract",
      "priority": "P0|P1|P2|P3",
      "endpoint": {"method": "POST", "path": "/api/v1/transfers"},
      "owasp_category": "API1|API2|...|null",
      "regulation": "BDDK|KVKK|PCI-DSS|MASAK|null",
      "request": {
        "method": "POST",
        "path": "/api/v1/transfers",
        "headers": {"Authorization": "Bearer {{auth_token}}"},
        "params": {},
        "body": {"from_account": "TR...", "amount": 100.50}
      },
      "assertions": [
        {"type": "status_code", "expected": 201},
        {"type": "json_path", "path": "$.transfer_id", "operator": "exists"},
        {"type": "response_time", "expected": 3000}
      ],
      "setup_chain": [
        {"step": "Login", "endpoint": "POST /auth/login", "extract": {"auth_token": "$.access_token"}}
      ],
      "ai_reasoning": "Neden bu test onemli"
    }
  ]
}"""

_SECURITY_AUDIT_PROMPT = """Sen OWASP API Security Top 10 ve bankacilik regülasyonlari konusunda uzman bir Siber Güvenlik Denetcisisin. Turkce yanit ver.

Verilen API endpoint'leri icin OWASP API Security Top 10 (2023) + bankacilik guvenligi testleri uret.

OWASP API TOP 10 (2023):
- API1:2023 Broken Object Level Authorization (BOLA) — Baska kullanicinin verisine erisim
- API2:2023 Broken Authentication — Zayif kimlik dogrulama, token calmasi
- API3:2023 Broken Object Property Level Authorization — Yetkilendirilmemis alan degisikligi
- API4:2023 Unrestricted Resource Consumption — DDoS, rate limit eksikligi
- API5:2023 Broken Function Level Authorization — Admin fonksiyonlarina normal kullanici erisimi
- API6:2023 Unrestricted Access to Sensitive Business Flows — Otomatize edilebilen is akislari
- API7:2023 Server Side Request Forgery (SSRF) — Sunucu uzerinden dahili ag erisimi
- API8:2023 Security Misconfiguration — CORS, verbose hata mesajlari, debug modu
- API9:2023 Improper Inventory Management — Eski/belgelenmemis API versiyonlari
- API10:2023 Unsafe Consumption of APIs — Ucuncu parti API entegrasyonlari

BANKACILIK EKSTRA KONTROLLER:
- BDDK: Islem limitleri, cift kontrol mekanizmasi, loglanabilirlik
- KVKK: Kisisel veri minimizasyonu, maskeleme, erisim kaydi
- PCI-DSS: Kart verisi depolama/iletim, tokenizasyon
- MASAK: Suphe li islem tespiti, kumulatif limit kontrolu
- SOX: Denetim izi, degisiklik yonetimi

Her guvenlik testi icin:
- Tam exploit senaryosu (nasil saldiri yapilir)
- Beklenen savunma (API ne yapmali)
- CWE referansi (varsa)
- Test request detayi

JSON formatinda yanit ver:
{
  "security_tests": [
    {
      "id": "SEC-XXX-001",
      "title": "BOLA — Baska kullanicinin hesap detayina erisim",
      "owasp": "API1",
      "cwe": "CWE-639",
      "severity": "critical|high|medium|low",
      "endpoint": {"method": "GET", "path": "/api/v1/accounts/{id}"},
      "attack_scenario": "Kullanici A, Kullanici B'nin account_id'sini kullanarak...",
      "expected_defense": "403 Forbidden + audit log kaydi",
      "regulation": "BDDK|KVKK|null",
      "request": {
        "method": "GET",
        "path": "/api/v1/accounts/{{other_user_account_id}}",
        "headers": {"Authorization": "Bearer {{user_a_token}}"}
      },
      "assertions": [
        {"type": "status_code", "operator": "one_of", "expected": [403, 404]},
        {"type": "json_path", "path": "$.account_number", "operator": "not_exists"}
      ]
    }
  ],
  "risk_matrix": {
    "API1": {"tested": true, "findings": N},
    "API2": {"tested": true, "findings": N}
  }
}"""

_CHAIN_BUILDER_PROMPT = """Sen API entegrasyon ve test otomasyon uzmanisin. Turkce yanit ver.

Verilen endpoint listesini analiz ederek anlamli API call chain'leri (is akislari) olustur.

BANKACILIK IS AKISLARI:
1. Login → Hesap Listesi → Hesap Detay → Transfer → Bakiye Dogrulama
2. Login → Kredi Basvurusu → Belge Yukleme → Basvuru Durumu
3. Login → Kart Listesi → Kart Detay → Ekstre → Taksit
4. OTP Istegi → OTP Dogrulama → Hassas Islem
5. Login → Beneficiary Ekleme → EFT/Havale → Dekont

Her chain icin:
- Adimlar arasi veri eslestirmesi (JSON path → degisken)
- Hata durumunda davranis
- Timeout ve retry stratejisi
- Pre/post condition'lar

JSON formatinda yanit ver:
{
  "chains": [
    {
      "name": "Para Transferi Akisi",
      "description": "Login'den transfer dogrulamaya tam akis",
      "steps": [
        {
          "order": 1,
          "label": "Login",
          "endpoint": {"method": "POST", "path": "/auth/login"},
          "body": {"email": "{{test_email}}", "password": "{{test_password}}"},
          "extract": [
            {"name": "auth_token", "json_path": "$.access_token"},
            {"name": "user_id", "json_path": "$.user.id"}
          ],
          "assertions": [{"type": "status_code", "expected": 200}]
        },
        {
          "order": 2,
          "label": "Hesap Listesi",
          "endpoint": {"method": "GET", "path": "/accounts"},
          "headers": {"Authorization": "Bearer {{auth_token}}"},
          "extract": [
            {"name": "from_account", "json_path": "$.accounts[0].iban"},
            {"name": "balance_before", "json_path": "$.accounts[0].balance"}
          ]
        }
      ],
      "post_conditions": ["Bakiye tutarlilik kontrolu", "Transaction log kaydi"]
    }
  ]
}"""


# ── Agent Sinifi ──────────────────────────────────────────────────────

class ServiceTestAgent(BaseAgent):
    """
    AI-Powered API/Service Test Intelligence Agent.

    Bankacilik API'leri icin:
    - Spec analizi (risk, PII, compliance)
    - Test case uretimi (9 kategori)
    - Guvenlik denetimi (OWASP Top 10)
    - Chain/flow olusturma
    """

    name = "ServiceTestAgent"
    model = ""  # Dinamik — mode'a gore degisir
    temperature = 0.2  # Yapisal cikti — dusuk yaraticilik
    max_tokens = 8192  # Uzun test listeleri icin
    inject_project_context = True

    model_fallback = []  # type: ignore

    # Mode -> System Prompt mapping
    _mode_prompts = {
        "spec_analysis": _SPEC_ANALYSIS_PROMPT,
        "test_generation": _TEST_GENERATION_PROMPT,
        "security_audit": _SECURITY_AUDIT_PROMPT,
        "chain_builder": _CHAIN_BUILDER_PROMPT,
    }

    def _resolve_model(self) -> str:
        """Mode'a gore optimal model sec."""
        # Analyst-seviye model — buyuk context, iyi JSON uretimi
        if settings.ai_provider == "ollama":
            return settings.ollama_model_analyst  # qwen2.5:32b
        return settings.openai_model or "gpt-4o"

    @staticmethod
    def _extract_endpoint_keywords(endpoints: list) -> List[str]:
        """Endpoint listesinden few-shot eslestirme icin anahtar kelimeler cikar."""
        keywords = set()  # type: set
        _KW_PATTERNS = [
            (re.compile(r"transfer|havale|eft", re.I), "transfer"),
            (re.compile(r"auth|login|token|session", re.I), "auth"),
            (re.compile(r"account|hesap|balance|bakiye", re.I), "account"),
            (re.compile(r"payment|odeme", re.I), "payment"),
            (re.compile(r"card|kart", re.I), "card"),
            (re.compile(r"credit|kredi", re.I), "credit"),
        ]
        for ep in endpoints:
            path = (ep.get("path") or "").lower()
            for pattern, keyword in _KW_PATTERNS:
                if pattern.search(path):
                    keywords.add(keyword)
        return list(keywords)

    def _build_context(self, ctx: dict) -> str:
        """Calisma moduna gore LLM'e gonderilecek context'i olustur.

        Few-shot orneklerini otomatik olarak ekler — LLM'e beklenen
        kalite seviyesini gosteren referans ornekler.
        """
        mode = ctx.get("mode", "test_generation")
        parts = []  # type: List[str]

        # Endpoint listesi
        endpoints = ctx.get("endpoints", [])
        if endpoints:
            ep_text = json.dumps(endpoints[:50], indent=2, ensure_ascii=False)
            parts.append(f"## API ENDPOINT'LERI ({len(endpoints)} adet)\n{ep_text}")

        # Spec metadata
        spec_meta = ctx.get("spec_metadata")
        if spec_meta:
            parts.append(f"## SPEC BILGISI\n{json.dumps(spec_meta, indent=2, ensure_ascii=False)}")

        # Regulations
        regulations = ctx.get("regulations", ["BDDK", "KVKK"])
        parts.append(f"## UYUMLULUK GEREKSINIMLERI\nAktif regulasyonlar: {', '.join(regulations)}")

        # Previous learnings
        learnings = ctx.get("learnings", "")
        if learnings:
            parts.append(f"## ONCEKI OGRENIMLER\n{learnings}")

        # Additional context
        extra = ctx.get("additional_context", "")
        if extra:
            parts.append(f"## EK BAGLAM\n{extra}")

        # Mode-specific
        if mode == "test_generation":
            test_types = ctx.get("test_types", [
                "positive", "negative", "boundary", "security",
                "compliance", "performance", "edge_case",
            ])
            parts.append(f"## ISTENILEN TEST TIPLERI\n{', '.join(test_types)}")

            max_per_endpoint = ctx.get("max_tests_per_endpoint", 8)
            parts.append(f"Her endpoint icin en fazla {max_per_endpoint} test uret.")

        elif mode == "security_audit":
            owasp_focus = ctx.get("owasp_focus", [])
            if owasp_focus:
                parts.append(f"## ODAKLANILACAK OWASP KATEGORILERI\n{', '.join(owasp_focus)}")

        elif mode == "chain_builder":
            flow_hints = ctx.get("flow_hints", [])
            if flow_hints:
                parts.append(f"## ISTENILEN IS AKISLARI\n{json.dumps(flow_hints, indent=2, ensure_ascii=False)}")

        # ── Few-Shot Ornekleri (kalite referansi) ───────────────────────
        try:
            from app.domains.ai.few_shot_bank import get_few_shot_examples
            endpoint_keywords = self._extract_endpoint_keywords(endpoints)
            few_shot_text = get_few_shot_examples(
                mode=mode,
                endpoint_keywords=endpoint_keywords if endpoint_keywords else None,
                max_examples=2,
            )
            if few_shot_text:
                parts.append(few_shot_text)
        except Exception as exc:
            logger.debug("Few-shot ornekleri yuklenemedi: %s", exc)

        return "\n\n".join(parts)

    def safe_run(self, ctx: dict) -> AgentResult:
        """
        ServiceTestAgent'i calistir.

        Smart Model Router ile optimal model/temperature/max_tokens secimi yapar.
        Few-shot ornekleri otomatik olarak context'e eklenir.

        ctx parametreleri:
          mode              : "spec_analysis" | "test_generation" | "security_audit" | "chain_builder"
          endpoints         : EndpointInfo dict listesi
          spec_metadata     : Spec baslik/versiyon bilgisi (opsiyonel)
          regulations       : Uyumluluk listesi, default ["BDDK", "KVKK"]
          test_types        : Istenilen test tipleri (test_generation icin)
          max_tests_per_endpoint : Her endpoint icin max test sayisi
          owasp_focus       : Odaklanilacak OWASP kategorileri (security_audit icin)
          flow_hints        : Is akisi ipuclari (chain_builder icin)
          learnings         : KnowledgeStore'dan onceki ogrenmeler
          additional_context : Ek baglam metni
        """
        mode = ctx.get("mode", "test_generation")
        endpoints = ctx.get("endpoints", [])

        # ── Smart Model Router ile model/temperature/max_tokens sec ──────
        try:
            from app.domains.ai.smart_model_router import route_for_endpoints
            recommendation = route_for_endpoints(
                task_type=mode,
                endpoints=endpoints,
            )
            self.model = recommendation.model
            self.temperature = recommendation.temperature
            self.max_tokens = recommendation.max_tokens
            logger.info(
                "ServiceTestAgent[%s] SmartRouter: model=%s temp=%.2f tokens=%d | %s",
                mode, recommendation.model, recommendation.temperature,
                recommendation.max_tokens, recommendation.reason,
            )
        except Exception as exc:
            # Fallback: eski davranis — _resolve_model + sabit temperature
            logger.warning("SmartRouter kullanilamadi, fallback: %s", exc)
            self.model = self._resolve_model()
            if mode == "security_audit":
                self.temperature = 0.15
            elif mode == "test_generation":
                self.temperature = 0.25
            else:
                self.temperature = 0.2

        # System prompt sec
        system_prompt = self._mode_prompts.get(mode, _TEST_GENERATION_PROMPT)

        # Context olustur (few-shot ornekleri dahil)
        user_content = self._build_context(ctx)

        # LLM cagir (JSON modunda)
        try:
            result = self.call_json(
                system=system_prompt,
                user=user_content,
            )
            if result is None:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    error="LLM bos yanit dondurdu",
                )

            # CrossAgentMemory'ye sonuc yayinla (fire-and-forget)
            self._publish_to_memory(mode, result, endpoints)

            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result,
            )
        except Exception as exc:
            logger.exception("ServiceTestAgent[%s] hatasi", mode)
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(exc),
            )

    def _publish_to_memory(self, mode: str, data: dict, endpoints: list) -> None:
        """CrossAgentMemory'ye uretim sonuclarini yayinla."""
        try:
            from app.domains.ai.cross_agent_memory import CrossAgentMemory

            test_count = len(data.get("test_cases", []))
            security_count = len(data.get("security_tests", []))
            chain_count = len(data.get("chains", []))

            event_type = {
                "test_generation": "test_generated",
                "security_audit": "risk_finding",
                "spec_analysis": "analysis_complete",
                "chain_builder": "pattern_detected",
            }.get(mode, "analysis_complete")

            tags = [mode]
            for ep in endpoints[:5]:
                path = ep.get("path", "")
                parts = [p for p in path.split("/") if p and p not in ("api", "v1", "v2")]
                tags.extend(parts[:2])

            CrossAgentMemory.publish(
                agent_name=self.name,
                event_type=event_type,
                data={
                    "project_id": getattr(self, "_project_id", None),
                    "summary": f"{mode}: {test_count} test, {security_count} security, {chain_count} chain",
                    "mode": mode,
                    "test_count": test_count,
                    "security_count": security_count,
                    "chain_count": chain_count,
                    "endpoint_count": len(endpoints),
                    "model": self.model,
                },
                tags=list(set(tags)),
            )
        except Exception as exc:
            logger.debug("CrossAgentMemory publish hatasi: %s", exc)
