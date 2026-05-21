"""
CodeGeneratorAgent — Ajan 5

Görevi:
  - Otomasyon kararı "UI" veya "API" olan senaryolar için kod üretir
  - UI → Playwright (TypeScript) + BDD Gherkin
  - API → Karate DSL veya pytest
  - Modüler, reusable, CI/CD uyumlu

Model: qwen2.5-coder:7b (kod üretimi için en iyi model)
"""

from __future__ import annotations

from app.config import settings
from .base_agent import BaseAgent, AgentResult

SYSTEM_BDD = """\
Sen kıdemli bir Test Otomasyon Mühendisisin. Türkçe açıklamalar, İngilizce kod yaz.

## Kritik Kurallar
- PROJE BAĞLAMI'ndaki gerçek endpoint path'lerini, tablo isimlerini ve mevcut UI elemanlarını kullan
- Mevcut BDD feature dosyalarının STILINI ve TERMINOLOJISINI takip et
- Generic placeholder kullanma — gerçek URL, form alanı ve buton isimlerini kullan

## BDD Gherkin Formatı
- Feature dosyası başlığı açıklayıcı olsun
- Background: ortak ön koşullar (login, setup vb.)
- Scenario Outline: data-driven testler için
- Tags: @smoke, @regression, @P0, @banking, @kritik
- Given/When/Then/And/But kullan

## Çıktı Formatı
MUTLAKA aşağıdaki JSON formatında yanıt ver:
{
  "bdd_features": [
    {
      "scenario_id": "SCN-001",
      "feature_file": "dosya_adı.feature",
      "content": "Feature: ...\\n  Scenario: ...\\n  ..."
    }
  ]
}

## Örnek Çıktı
{
  "bdd_features": [{
    "scenario_id": "SCN-001",
    "feature_file": "login.feature",
    "content": "Feature: Kullanıcı Girişi\\n\\n  Background:\\n    Given API base URL 'http://localhost:8000' ayarlandı\\n\\n  @smoke @P0 @auth\\n  Scenario: Geçerli kimlik bilgileriyle giriş\\n    Given Kullanıcı login sayfasındadır\\n    When Email 'admin@test.com' ve şifre 'Admin123!' ile giriş yapar\\n    Then HTTP 200 yanıtı alır\\n    And Yanıtta geçerli JWT token bulunur"
  }]
}
"""

SYSTEM_PLAYWRIGHT = """\
Sen kıdemli bir Playwright Test Mühendisisin. TypeScript kullan.

## Kritik Kurallar
- PROJE BAĞLAMI'ndaki gerçek URL'leri ve sayfa yapısını referans al
- Mevcut E2E testlerin (.spec.ts) stilini ve import yapısını takip et
- Projedeki gerçek route'ları kullan (ör. /dashboard, /login, /scenarios)

## Teknik Kurallar
- Page Object Model (POM) kullan
- data-testid > role > aria-label > text sıralamasıyla seçici tercih et
- Her test bağımsız (beforeEach ile setup)
- expect() ile güçlü assertion'lar: toBeVisible, toHaveText, toContainText
- Async/await pattern
- Türkçe yorum satırları

## Çıktı Formatı
MUTLAKA aşağıdaki JSON formatında yanıt ver:
{
  "playwright_tests": [
    {
      "scenario_id": "SCN-001",
      "file_path": "e2e/tests/dosya.spec.ts",
      "content": "import { test, expect } from '@playwright/test';\\n..."
    }
  ]
}

## Örnek Çıktı
{
  "playwright_tests": [{
    "scenario_id": "SCN-001",
    "file_path": "e2e/tests/login.spec.ts",
    "content": "import { test, expect } from '@playwright/test';\\n\\ntest.describe('Login Sayfası', () => {\\n  test.beforeEach(async ({ page }) => {\\n    await page.goto('/login');\\n  });\\n\\n  // Başarılı giriş testi\\n  test('geçerli kimlik ile giriş yapabilmeli', async ({ page }) => {\\n    await page.getByTestId('email-input').fill('admin@test.com');\\n    await page.getByTestId('password-input').fill('Admin123!');\\n    await page.getByRole('button', { name: 'Giriş' }).click();\\n    await expect(page).toHaveURL('/dashboard');\\n    await expect(page.getByTestId('user-menu')).toBeVisible();\\n  });\\n});"
  }]
}
"""

SYSTEM_API = """\
Sen kıdemli bir API Test Mühendisisin.

## Kritik Kurallar
- PROJE BAĞLAMI'ndaki gerçek API endpoint'lerini kullan (ör. GET /api/v1/tspm/scenarios)
- Projenin authentication mekanizmasını (JWT Bearer token) kullan
- Response schema'larını projedeki gerçek modellere göre doğrula

## Teknik Kurallar
- pytest + httpx formatında yaz
- Fixture'larla authentication ve base_url ayarla
- Her test bağımsız
- Assert + soft assert — status code + response body + schema validation
- Türkçe yorum satırları

## Çıktı Formatı
MUTLAKA aşağıdaki JSON formatında yanıt ver:
{
  "api_tests": [
    {
      "scenario_id": "SCN-001",
      "file_path": "api-tests/test_dosya.py",
      "content": "import pytest\\nimport httpx\\n..."
    }
  ]
}
"""


