"""
DataAnalystAgent — Ajan 1

Görevi:
  - DB şemalarını, API dokümantasyonunu, logları ve analiz dokümanlarını inceler
  - Business flow'ları çıkarır
  - Kritik senaryoları belirler
  - Riskli alanları işaretler

Model: qwen2.5:14b (en iyi analitik model)
"""

from __future__ import annotations

from app.config import settings
from .base_agent import BaseAgent, AgentResult

SYSTEM = """\
Sen kıdemli bir Sistem Analisti ve QA Mimarısın.
Türkçe yanıt ver.

## Ana Görev
Sana verilen GERÇEK veri kaynaklarını (DB şemaları, API dokümantasyonu, loglar, mevcut testler)
analiz ederek iş akışlarını, kritik senaryoları ve riskli alanları çıkar.

## Kritik Kurallar
- PROJE BAĞLAMI bölümündeki gerçek DB tablolarını, API endpoint'lerini ve mevcut testleri referans al
- Generic/hayali modül isimleri KULLANMA — sadece gerçek proje verilerindeki modülleri kullan
- Mevcut BDD senaryoları ve E2E testleri varsa, onlarla çakışmayan yeni alanları keşfet
- Son git değişikliklerindeki modüllere özellikle dikkat et — yeni eklenen/değişen alanlar risk taşır

## Domain Bilgin
Proje bankacılık/finans alanındaysa aşağıdaki kuralları uygula:
- EFT/Havale akışları ve T+0/T+1 settlement kuralları
- BDDK düzenlemeleri (5411 sayılı Bankacılık Kanunu)
- PCI-DSS kart veri güvenliği
- MASAK kara para aklamayla mücadele gereksinimleri
- KYC/AML kontrolleri, limit yönetimi, risk kontrolleri
- 3FA/MFA kimlik doğrulama gereksinimleri

Proje farklı bir domainse, domain bilgini o alana adapte et.

## Çıktı Formatı
MUTLAKA aşağıdaki JSON formatında yanıt ver:
{
  "business_flows": [
    {
      "name": "akış adı (gerçek modül/endpoint adını kullan)",
      "description": "açıklama",
      "modules": ["gerçek_modül1", "gerçek_modül2"],
      "risk_level": "critical|high|medium|low",
      "related_endpoints": ["GET /api/...", "POST /api/..."],
      "related_tables": ["tablo_adı"]
    }
  ],
  "critical_areas": ["alan1", "alan2"],
  "risk_matrix": [
    {
      "area": "alan",
      "risk": "risk açıklaması",
      "severity": "critical|high|medium|low",
      "regulation": "BDDK|PCI-DSS|MASAK|iç kural|yok"
    }
  ],
  "data_gaps": ["eksik veri1", "eksik veri2"],
  "untested_areas": ["henüz test edilmemiş modül/endpoint"],
  "summary": "genel özet"
}

## Örnek (Few-Shot)
Giriş: DB'de users, scenarios, executions tabloları var. API'de /auth/login, /tspm/scenarios, /tspm/executions endpoint'leri var.
Beklenen çıktı (kısaltılmış):
{
  "business_flows": [
    {"name": "Kullanıcı Yönetimi", "modules": ["auth", "users"], "risk_level": "high", "related_endpoints": ["POST /api/v1/auth/login", "GET /api/v1/auth/me"]},
    {"name": "Senaryo Yönetimi", "modules": ["tspm_scenarios"], "risk_level": "medium", "related_endpoints": ["GET /api/v1/tspm/scenarios", "POST /api/v1/tspm/scenarios"]}
  ],
  "critical_areas": ["authentication", "yetkilendirme", "veri tutarlılığı"],
  "untested_areas": ["execution raporlama", "bulk senaryo silme"]
}
Gerçek proje verilerini kullan, bu örneği KOPYALAMA.
"""


class DataAnalystAgent(BaseAgent):
    name = "Veri Analisti"
    temperature = 0.2
    model_fallback = ["mistral:latest"]

    @property
    def model(self) -> str:  # type: ignore[override]
        return (
            settings.ollama_model_analyst
            if settings.ai_provider == "ollama"
            else settings.openai_model
        )

    def run(self, context: dict) -> AgentResult:
        """
        context keys:
          db_schema   — DB şema açıklaması (tablo listesi, kolonlar)
          api_docs    — API endpoint listesi veya swagger özeti
          logs        — Örnek log satırları
          description — Sistem açıklaması (Medifim gibi)
          existing_knowledge — KnowledgeStore'dan gelen geçmiş bağlam
        """
        parts = []
        if context.get("description"):
            parts.append(f"## Sistem: {context['description']}")
        if context.get("db_schema"):
            parts.append(f"## DB Şeması:\n{context['db_schema'][:5000]}")
        if context.get("api_docs"):
            parts.append(f"## API Dokümantasyonu:\n{context['api_docs'][:5000]}")
        if context.get("logs"):
            parts.append(f"## Örnek Loglar:\n{context['logs'][:2000]}")
        if context.get("existing_knowledge"):
            parts.append(f"## Önceki Analiz Bilgisi:\n{context['existing_knowledge'][:2000]}")
        if context.get("existing_features"):
            parts.append(f"## Mevcut BDD Senaryoları:\n{context['existing_features'][:2000]}")
        if context.get("existing_tests"):
            parts.append(f"## Mevcut E2E Testler:\n{context['existing_tests'][:1500]}")
        if context.get("recent_changes"):
            parts.append(f"## Son Git Değişiklikleri:\n{context['recent_changes'][:1000]}")

        if not parts:
            parts.append("Proje bağlamı bulunamadı. System prompt'taki PROJE BAĞLAMI bilgilerini kullan.")

        user_prompt = "\n\n".join(parts)
        user_prompt += "\n\nBu sistemi analiz et ve yukarıdaki JSON formatında yanıt ver. GERÇEK modül ve endpoint isimlerini kullan."

        result = self.call_json(SYSTEM, user_prompt)

        # Öğrenilenleri hafızaya kaydet
        if not result.get("parse_error"):
            summary = result.get("summary", "")
            critical = ", ".join(result.get("critical_areas", []))
            self.learn(
                f"Veri Analizi: {summary}. Kritik alanlar: {critical}",
                metadata={"system": context.get("description", ""), "agent": self.name},
            )

        return AgentResult(
            agent_name=self.name,
            success=not result.get("parse_error", False),
            data=result,
        )
