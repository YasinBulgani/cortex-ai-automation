"""
ScenarioGeneratorAgent — Ajan 2

Görevi:
  - DataAnalystAgent çıktısını alır
  - Pozitif / Negatif / Edge case senaryolar üretir
  - Senaryoları modüllere böler
  - Bağımlılıkları çıkarır
  - Standart format: ad, açıklama, ön koşul, adımlar, beklenen sonuç

Model: qwen2.5:14b
"""

from __future__ import annotations

from app.config import settings
from .base_agent import BaseAgent, AgentResult

SYSTEM = """\
Sen kıdemli bir QA Mühendisisin. Türkçe yanıt ver.

## Ana Görev
Verilen iş akışları ve kritik alanlar için kapsamlı, PROJEYE ÖZGÜ test senaryoları üret.

## Kritik Kurallar
- Senaryolarda GERÇEK proje modüllerini, endpoint'lerini ve tablo isimlerini kullan
- Mevcut BDD senaryolarını (PROJE BAĞLAMI'nda listelenen) TEKRAR ETME
- Mevcut E2E testlerin kapsamadığı alanları ÖNCEL olarak hedefle
- Son git değişikliklerindeki modüllere ekstra senaryo üret (regresyon riski yüksek)
- Senaryo adımlarında projedeki gerçek API path'lerini ve form alanlarını referans al

## Senaryo Çeşitliliği
Her modül/akış için minimum:
- 3 pozitif senaryo (happy path)
- 2 negatif senaryo (hata durumları, yetki kontrolleri)
- 1 edge case / sınır değer senaryosu
- 1 concurrency/race condition senaryosu (varsa)

## Domain-Specific Kurallar
Proje bankacılık/finans alanındaysa:
- Para tutarları: 0, 1 kuruş, max limit, limit+1
- Zaman bazlı: mesai saati, hafta sonu, tatil
- Concurrent: double-spend, race condition
- Session: timeout, token yenileme
Diğer domainler için benzer domain-specific kuralları uygula.

## Çıktı Formatı
MUTLAKA aşağıdaki JSON formatında yanıt ver:
{
  "scenarios": [
    {
      "id": "SCN-001",
      "module": "gerçek_modül_adı",
      "title": "senaryo başlığı",
      "type": "positive|negative|edge_case",
      "description": "açıklama",
      "preconditions": ["ön koşul 1"],
      "steps": [
        {"order": 1, "action": "adım (gerçek endpoint/form kullan)", "expected": "beklenen"}
      ],
      "expected_result": "genel beklenen sonuç",
      "priority": "P0|P1|P2|P3",
      "depends_on": ["SCN-XXX"],
      "tags": ["etiket1", "etiket2"],
      "related_endpoint": "POST /api/v1/..."
    }
  ],
  "modules": ["gerçek_modül1", "gerçek_modül2"],
  "total_count": 0,
  "coverage_summary": "kapsam özeti — hangi alanlar kapsandı, hangisi hâlâ eksik"
}

## Örnek (Few-Shot)
Giriş: "Kullanıcı login modülü, JWT authentication, POST /api/v1/auth/login endpoint'i"
Beklenen çıktı (kısaltılmış):
{
  "scenarios": [
    {
      "id": "SCN-001", "module": "auth", "title": "Geçerli kimlik bilgileriyle başarılı giriş",
      "type": "positive", "priority": "P0",
      "steps": [{"order": 1, "action": "POST /api/v1/auth/login — email: admin@test.com, password: Admin123!", "expected": "200 OK + JWT token döner"}],
      "related_endpoint": "POST /api/v1/auth/login"
    },
    {
      "id": "SCN-002", "module": "auth", "title": "Yanlış şifreyle giriş denemesi",
      "type": "negative", "priority": "P0",
      "steps": [{"order": 1, "action": "POST /api/v1/auth/login — email: admin@test.com, password: wrong", "expected": "401 Unauthorized"}],
      "related_endpoint": "POST /api/v1/auth/login"
    },
    {
      "id": "SCN-003", "module": "auth", "title": "Boş email ile giriş",
      "type": "edge_case", "priority": "P1",
      "steps": [{"order": 1, "action": "POST /api/v1/auth/login — email: '', password: test", "expected": "422 Validation Error"}],
      "related_endpoint": "POST /api/v1/auth/login"
    }
  ]
}
Bu örnekteki gibi GERÇEK endpoint ve veri kullan, generic yazma.
"""


class ScenarioGeneratorAgent(BaseAgent):
    name = "Senaryo Üretici"
    temperature = 0.4
    max_tokens = 6000
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
          analysis     — DataAnalystAgent'ın çıktısı (business_flows, risk_matrix)
          description  — Sistem açıklaması
          focus_module — Belirli bir modüle odaklan (opsiyonel)
          existing_scenarios — Daha önce üretilmiş senaryolar (tekrar önleme)
        """
        analysis = context.get("analysis", {})
        flows = analysis.get("business_flows", [])
        critical = analysis.get("critical_areas", [])
        risks = analysis.get("risk_matrix", [])

        focus = context.get("focus_module", "")
        desc = context.get("description", "Bankacılık sistemi")

        parts = [f"Sistem: {desc}"]

        if flows:
            flow_text = "\n".join([
                f"- {f['name']}: {f['description']} (Risk: {f['risk_level']})"
                for f in flows[:10]
            ])
            parts.append(f"İş Akışları:\n{flow_text}")

        if critical:
            parts.append(f"Kritik Alanlar: {', '.join(critical[:10])}")

        if risks:
            risk_text = "\n".join([
                f"- {r['area']}: {r['risk']} [{r['regulation']}]"
                for r in risks[:8]
            ])
            parts.append(f"Risk Matrisi:\n{risk_text}")

        if focus:
            parts.append(f"\nÖNCELİKLE bu modüle odaklan: {focus}")

        existing = context.get("existing_scenarios", [])
        if existing:
            titles = [s.get("title", "") for s in existing[-10:]]
            parts.append(f"Zaten mevcut senaryolar (tekrar etme): {', '.join(titles)}")

        parts.append("\nYukarıdaki sisteme göre kapsamlı test senaryoları üret.")
        user_prompt = "\n\n".join(parts)

        result = self.call_json(SYSTEM, user_prompt)

        if not result.get("parse_error"):
            count = result.get("total_count") or len(result.get("scenarios", []))
            modules = ", ".join(result.get("modules", []))
            self.learn(
                f"Senaryo Üretimi: {count} senaryo üretildi. Modüller: {modules}",
                metadata={"system": desc, "scenario_count": count},
            )

        return AgentResult(
            agent_name=self.name,
            success=not result.get("parse_error", False),
            data=result,
        )
