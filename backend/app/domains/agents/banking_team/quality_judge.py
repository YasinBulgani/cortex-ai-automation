"""
QualityJudgeAgent — LLM-as-Judge: Üretilen test senaryolarını ve kodu puanlar.

4 Boyutlu Rubrik:
  1. Senaryo Tamlığı     (40%) — Pozitif, negatif, edge-case kapsam
  2. Regülasyon Uyumu     (30%) — BDDK, PCI-DSS, MASAK, KYC, KVKK
  3. Assertion Gücü       (20%) — Doğrulama kapsamı ve kalitesi
  4. Veri Sınırları       (10%) — Test verisi çeşitliliği ve boundary values

Entegrasyon:
  CodeGenerator sonrası çalışır → Kalite skoru düşükse (< 6/10) senaryolar geri
  döndürülür → SelfImproving'e de feedback verilir.

Kalite Geçidi:
  - score >= 7.0   → PASS  (OutputWriter'a devam et)
  - 5.0 <= score < 7.0 → WARN (devam et ama uyarı logla)
  - score < 5.0   → FAIL  (kodları yeniden üret veya atla)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings
from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# ── 4-Dimensional Rubric ────────────────────────────────────────────────────
RUBRIC_DIMENSIONS = [
    {
        "name": "scenario_completeness",
        "label": "Senaryo Tamlığı",
        "weight": 0.40,
        "description": (
            "Pozitif, negatif ve edge-case senaryoların kapsama oranı. "
            "Eksik akış var mı? Happy path + sad path + boundary conditions kontrol et."
        ),
    },
    {
        "name": "regulation_alignment",
        "label": "Regülasyon Uyumu",
        "weight": 0.30,
        "description": (
            "BDDK, PCI-DSS, MASAK AML, KYC, KVKK regülasyonlarına uyum. "
            "Her regülasyon için en az bir senaryo var mı? Compliance kontrolleri yeterli mi?"
        ),
    },
    {
        "name": "assertion_strength",
        "label": "Assertion Gücü",
        "weight": 0.20,
        "description": (
            "Test assertion'larının kalitesi. Sadece status code değil, "
            "response body, hata mesajları, DB state kontrolleri de var mı? "
            "toBeVisible, toHaveText gibi güçlü Playwright assertion'lar kullanılmış mı?"
        ),
    },
    {
        "name": "data_boundaries",
        "label": "Veri Sınırları",
        "weight": 0.10,
        "description": (
            "Test verisi çeşitliliği: null, boş string, max-length, özel karakter, "
            "Türkçe karakter (ğüşöçı), negatif sayılar, tarih sınırları kontrol edilmiş mi?"
        ),
    },
]

SYSTEM_JUDGE = """\
Sen kıdemli bir QA kalite denetçisisin. Test senaryolarını ve kodunu 4 boyutlu rubrikle değerlendir.

## Kritik Kurallar
- PROJE BAĞLAMI'ndaki gerçek modüllere, endpoint'lere ve tablolara karşı kapsam kontrolü yap
- Projedeki mevcut testlerin kapsamıyla karşılaştır — aynı alanı tekrar test eden senaryolara puan kır
- Gerçek API response schema'larıyla assertion uyumunu kontrol et
- Domain-specific kuralları (bankacılık/finans regülasyonları vb.) projenin gerçek domaininden çıkar

## Rubrik
1. Senaryo Tamlığı (40%): Pozitif/negatif/edge-case kapsam — GERÇEK proje modüllerine göre değerlendir
2. Regülasyon Uyumu (30%): Projeye uygulanabilir regülasyonların kontrolü
3. Assertion Gücü (20%): Doğrulama kalitesi (status code + body + DB state + UI state)
4. Veri Sınırları (10%): Boundary values, null, Türkçe karakter (ğüşöçı), max-length

Her boyut için 1-10 arası puan ver ve KONKRET gerekçe yaz.

