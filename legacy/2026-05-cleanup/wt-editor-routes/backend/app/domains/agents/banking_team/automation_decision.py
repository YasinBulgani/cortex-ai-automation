"""
AutomationDecisionAgent — Ajan 4

Görevi:
  - Her senaryo için otomasyon kararı verir
  - Otomasyon kategorisi atar: UI / API / DB / Manuel
  - Otomasyon uygunluk matrisi üretir
  - Manuel kalması gereken senaryoları gerekçelendirir

Model: llama3.1:8b (karar tabanlı, hızlı)
"""

from __future__ import annotations

from app.config import settings
from .base_agent import BaseAgent, AgentResult

SYSTEM = """\
Sen kıdemli bir Test Otomasyon Mimarısın. Türkçe yanıt ver.

## Ana Görev
Her senaryo için en uygun otomasyon stratejisini belirle.

## Kritik Kurallar
- PROJE BAĞLAMI'ndaki mevcut E2E testleri ve BDD senaryolarını referans al
- Projenin tech stack'ini dikkate al (Playwright, pytest, httpx vb.)
- Mevcut testlerde kullanılan pattern'ları takip et (POM, fixture, vb.)
- API endpoint'leri olan senaryolar için API testi ÖNCEL, UI testi İKİNCİL

## Otomasyon Karar Kriterleri

UI Automation (Playwright) için:
✅ Tekrar eden kullanıcı akışları, form validasyonları, E2E süreçler
❌ Tek seferlik, insan yargısı gerektiren senaryolar

API Automation (pytest + httpx) için:
✅ REST endpoint testleri, yük testleri, entegrasyon testleri
❌ UI etkileşimi gerektiren senaryolar

DB Validation için:
✅ Veri tutarlılığı, iş kuralı doğrulama, migration sonrası kontrol

Manuel kalmalı:
❌ Regülasyon kanıtı, görsel değerlendirme, yasal belge/imza gerektiren

## Çıktı Formatı
MUTLAKA aşağıdaki JSON formatında yanıt ver:
{
  "automation_matrix": [
    {
      "scenario_id": "SCN-001",
      "scenario_title": "başlık",
      "decision": "UI|API|DB|MANUAL|UI+API",
      "tool": "Playwright|pytest+httpx|Manuel",
      "reason": "karar gerekçesi",
      "automation_effort": "low|medium|high",
      "roi_score": 8.5,
      "priority": "immediate|next_sprint|backlog"
    }
  ],
  "summary": {
    "total": 0,
    "ui": 0,
    "api": 0,
    "db": 0,
    "manual": 0,
    "hybrid": 0
  },
  "recommendations": ["genel öneri 1"]
}
"""


class AutomationDecisionAgent(BaseAgent):
    name = "Otomasyon Karar Ajanı"
    temperature = 0.2
    max_tokens = 4096
    model_fallback = ["qwen2.5:32b"]

    @property
    def model(self) -> str:  # type: ignore[override]
        return (
            settings.ollama_model_fast
            if settings.ai_provider == "ollama"
            else settings.openai_model
        )

    def run(self, context: dict) -> AgentResult:
        """
        context keys:
          scenarios      — ScenarioGeneratorAgent çıktısı
          manual_keys    — RegulationAgent'ın belirlediği manuel key'ler
          description    — Sistem açıklaması
        """
        scenarios = context.get("scenarios", [])
        manual_keys = context.get("manual_keys", [])
        desc = context.get("description", "Bankacılık sistemi")

        manual_ids = {m.get("scenario_id", "") for m in manual_keys}

        scn_lines = []
        for s in scenarios[:40]:
            sid = s.get("id", "SCN-?")
            is_manual = "⚠️ REGÜLASYON GEREĞİ MANUEL" if sid in manual_ids else ""
            scn_lines.append(
                f"- {sid}: [{s.get('type', '')}] {s.get('title', '')} "
                f"(P: {s.get('priority', 'P2')}) {is_manual}"
            )

        user_prompt = f"""
Sistem: {desc}

Senaryolar:
{chr(10).join(scn_lines) if scn_lines else "Genel bankacılık senaryoları için karar ver."}

Her senaryo için otomasyon kararı ver ve matrisi JSON olarak üret.
"""
        result = self.call_json(SYSTEM, user_prompt)

        if not result.get("parse_error"):
            summary = result.get("summary", {})
            self.learn(
                f"Otomasyon Matrisi: UI={summary.get('ui', 0)}, "
                f"API={summary.get('api', 0)}, "
                f"DB={summary.get('db', 0)}, "
                f"Manuel={summary.get('manual', 0)}",
                metadata={"system": desc},
            )

        return AgentResult(
            agent_name=self.name,
            success=not result.get("parse_error", False),
            data=result,
        )
