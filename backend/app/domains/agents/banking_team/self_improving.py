"""
SelfImprovingAgent — Ajan 6 (Sürekli Öğrenme Döngüsü)

Görevi:
  - Bir önceki döngünün tüm çıktılarını analiz eder
  - Başarısız senaryoları ve nedenleri çıkarır
  - Senaryoları günceller / iyileştirir
  - Otomasyon kodunu optimize eder
  - KnowledgeStore'dan geçmişi okur ve yeni öğrenimleri yazar
  - Bir sonraki döngü için öncelik sıralaması yapar

Model: qwen2.5:14b (meta-analiz için en güçlü model)
"""

from __future__ import annotations

from app.config import settings
from .base_agent import BaseAgent, AgentResult

SYSTEM = """\
Sen bir AI QA Sistem Mimarısın ve sürekli öğrenme uzmanısın. Türkçe yanıt ver.

## Ana Görev
Verilen test döngüsünün TÜM çıktılarını analiz et, iyileştirme önerileri üret
ve bir sonraki döngü için KONKRET aksiyon planı çıkar.

## Kritik Kurallar
- PROJE BAĞLAMI'ndaki gerçek modül/endpoint/tablo isimlerini kullanarak kapsam boşluğu analizi yap
- Geçmiş öğrenimlerdeki (KnowledgeStore) hata kalıplarını referans al — aynı hataları tekrarlama
- Mevcut testlerle (BDD + E2E) çakışmayan yeni test alanları öner
- Somut, uygulanabilir öneriler ver — "daha fazla test yaz" gibi generic öneriler YASAK

## Analiz Kriterleri
1. Başarısız test kalıpları — neden başarısız? Tekrar eden hata var mı?
2. Kapsam boşlukları — GERÇEK proje modüllerinden hangisi yetersiz test edilmiş?
3. Yanlış pozitif/negatif senaryolar — gerçek dünyada mantıklı mı?
4. Otomasyon oranı düşük alanlar — hangi modüller daha fazla otomasyona uygun?
5. Regülasyon kuralı eksiklikleri — projeye uygulanabilir regülasyonlardan hangisi eksik?

## Çıktı Formatı
MUTLAKA aşağıdaki JSON formatında yanıt ver:
{
  "cycle_assessment": {
    "cycle_number": 1,
    "overall_score": 7.5,
    "strengths": ["KONKRET güçlü yön — hangi modül/senaryo iyi"],
    "weaknesses": ["KONKRET zayıf yön — hangi modül/endpoint eksik"]
  },
  "improvements": [
    {
      "target": "scenario|code|regulation|coverage",
      "item_id": "SCN-001 veya gerçek_modül_adı",
      "current_issue": "mevcut sorun",
      "suggested_fix": "KONKRET önerilen düzeltme (ne yapılacak, nasıl)",
      "priority": "high|medium|low"
    }
  ],
  "next_cycle_priorities": [
    {
      "focus": "KONKRET modül/endpoint/alan",
      "reason": "neden öncelikli",
      "expected_improvement": "beklenen gelişme"
    }
  ],
  "new_scenarios_needed": [
    {
      "area": "gerçek_modül_adı",
      "reason": "neden eksik",
      "scenario_type": "positive|negative|edge_case",
      "related_endpoint": "varsa API path"
    }
  ],
  "automation_optimizations": ["KONKRET optimizasyon"],
  "learning_summary": "bu döngüden öğrenilenler — gelecek döngüler için not"
}
"""


class SelfImprovingAgent(BaseAgent):
    name = "Self-Improving Ajanı"
    temperature = 0.3
    max_tokens = 5000
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
          cycle_number      — Kaçıncı döngü
          analysis          — DataAnalystAgent çıktısı
          scenarios         — Üretilen senaryolar
          regulation_rules  — RegulationAgent çıktısı
          automation_matrix — Otomasyon kararları
          generated_code    — Üretilen kod sayısı
          knowledge_history — KnowledgeStore'dan son insight'lar
          previous_improvements — Önceki döngünün iyileştirme önerileri
        """
        cycle = context.get("cycle_number", 1)
        scenarios = context.get("scenarios", [])
        matrix = context.get("automation_matrix", [])
        rules = context.get("regulation_rules", {})
        generated = context.get("generated_code", {})
        history = context.get("knowledge_history", "")
        prev = context.get("previous_improvements", [])

        # Özet metrikler
        total_scn = len(scenarios)
        types = {"positive": 0, "negative": 0, "edge_case": 0}
        for s in scenarios:
            t = s.get("type", "positive")
            types[t] = types.get(t, 0) + 1

        auto_summary = {}
        if matrix:
            for m in matrix:
                d = m.get("decision", "MANUAL")
                auto_summary[d] = auto_summary.get(d, 0) + 1

        rules_count = len(rules.get("rules", []))
        manual_keys = len(rules.get("manual_keys", []))
        code_count = generated.get("generated_count", 0) if isinstance(generated, dict) else 0

        parts = [
            f"Döngü #{cycle} Özeti:",
            f"- Toplam senaryo: {total_scn} (Pozitif={types['positive']}, "
            f"Negatif={types['negative']}, EdgeCase={types['edge_case']})",
            f"- Regülasyon kuralı: {rules_count}, Manuel key: {manual_keys}",
            f"- Otomasyon dağılımı: {auto_summary}",
            f"- Üretilen kod dosyası: {code_count}",
        ]

        if history:
            parts.append(f"\nGeçmiş Öğrenim Bağlamı:\n{history[:800]}")

        if prev:
            prev_text = "\n".join([
                f"- {p.get('item_id', '')}: {p.get('suggested_fix', '')}"
                for p in prev[:5]
            ])
            parts.append(f"\nÖnceki Döngü İyileştirme Önerileri:\n{prev_text}")

        # Kapsam boşluklarını analiz et
        modules_covered = list({s.get("module", "") for s in scenarios if s.get("module")})
        if modules_covered:
            parts.append(f"\nKapsanan modüller: {', '.join(modules_covered)}")

        parts.append(
            "\nBu döngüyü değerlendir. Zayıf noktaları belirle. "
            "Bir sonraki döngü için öncelikleri ve iyileştirme planını üret."
        )

        user_prompt = "\n".join(parts)
        result = self.call_json(SYSTEM, user_prompt)

        if not result.get("parse_error"):
            score = result.get("cycle_assessment", {}).get("overall_score", 0)
            learning = result.get("learning_summary", "")
            improvements_count = len(result.get("improvements", []))

            # Bu döngüden öğrenilenleri KnowledgeStore'a kalıcı kaydet
            self.learn(
                f"Döngü #{cycle} Öğrenimi (Skor: {score}/10): {learning}. "
                f"{improvements_count} iyileştirme önerisi üretildi.",
                metadata={
                    "cycle": cycle,
                    "score": score,
                    "improvements": improvements_count,
                },
            )

        return AgentResult(
            agent_name=self.name,
            success=not result.get("parse_error", False),
            data=result,
        )
