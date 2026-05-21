"""
BDDScenarioGenerator — Doğal dil gereksinimlerinden Gherkin senaryosu üretir.

Kaynaklar:
  - User Story / Jira ticket
  - Gereksinim dokümanı
  - Mevcut test kodu (reverse engineering)
  - API spesifikasyonu (OpenAPI)

Çıktılar:
  - .feature dosyaları (Gherkin)
  - Senaryo tag'leri (@smoke, @regression, @critical, @security)
  - Scenario Outline + Examples desteği
  - Edge case ve negatif senaryolar
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class BDDGenerationResult:
    feature_content: str
    scenario_count: int
    tags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source: str = ""


BDD_SYSTEM_PROMPT = """Sen bir BDD/Gherkin uzmanısın. Verilen gereksinimden
standart Gherkin feature dosyası üret.

KURALLAR:
1. SADECE AŞAĞIDAKİ DESTEKLENEN ADIMLARI KULLAN:
  Given kullanıcı ana sayfadadır
  Given kullanıcı "<path>" sayfasındadır
  When kullanıcı "<metin>" metnine tıklar
  When kullanıcı "<selector>" kutusuna "<değer>" yazar
  When kullanıcı arama kutusuna "<değer>" yazar
  When kullanıcı Enter tuşuna basar
  When kullanıcı "<ms>" milisaniye bekler
  When AI "<görev>" görevini gerçekleştirir
  Then sayfa başlığı "<metin>" içermelidir
  Then URL "<metin>" içermelidir
  Then "<selector>" elementi görünür olmalıdır
  Then en az 1 adım başarılı olmalıdır

2. Uygun tag'ler ekle: @smoke, @regression, @critical, @security, @negative, @edge-case
3. Background kullan (ortak setup)
4. Scenario Outline + Examples kullan (parametrik test)
5. Edge case ve negatif senaryoları da üret
6. SADECE feature text döndür. Markdown veya açıklama EKLEME.
"""

BDD_FROM_CODE_PROMPT = """Sen bir reverse-engineering BDD uzmanısın.
Verilen test kodunu analiz edip Gherkin feature dosyasına dönüştür.
Aynı kurallar geçerli (sadece desteklenen adımlar, tag'ler, Scenario Outline)."""

BDD_FROM_API_PROMPT = """Sen bir API test BDD uzmanısın.
Verilen OpenAPI/Swagger spesifikasyonundan API test senaryoları üret.
Her endpoint için happy path, error handling ve edge case senaryoları oluştur."""


class BDDScenarioGenerator:
    """Çoklu kaynaktan BDD senaryosu üretici."""

    def __init__(self, existing_steps: list[str] | None = None):
        from config.ai_config_loader import get_bdd_generator_config
        self._cfg = get_bdd_generator_config()
        self.existing_steps = existing_steps or []
        self.max_scenarios = self._cfg.get("max_scenarios_per_feature", 15)
        self.output_dir = self._cfg.get("output_dir", "features/generated")

    def from_requirement(
        self, requirement: str, feature_name: str = "Generated"
    ) -> BDDGenerationResult:
        """Doğal dil gereksiniminden Gherkin üret."""
        context = ""
        if self.existing_steps:
            context = "\n\nMevcut step definition'lar:\n" + "\n".join(
                self.existing_steps[:50]
            )

        content = self._call_ai(
            BDD_SYSTEM_PROMPT,
            f"Gereksinim: {requirement}\n\nFeature adı: {feature_name}{context}",
        )

        return self._build_result(content, source="requirement")

    def from_code(self, test_code: str) -> BDDGenerationResult:
        """Mevcut test kodundan Gherkin üret (reverse engineering)."""
        content = self._call_ai(
            BDD_FROM_CODE_PROMPT,
            f"Test Kodu:\n{test_code}",
        )
        return self._build_result(content, source="code")

    def from_api_spec(self, openapi_spec: str | dict) -> BDDGenerationResult:
        """OpenAPI spesifikasyonundan API BDD senaryoları üret."""
        spec_str = json.dumps(openapi_spec, indent=2) if isinstance(openapi_spec, dict) else openapi_spec
        content = self._call_ai(
            BDD_FROM_API_PROMPT,
            f"OpenAPI Spec:\n{spec_str[:8000]}",
        )
        return self._build_result(content, source="api_spec")

    def batch_generate(
        self, requirements: list[dict], output_dir: str | Path | None = None
    ) -> list[BDDGenerationResult]:
        """Birden fazla gereksinimden toplu senaryo üret."""
        results = []
        out = Path(output_dir) if output_dir else settings.FEATURES_DIR / "generated"
        out.mkdir(parents=True, exist_ok=True)

        for req in requirements:
            text = req.get("text", req.get("requirement", ""))
            name = req.get("name", req.get("feature_name", "feature"))
            result = self.from_requirement(text, feature_name=name)
            results.append(result)

            filename = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower()) + ".feature"
            (out / filename).write_text(result.feature_content, encoding="utf-8")
            logger.info("Generated: %s (%d scenarios)", filename, result.scenario_count)

        return results

    def _call_ai(self, system_prompt: str, user_prompt: str) -> str:
        from core.llm_bridge import call_llm

        content = call_llm(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return _clean_gherkin(content)

    def _build_result(self, content: str, source: str) -> BDDGenerationResult:
        scenario_count = content.lower().count("scenario")
        tags = list(set(re.findall(r"@\w+", content)))
        warnings = []
        if scenario_count == 0:
            warnings.append("No scenarios generated")
        if not tags:
            warnings.append("No tags found — consider adding @smoke/@regression")
        return BDDGenerationResult(
            feature_content=content,
            scenario_count=scenario_count,
            tags=tags,
            warnings=warnings,
            source=source,
        )


def _clean_gherkin(raw: str) -> str:
    """Markdown bloklarını temizle."""
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        raw = "\n".join(lines)
    return raw.strip()
