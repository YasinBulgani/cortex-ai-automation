"""
DebateOrchestrator — Multi-Agent Debate Pattern (P1)

Akış:
  1. AUTHOR (ScenarioGenerator veya CodeGenerator) → İlk draft
  2. CRITIC → Draft'ı incele, eksikleri bul, puanla
  3. REVISE (Author) → Critic feedback ile düzelt
  4. JUDGE (QualityJudge) → Son puanlama, PASS/FAIL karar

Neden Debate Pattern?
  - Tek LLM çağrısında kalite %60-70 arası → Debate ile %85-95
  - Critic farklı perspektif ekler (karşı-taraf argümanı)
  - Her iterasyonda kalite artışı ölçülebilir
  - Bankacılık regülasyonları için kritik — tek geçiş yeterli değil

Kullanım:
  orchestrator = DebateOrchestrator(max_rounds=2)
  result = orchestrator.run_debate(context)
  # result.data = {"final_output": ..., "debate_log": [...], "quality_score": 8.2}
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings
from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# ── Critic System Prompt ────────────────────────────────────────────────────
CRITIC_SYSTEM = """\
Sen kıdemli bir QA denetçisisin. Üretilen test senaryolarını ve kodunu incele.

## Kritik Kurallar
- PROJE BAĞLAMI'ndaki gerçek modüllere ve endpoint'lere göre eksik kapsam kontrolü yap
- Projedeki mevcut testlerle (BDD + E2E) çakışan senaryolara puan kır — tekrar eklemeye gerek yok
- Somut, uygulanabilir eleştiriler yap — "daha iyi olabilir" gibi generic ifadeler YASAK

## Görevin
1. Eksik senaryoları bul — GERÇEK proje modüllerine göre (pozitif/negatif/edge-case dengesi)
2. Regülasyon boşluklarını tespit et (projeye uygulanabilir olanlar)
3. Assertion zayıflıklarını belirle
4. Veri sınır testlerinin yeterliliğini kontrol et
5. Konkretlik puanı ver (1-10)

## Çıktı Formatı
MUTLAKA JSON formatında yanıt ver:
{
  "score": 6,
  "strengths": ["KONKRET iyi olan yönler"],
  "weaknesses": [
    {
      "category": "scenario_gap|regulation_gap|assertion_weak|data_boundary|naming",
      "severity": "high|medium|low",
      "description": "KONKRET eksiklik — hangi modül/endpoint için",
      "suggestion": "KONKRET düzeltme — ne yapılmalı"
    }
  ],
  "missing_scenarios": [
    {
      "type": "negative|edge_case|positive",
      "title": "Eksik senaryo başlığı",
      "reason": "Neden gerekli — hangi modül/akış kapsamda değil",
      "module": "gerçek_modül_adı"
    }
  ],
  "revision_instructions": "Author'a verilecek düzeltme talimatları — KONKRET ve eylem odaklı, gerçek modül isimlerini kullan"
}
"""

# ── Revision System Prompt ──────────────────────────────────────────────────
REVISION_SYSTEM = """\
Sen kıdemli bir QA mühendisisin. Daha önce ürettiğin senaryolar/kod hakkında
bir denetçiden geri bildirim aldın. Bu geri bildirimi kullanarak çıktını iyileştir.

## Kurallar
1. Critic'in belirttiği HER zayıflığı KONKRET olarak adresle
2. Eksik senaryoları ekle — GERÇEK proje modül/endpoint isimlerini kullan
3. Zayıf assertion'ları güçlendir — status code + body + DB state kontrol et
4. Regülasyon boşluklarını kapat — projeye uygulanabilir olanlar
5. Mevcut İYİ YÖNLERİ KORUYARAK iyileştir
6. PROJE BAĞLAMI'ndaki bilgileri referans alarak düzelt