## Çıktı Formatı
MUTLAKA aşağıdaki JSON formatında yanıt ver:
{
  "dimensions": [
    {
      "name": "scenario_completeness",
      "score": 7,
      "max_score": 10,
      "reasoning": "Konkret neden bu puanı verdin",
      "missing": ["Eksik olan şeyler — gerçek modül/endpoint bazında"]
    },
    {
      "name": "regulation_alignment",
      "score": 6,
      "max_score": 10,
      "reasoning": "Konkret neden",
      "missing": ["Eksik regülasyon kontrolleri"]
    },
    {
      "name": "assertion_strength",
      "score": 5,
      "max_score": 10,
      "reasoning": "Konkret neden",
      "missing": ["Eksik assertion türleri"]
    },
    {
      "name": "data_boundaries",
      "score": 4,
      "max_score": 10,
      "reasoning": "Konkret neden",
      "missing": ["Eksik veri sınır testleri"]
    }
  ],
  "weighted_score": 5.8,
  "verdict": "PASS|WARN|FAIL",
  "summary": "Genel değerlendirme — hangi gerçek modüller yeterli, hangisi yetersiz",
  "improvements": [
    {
      "priority": "high|medium|low",
      "dimension": "hangi boyut",
      "suggestion": "KONKRET iyileştirme — hangi modül/endpoint için ne yapılmalı"
    }
  ]
}
"""


class QualityJudgeAgent(BaseAgent):
    """LLM-as-Judge: Test kalitesini 4 boyutlu rubrikle puanlar."""

    name = "Kalite Hakimi"
    temperature = 0.1
    max_tokens = 2048
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
          scenarios        — Üretilen senaryolar listesi
          generated_code   — Üretilen kod dict'i (bdd_features, playwright_tests, api_tests)
          regulation_rules — Regülasyon kuralları
          description      — Sistem açıklaması
        """
        scenarios = context.get("scenarios", [])
        generated_code = context.get("generated_code", {})
        regulation_rules = context.get("regulation_rules", {})
        description = context.get("description", "")

        if not scenarios and not generated_code:
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={
                    "weighted_score": 0,
                    "verdict": "SKIP",
                    "message": "Değerlendirilecek senaryo veya kod yok.",
                },
            )

        # ── Değerlendirme verisi hazırla ─────────────────────────────
        eval_data = self._prepare_evaluation(scenarios, generated_code, regulation_rules, description)

        # ── LLM ile değerlendir ──────────────────────────────────────
        judge_result = self._evaluate_with_llm(eval_data)

        if not judge_result or judge_result.get("parse_error"):
            # LLM çalışmadıysa heuristic değerlendirme yap
            judge_result = self._heuristic_evaluation(scenarios, generated_code, regulation_rules)

        # ── Kalite verdictini hesapla ────────────────────────────────
        weighted_score = judge_result.get("weighted_score", 0)
        if weighted_score >= 7.0:
            verdict = "PASS"
        elif weighted_score >= 5.0:
            verdict = "WARN"
        else:
            verdict = "FAIL"

        judge_result["verdict"] = verdict
        judge_result["quality_gate_passed"] = verdict in ("PASS", "WARN")

        # ── KnowledgeStore'a kaydet ──────────────────────────────────
        self.learn(
            f"Kalite Değerlendirmesi: {verdict} (skor: {weighted_score:.1f}/10). "
            f"{len(scenarios)} senaryo, {generated_code.get('generated_count', 0)} kod dosyası. "
            f"Eksikler: {', '.join(judge_result.get('improvements', [{}])[:3].__class__.__name__ for _ in range(0))}",
            metadata={
                "weighted_score": weighted_score,
                "verdict": verdict,
                "scenario_count": len(scenarios),
            },
        )

        # ── Fine-Tune Data Collector — yuksek kaliteli ciftleri topla ────
        if weighted_score >= 7.0:
            try:
                from app.domains.ai.quality_metrics import collect_finetune_pair
                collect_finetune_pair(
                    agent_name="QualityJudge",
                    system_prompt="Kalite degerlendirmesi",
                    user_prompt=str(scenarios[:5])[:1000],
                    response=json.dumps(judge_result, ensure_ascii=False)[:2000],
                    quality_score=weighted_score,
                    is_good_example=True,
                    project_id=getattr(self, "_project_id", None),
                )
            except Exception as exc:
                logger.debug("Fine-tune pair kayit hatasi: %s", exc)

        # ── CrossAgentMemory'ye yayinla ──────────────────────────────
        try:
            from app.domains.ai.cross_agent_memory import CrossAgentMemory
            CrossAgentMemory.publish(
                agent_name=self.name,
                event_type="quality_score",
                data={
                    "project_id": getattr(self, "_project_id", None),
                    "score": weighted_score,
                    "verdict": verdict,
                    "scenario_count": len(scenarios),
                },
                tags=["quality", verdict.lower()],
            )
        except Exception as exc:
            logger.debug("CrossAgentMemory publish hatasi: %s", exc)

        return AgentResult(
            agent_name=self.name,
            success=True,
            data=judge_result,
        )

    def _prepare_evaluation(
        self,
        scenarios: list,
        generated_code: dict,
        regulation_rules: dict,
        description: str,
    ) -> str:
        """LLM'e gönderilecek değerlendirme metnini hazırla."""
        parts = []

        if description:
            parts.append(f"## Sistem Açıklaması\n{description[:500]}")

        # Senaryo özeti
        if scenarios:
            parts.append(f"\n## Senaryolar ({len(scenarios)} adet)")
            for i, s in enumerate(scenarios[:15], 1):
                stype = s.get("type", "?")
                priority = s.get("priority", "?")
                title = s.get("title", s.get("scenario_title", ""))
                module = s.get("module", "?")
                steps = s.get("steps", [])
                endpoint = s.get("related_endpoint", "")
                ep_str = f" → {endpoint}" if endpoint else ""
                parts.append(f"  {i}. [{stype}/{priority}] [{module}] {title} ({len(steps)} adım){ep_str}")

        # Kod özeti
        bdd = generated_code.get("bdd_features", [])
        pw = generated_code.get("playwright_tests", [])
        api = generated_code.get("api_tests", [])

        if bdd:
            parts.append(f"\n## BDD Senaryoları ({len(bdd)} adet)")
            for feat in bdd[:3]:
                content = feat.get("content", "")[:400]
                parts.append(f"```gherkin\n{content}\n```")

        if pw:
            parts.append(f"\n## Playwright Testleri ({len(pw)} adet)")
            for test in pw[:2]:
                content = test.get("content", "")[:500]
                parts.append(f"```typescript\n{content}\n```")

        if api:
            parts.append(f"\n## API Testleri ({len(api)} adet)")
            for test in api[:2]:
                content = test.get("content", "")[:500]
                parts.append(f"```python\n{content}\n```")

        # Regülasyon kuralları
        rules = regulation_rules.get("rules", [])
        if rules:
            parts.append(f"\n## Regülasyon Kuralları ({len(rules)} adet)")
            for r in rules[:5]:
                parts.append(f"  - {r.get('regulation', '?')}: {r.get('description', '')[:100]}")

        return "\n".join(parts)

    def _evaluate_with_llm(self, eval_data: str) -> dict | None:
        """LLM'e rubrik ile değerlendirme yaptır."""
        try:
            result = self.call_json(SYSTEM_JUDGE, eval_data)
            if result.get("parse_error"):
                return None

            # Weighted score'u doğrula/yeniden hesapla
            dimensions = result.get("dimensions", [])
            if dimensions:
                result["weighted_score"] = self._calc_weighted_score(dimensions)

            return result
        except Exception as e:
            logger.debug("QualityJudge LLM hatası: %s", e)
            return None

    def _calc_weighted_score(self, dimensions: list[dict]) -> float:
        """Boyut puanlarindan weighted score hesapla."""
        total = 0.0
        known_names = {r["name"] for r in RUBRIC_DIMENSIONS}
        weight_map = {r["name"]: r["weight"] for r in RUBRIC_DIMENSIONS}

        for dim in dimensions:
            dim_name = dim.get("name", "")
            score = min(float(dim.get("score", 0)), 10.0)

            if dim_name in weight_map:
                weight = weight_map[dim_name]
            else:
                weight = 0.25  # default esit dagilim
                logger.warning(
                    "QualityJudge: Bilinmeyen dimension '%s', varsayılan weight=0.25 kullaniliyor. "
                    "Beklenen: %s",
                    dim_name,
                    ", ".join(sorted(known_names)),
                )
            total += score * weight
        return round(total, 2)

    # ── Heuristic Fallback ──────────────────────────────────────────────────

    def _heuristic_evaluation(
        self,
        scenarios: list,
        generated_code: dict,
        regulation_rules: dict,
    ) -> dict:
        """LLM çalışmadığında kural-tabanlı heuristic değerlendirme."""
        dimensions = []

        # 1. Senaryo Tamlığı
        types = {s.get("type", "unknown") for s in scenarios}
        type_count = len(types)
        scenario_score = min(10, len(scenarios) * 1.5)
        if "negative" not in types and "edge_case" not in types:
            scenario_score = min(scenario_score, 5)
        if type_count >= 3:
            scenario_score = min(10, scenario_score + 2)
        dimensions.append({
            "name": "scenario_completeness",
            "score": round(scenario_score, 1),
            "max_score": 10,
            "reasoning": f"{len(scenarios)} senaryo, {type_count} farklı tip ({', '.join(types)})",
            "missing": [] if type_count >= 3 else [t for t in ["positive", "negative", "edge_case"] if t not in types],
        })

        # 2. Regülasyon Uyumu
        rules = regulation_rules.get("rules", [])
        regulation_labels = {r.get("regulation", "") for r in rules}
        expected_regs = {"BDDK", "PCI-DSS", "MASAK", "KYC", "KVKK"}
        covered = regulation_labels & expected_regs
        reg_score = (len(covered) / len(expected_regs)) * 10 if expected_regs else 5
        dimensions.append({
            "name": "regulation_alignment",
            "score": round(reg_score, 1),
            "max_score": 10,
            "reasoning": f"{len(covered)}/{len(expected_regs)} regülasyon kapsandı",
            "missing": list(expected_regs - covered),
        })

        # 3. Assertion Gücü (kod analizi)
        all_code = ""
        for key in ("bdd_features", "playwright_tests", "api_tests"):
            for item in generated_code.get(key, []):
                all_code += item.get("content", "") + "\n"

        assertion_patterns = [
            "expect(", "toBeVisible", "toHaveText", "toContain",
            "assert ", "assertEqual", "assertIn", "status_code",
            "toBeTruthy", "toHaveCount", "response.json",
        ]
        found = sum(1 for p in assertion_patterns if p in all_code)
        assert_score = min(10, (found / max(len(assertion_patterns), 1)) * 12)
        dimensions.append({
            "name": "assertion_strength",
            "score": round(assert_score, 1),
            "max_score": 10,
            "reasoning": f"{found}/{len(assertion_patterns)} assertion pattern bulundu",
            "missing": [p for p in assertion_patterns if p not in all_code][:5],
        })

        # 4. Veri Sınırları
        boundary_patterns = [
            "null", "empty", "max", "min", "boundary", "özel karakter",
            "uzun_", "negatif", "sıfır", "geçersiz", "invalid",
        ]
        found_boundary = sum(1 for p in boundary_patterns if p.lower() in all_code.lower())
        data_score = min(10, (found_boundary / max(len(boundary_patterns), 1)) * 12)
        dimensions.append({
            "name": "data_boundaries",
            "score": round(data_score, 1),
            "max_score": 10,
            "reasoning": f"{found_boundary}/{len(boundary_patterns)} boundary pattern bulundu",
            "missing": [p for p in boundary_patterns if p.lower() not in all_code.lower()][:5],
        })

        weighted_score = self._calc_weighted_score(dimensions)

        # Improvement önerileri oluştur
        improvements = []
        for dim in dimensions:
            if dim["score"] < 7 and dim.get("missing"):
                improvements.append({
                    "priority": "high" if dim["score"] < 5 else "medium",
                    "dimension": dim["name"],
                    "suggestion": f"{dim['name']} boyutunda eksik: {', '.join(dim['missing'][:3])}",
                })

        return {
            "dimensions": dimensions,
            "weighted_score": weighted_score,
            "summary": f"Heuristic değerlendirme: {weighted_score:.1f}/10",
            "improvements": improvements,
            "evaluation_method": "heuristic",
        }