class CodeGeneratorAgent(BaseAgent):
    name = "Kod Üretici"
    temperature = 0.2
    max_tokens = 6000
    model_fallback = ["mistral:latest", "qwen2.5:32b"]

    @property
    def model(self) -> str:  # type: ignore[override]
        return (
            settings.ollama_model_coder
            if settings.ai_provider == "ollama"
            else settings.openai_model
        )

    def run(self, context: dict) -> AgentResult:
        """
        context keys:
          automation_matrix — AutomationDecisionAgent çıktısı
          scenarios         — Senaryo detayları
          description       — Sistem açıklaması
          generate          — ["bdd", "playwright", "api"] hangilerini üretecek
        """
        matrix = context.get("automation_matrix", [])
        scenarios_map = {
            s.get("id", ""): s
            for s in context.get("scenarios", [])
        }
        desc = context.get("description", "Bankacılık sistemi")
        generate = context.get("generate", ["bdd", "playwright", "api"])

        # UI ve API senaryolarını ayır
        ui_items = [m for m in matrix if "UI" in m.get("decision", "")][:8]
        api_items = [m for m in matrix if "API" in m.get("decision", "") and "UI" not in m.get("decision", "")][:8]

        output: dict = {
            "bdd_features": [],
            "playwright_tests": [],
            "api_tests": [],
            "generated_count": 0,
        }

        # ── BDD Gherkin ───────────────────────────────────────────────
        if "bdd" in generate and ui_items:
            bdd_scenarios = []
            for item in ui_items[:5]:
                sid = item.get("scenario_id", "")
                scn = scenarios_map.get(sid, {})
                steps_text = "\n".join([
                    f"  {step.get('action', '')}"
                    for step in scn.get("steps", [])
                ])
                bdd_scenarios.append(
                    f"Senaryo {sid}: {item.get('scenario_title', '')}\\n"
                    f"Tip: {scn.get('type', 'positive')}\\n"
                    f"Adımlar:\\n{steps_text}"
                )

            bdd_prompt = (
                f"Sistem: {desc}\\n\\nBu senaryolar için BDD Gherkin feature dosyaları üret:\\n\\n"
                + "\\n---\\n".join(bdd_scenarios)
            )
            bdd_result = self.call_json(SYSTEM_BDD, bdd_prompt)
            output["bdd_features"] = bdd_result.get("bdd_features", [])

        # ── Playwright ────────────────────────────────────────────────
        if "playwright" in generate and ui_items:
            pw_scenarios = []
            for item in ui_items[:4]:
                sid = item.get("scenario_id", "")
                scn = scenarios_map.get(sid, {})
                pw_scenarios.append(
                    f"Senaryo: {item.get('scenario_title', '')} ({sid})\\n"
                    f"Ön koşullar: {', '.join(scn.get('preconditions', []))}\\n"
                    f"Beklenen sonuç: {scn.get('expected_result', '')}"
                )

            pw_prompt = (
                f"Sistem: {desc}\\n\\nBu senaryolar için Playwright TypeScript testleri yaz:\\n\\n"
                + "\\n---\\n".join(pw_scenarios)
            )
            pw_result = self.call_json(SYSTEM_PLAYWRIGHT, pw_prompt)
            output["playwright_tests"] = pw_result.get("playwright_tests", [])

        # ── API Tests ─────────────────────────────────────────────────
        if "api" in generate and api_items:
            api_scenarios = []
            for item in api_items[:4]:
                sid = item.get("scenario_id", "")
                scn = scenarios_map.get(sid, {})
                api_scenarios.append(
                    f"Senaryo: {item.get('scenario_title', '')} ({sid})\\n"
                    f"Beklenen sonuç: {scn.get('expected_result', '')}"
                )

            api_prompt = (
                f"Sistem: {desc}\\n\\nBu API senaryoları için pytest testleri yaz:\\n\\n"
                + "\\n---\\n".join(api_scenarios)
            )
            api_result = self.call_json(SYSTEM_API, api_prompt)
            output["api_tests"] = api_result.get("api_tests", [])

        output["generated_count"] = (
            len(output["bdd_features"])
            + len(output["playwright_tests"])
            + len(output["api_tests"])
        )

        self.learn(
            f"Kod Üretimi: {output['generated_count']} dosya üretildi. "
            f"BDD={len(output['bdd_features'])}, "
            f"Playwright={len(output['playwright_tests'])}, "
            f"API={len(output['api_tests'])}",
            metadata={"system": desc},
        )

        return AgentResult(
            agent_name=self.name,
            success=True,
            data=output,
        )