AYNI JSON FORMATINDA yanıt ver (orijinal format).
"""


class DebateOrchestrator(BaseAgent):
    """Multi-agent debate: Author → Critic → Revise → Judge."""

    name = "Tartışma Orkestratörü"
    temperature = 0.3
    max_tokens = 4096
    model_fallback = ["mistral:latest"]

    def __init__(self, max_rounds: int = 2, min_quality: float = 7.0):
        super().__init__()
        self.max_rounds = max_rounds
        self.min_quality = min_quality

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
          debate_type      — "scenario" | "code" (hangi çıktıyı tartışacak)
          author_output    — Author'ın ilk çıktısı (JSON dict)
          author_system    — Author'ın system prompt'u
          description      — Sistem açıklaması
          regulation_rules — Regülasyon kuralları
          scenarios        — (code debate için) Senaryolar
        """
        debate_type = context.get("debate_type", "scenario")
        author_output = context.get("author_output", {})
        description = context.get("description", "Bankacılık sistemi")
        regulation_rules = context.get("regulation_rules", {})

        if not author_output:
            return AgentResult(
                agent_name=self.name,
                success=False,
                error="Tartışılacak author çıktısı yok",
            )

        debate_log: list[dict] = []
        current_output = author_output
        best_score = 0.0
        best_output = author_output

        for round_num in range(1, self.max_rounds + 1):
            logger.info("Debate round %d/%d — type=%s", round_num, self.max_rounds, debate_type)

            # ── CRITIC ──────────────────────────────────────────────
            critic_result = self._run_critic(current_output, description, regulation_rules)
            critic_score = critic_result.get("score", 0)

            debate_log.append({
                "round": round_num,
                "phase": "critic",
                "score": critic_score,
                "weaknesses_count": len(critic_result.get("weaknesses", [])),
                "missing_count": len(critic_result.get("missing_scenarios", [])),
            })

            logger.info("  Critic score: %.1f, weaknesses: %d", critic_score, len(critic_result.get("weaknesses", [])))

            # Kalite yeterli mi?
            if critic_score >= self.min_quality:
                logger.info("  ✅ Kalite yeterli (%.1f >= %.1f), debate bitiyor", critic_score, self.min_quality)
                best_output = current_output
                best_score = critic_score
                break

            # ── REVISE ──────────────────────────────────────────────
            revised_output = self._run_revision(
                current_output, critic_result, description, context
            )

            debate_log.append({
                "round": round_num,
                "phase": "revision",
                "changes": self._count_changes(current_output, revised_output, debate_type),
            })

            if critic_score > best_score:
                best_score = critic_score
                best_output = revised_output

            current_output = revised_output

        # ── JUDGE (Final) ───────────────────────────────────────────
        judge_result = self._run_final_judge(best_output, description, regulation_rules)
        final_score = judge_result.get("weighted_score", best_score)
        verdict = judge_result.get("verdict", "PASS" if final_score >= self.min_quality else "WARN")

        debate_log.append({
            "round": "final",
            "phase": "judge",
            "score": final_score,
            "verdict": verdict,
        })

        # ── KnowledgeStore ──────────────────────────────────────────
        self.learn(
            f"Debate ({debate_type}): {len(debate_log)} adım, "
            f"başlangıç={author_output.get('score', '?')}, son={final_score:.1f}, "
            f"verdict={verdict}",
            metadata={
                "debate_type": debate_type,
                "rounds": self.max_rounds,
                "final_score": final_score,
                "verdict": verdict,
            },
        )

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "final_output": best_output,
                "debate_log": debate_log,
                "quality_score": final_score,
                "verdict": verdict,
                "rounds_used": len([d for d in debate_log if d.get("phase") == "critic"]),
                "improvement": final_score - (debate_log[0].get("score", 0) if debate_log else 0),
            },
        )

    # ── Internal Methods ────────────────────────────────────────────────────

    def _run_critic(self, output: dict, description: str, regulation_rules: dict) -> dict:
        """Critic: çıktıyı incele ve puanla."""
        # Output'u okunabilir forma çevir
        output_text = json.dumps(output, ensure_ascii=False, indent=2)[:3000]

        rules_text = ""
        if regulation_rules:
            rules = regulation_rules.get("rules", [])
            rules_text = "\n".join([
                f"  - {r.get('regulation', '')}: {r.get('description', '')[:80]}"
                for r in rules[:10]
            ])

        user_prompt = (
            f"## Sistem Açıklaması\n{description[:300]}\n\n"
            f"## Regülasyon Kuralları\n{rules_text}\n\n"
            f"## İncelenecek Çıktı\n```json\n{output_text}\n```\n\n"
            f"Bu çıktıyı bankacılık QA kalite standartlarına göre değerlendir."
        )

        result = self.call_json(CRITIC_SYSTEM, user_prompt)

        # Score doğrulaması
        score = result.get("score", 5)
        if not isinstance(score, (int, float)):
            score = 5
        result["score"] = min(10, max(0, score))

        return result

    def _run_revision(
        self,
        current_output: dict,
        critic_result: dict,
        description: str,
        context: dict,
    ) -> dict:
        """Author'a critic feedback vererek revize ettir."""
        output_text = json.dumps(current_output, ensure_ascii=False, indent=2)[:2500]
        feedback_text = json.dumps(critic_result, ensure_ascii=False, indent=2)[:1500]

        revision_instructions = critic_result.get("revision_instructions", "Genel iyileştirme yap")

        user_prompt = (
            f"## Orijinal Çıktın\n```json\n{output_text}\n```\n\n"
            f"## Critic Geri Bildirimi\n```json\n{feedback_text}\n```\n\n"
            f"## Düzeltme Talimatları\n{revision_instructions}\n\n"
            f"Yukarıdaki feedback'e göre çıktını iyileştir. "
            f"İYİ YANLARI KORU, sadece eksikleri düzelt."
        )

        revised = self.call_json(REVISION_SYSTEM, user_prompt)

        # Eğer revision başarısızsa orijinali döndür
        if revised.get("parse_error"):
            return current_output

        return revised

    def _run_final_judge(
        self, output: dict, description: str, regulation_rules: dict
    ) -> dict:
        """QualityJudge 4-boyutlu rubrik ile final değerlendirme."""
        try:
            from .quality_judge import QualityJudgeAgent

            judge = QualityJudgeAgent()

            # Judge context hazırla
            scenarios = output.get("scenarios", [])
            generated_code = {}
            if "bdd_features" in output or "playwright_tests" in output:
                generated_code = output

            judge_context = {
                "scenarios": scenarios,
                "generated_code": generated_code,
                "regulation_rules": regulation_rules,
                "description": description,
            }

            result = judge.run(judge_context)
            if result.success:
                return result.data
        except Exception as e:
            logger.debug("Final judge hatası: %s", e)

        # Fallback: basit skor
        return {"weighted_score": 6.0, "verdict": "WARN"}

    def _count_changes(self, old: dict, new: dict, debate_type: str) -> dict:
        """İki versiyon arasındaki değişiklikleri say."""
        changes = {"added": 0, "modified": 0, "total": 0}

        if debate_type == "scenario":
            old_ids = {s.get("id", "") for s in old.get("scenarios", [])}
            new_scenarios = new.get("scenarios", [])
            changes["total"] = len(new_scenarios)
            changes["added"] = sum(1 for s in new_scenarios if s.get("id", "") not in old_ids)
            changes["modified"] = changes["total"] - changes["added"]
        elif debate_type == "code":
            for key in ("bdd_features", "playwright_tests", "api_tests"):
                old_count = len(old.get(key, []))
                new_count = len(new.get(key, []))
                changes["added"] += max(0, new_count - old_count)
                changes["total"] += new_count

        return changes


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience: Debate entegrasyonu orchestrator'a kolay bağlanabilir
# ═══════════════════════════════════════════════════════════════════════════════

def debate_scenarios(
    author_output: dict,
    description: str,
    regulation_rules: dict,
    max_rounds: int = 2,
    min_quality: float = 7.0,
) -> AgentResult:
    """Senaryo debate'i çalıştır — orchestrator'dan doğrudan çağrılabilir."""
    debater = DebateOrchestrator(max_rounds=max_rounds, min_quality=min_quality)
    return debater.run({
        "debate_type": "scenario",
        "author_output": author_output,
        "description": description,
        "regulation_rules": regulation_rules,
    })


def debate_code(
    author_output: dict,
    description: str,
    regulation_rules: dict,
    scenarios: list,
    max_rounds: int = 2,
    min_quality: float = 7.0,
) -> AgentResult:
    """Kod debate'i çalıştır — orchestrator'dan doğrudan çağrılabilir."""
    debater = DebateOrchestrator(max_rounds=max_rounds, min_quality=min_quality)
    return debater.run({
        "debate_type": "code",
        "author_output": author_output,
        "description": description,
        "regulation_rules": regulation_rules,
        "scenarios": scenarios,
    })
