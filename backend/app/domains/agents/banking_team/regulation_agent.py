"""
RegulationAgent — Ajan 3

Görevi:
  - Her senaryoyu bankacılık regülasyonlarına bağlar
  - BDDK, PCI-DSS, MASAK, KYC/AML kurallarını uygular
  - JSON/YAML rule engine formatında kural seti üretir
  - Manuel test key'lerini belirler (regülasyon bağımlısı olanlar)

Model: llama3.1:8b (kural tabanlı, hız önemli)
"""

from __future__ import annotations

from app.config import settings
from .base_agent import BaseAgent, AgentResult

SYSTEM = """\
Sen Türk Bankacılık ve Finans Regülasyon Uzmanısın. Türkçe yanıt ver.

## Ana Görev
Verilen senaryoları uygun regülasyon kurallarına bağla ve test edilebilir kural motoru üret.

## Kritik Kurallar
- PROJE BAĞLAMI'ndaki gerçek modülleri ve endpoint'leri referans alarak kuralları bağla
- Projenin DB şemasındaki hassas alanları (ör. kişisel veri kolonları) KVKK kapsamında değerlendir
- API endpoint'lerindeki authentication/authorization mekanizmalarını güvenlik kurallarıyla eşleştir
- Sadece projeyle GERÇEKTEN İLGİLİ regülasyonları uygula — proje bankacılık değilse PCI-DSS geçersiz olabilir

## Bilgi Tabanı
Uygulanabilir regülasyonlar (proje domainine göre seç):
- BDDK: 5411 sayılı Bankacılık Kanunu, Kredi Riski Yönetimi Tebliği
- PCI-DSS v4.0: Kart veri güvenliği standartları
- MASAK: 5549 sayılı Kanun, şüpheli işlem bildirimi (STR)
- KYC/AML: Müşteri tanıma, risk bazlı yaklaşım
- SWIFT: Uluslararası transfer kuralları, sanction screening
- TCMB: Ödeme sistemleri tebliğleri
- SPK: Sermaye piyasası işlemleri
- KVKK: Kişisel veri işleme (HER projede geçerli)

## Çıktı Formatı
MUTLAKA aşağıdaki JSON formatında yanıt ver:
{
  "rules": [
    {
      "rule_id": "BDDK-001",
      "regulation": "BDDK|PCI-DSS|MASAK|KYC|SWIFT|KVKK|TCMB",
      "title": "Kural başlığı",
      "description": "Kural açıklaması",
      "applies_to": ["SCN-001", "SCN-002"],
      "related_endpoint": "POST /api/v1/...",
      "related_table": "tablo_adı",
      "validation": {
        "type": "range|regex|exists|custom",
        "field": "alan adı",
        "condition": "koşul",
        "error_message": "hata mesajı"
      },
      "severity": "mandatory|recommended|informational",
      "test_evidence_required": true
    }
  ],
  "manual_keys": [
    {
      "scenario_id": "SCN-XXX",
      "reason": "Manuel kalma gerekçesi",
      "regulation": "ilgili regülasyon",
      "risk_level": "critical|high"
    }
  ],
  "compliance_summary": {
    "total_rules": 0,
    "mandatory": 0,
    "scenarios_with_regulation": 0,
    "applicable_regulations": ["proje için geçerli regülasyonlar"]
  }
}
"""


class RegulationAgent(BaseAgent):
    name = "Regülasyon Ajanı"
    temperature = 0.1  # Kural tabanlı — düşük yaratıcılık
    max_tokens = 5000
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
          scenarios   — ScenarioGeneratorAgent'ın ürettiği senaryolar
          description — Sistem açıklaması
          regulations — Hangi regülasyonlar uygulanacak (opsiyonel, default: hepsi)
        """
        scenarios = context.get("scenarios", [])
        desc = context.get("description", "Bankacılık sistemi")
        regs = context.get("regulations", ["BDDK", "PCI-DSS", "MASAK", "KYC", "KVKK"])

        scn_text = "\n".join([
            f"- {s.get('id', 'SCN-?')}: {s.get('title', '')} [{s.get('type', '')}]"
            for s in scenarios[:30]
        ])

        user_prompt = f"""
Sistem: {desc}
Uygulanacak Regülasyonlar: {', '.join(regs)}

Test Senaryoları:
{scn_text if scn_text else "Genel bankacılık senaryoları varsay."}

Bu senaryoları yukarıdaki regülasyonlarla ilişkilendir.
Hangi senaryolar regülasyon gereği manuel test edilmeli? Belirle.
Kural motorunu JSON formatında üret.
"""
        result = self.call_json(SYSTEM, user_prompt)

        if not result.get("parse_error"):
            total_rules = result.get("compliance_summary", {}).get("total_rules", 0)
            manual_count = len(result.get("manual_keys", []))
            self.learn(
                f"Regülasyon Analizi: {total_rules} kural, {manual_count} manuel test key. "
                f"Regülasyonlar: {', '.join(regs)}",
                metadata={"system": desc, "rule_count": total_rules},
            )

        return AgentResult(
            agent_name=self.name,
            success=not result.get("parse_error", False),
            data=result,
        )
