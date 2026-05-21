/**
 * Built-in prompt library — Neurex'in core promptları.
 *
 * Yeni prompt eklerken:
 *   1. Burada export edin
 *   2. Versionu artırın (semver)
 *   3. evals/{prompt_id}.yaml içine test case ekleyin
 */

import type { PromptTemplate } from "./registry";

// ─── Senaryo üretimi ────────────────────────────────────────────────────

export const generateBddScenario: PromptTemplate<{
  project_name: string;
  requirement: string;
  domain_context: string;
}> = {
  id: "scenario.generate-bdd",
  version: "1.0.0",
  description: "Gereksinimden BDD/Gherkin formatında senaryo üret",
  recommended_tier: "premium",
  max_output_tokens: 1500,
  template: `Sen deneyimli bir QA mühendisisin. Aşağıdaki gereksinimden, Türkçe Gherkin (Given-When-Then) formatında 3 senaryo üret.

Proje: {{ project_name }}
Bağlam: {{ domain_context }}
Gereksinim: {{ requirement }}

Çıktı kuralları:
- Happy path, negative case, edge case dahil 3 senaryo
- Her step kısa ve action-odaklı
- Test data placeholder kullan (gerçek PII koyma)

Gherkin:`,
  variables: ["project_name", "requirement", "domain_context"],
};

// ─── Test analizi ──────────────────────────────────────────────────────

export const analyzeTestFailure: PromptTemplate<{
  test_name: string;
  error_message: string;
  stack_trace: string;
  recent_changes: string;
}> = {
  id: "analysis.test-failure",
  version: "1.0.0",
  description: "Test başarısızlığını analiz et, kök nedeni bul",
  recommended_tier: "premium",
  max_output_tokens: 1000,
  template: `Bu test başarısızlığı için kök neden analizi yap.

Test: {{ test_name }}

Hata mesajı:
\`\`\`
{{ error_message }}
\`\`\`

Stack trace:
\`\`\`
{{ stack_trace }}
\`\`\`

Son kod değişiklikleri:
{{ recent_changes }}

Analiz formatı (JSON):
{
  "root_cause": "kısa açıklama",
  "confidence": 0.0-1.0,
  "likely_files": ["dosya/yol.ts"],
  "fix_suggestion": "öneri",
  "is_flaky": true|false
}`,
  variables: ["test_name", "error_message", "stack_trace", "recent_changes"],
};

// ─── Locator iyileştirme ───────────────────────────────────────────────

export const healLocator: PromptTemplate<{
  broken_locator: string;
  page_url: string;
  dom_snippet: string;
}> = {
  id: "automation.heal-locator",
  version: "1.0.0",
  description: "Kırılmış locator için 3 alternatif öner",
  recommended_tier: "balanced",
  max_output_tokens: 500,
  template: `Bu locator artık çalışmıyor. DOM'a bakıp 3 alternatif öner.

Eski locator: {{ broken_locator }}
Sayfa: {{ page_url }}
Mevcut DOM:
\`\`\`html
{{ dom_snippet }}
\`\`\`

Öncelik: data-testid > role+text > stable id > XPath
JSON:
[
  { "locator": "...", "strategy": "role-text", "confidence": 0.95 },
  ...
]`,
  variables: ["broken_locator", "page_url", "dom_snippet"],
};

// ─── Yardımcı: tümünü registry'e kaydet ────────────────────────────────

import { defaultRegistry } from "./registry";

export function registerBuiltinPrompts(): void {
  defaultRegistry.register(generateBddScenario);
  defaultRegistry.register(analyzeTestFailure);
  defaultRegistry.register(healLocator);
}
