import { readFileSync } from 'node:fs';

export interface TestGenerationRequest {
  userStory: string;
  pageObjects: string[];
  existingTests?: string[];
  language?: 'tr' | 'en';
}

export interface GeneratedTest {
  filename: string;
  content: string;
  scenarios: string[];
}

const PROJECT_CONTEXT = `
Proje: BGTS Test Dönüşüm
Framework: Playwright + TypeScript
Pattern: Page Object Model (BasePage extend)
Locator: data-testid convention — {screen}-{element-type}-{identifier}
Fixture: e2e/fixtures/pages.fixture.ts
`;

/**
 * LLM'e gönderilecek prompt'u oluşturur.
 * Gerçek API çağrısı ayrı bir orkestratör tarafından yapılır.
 */
export function buildTestGenerationPrompt(req: TestGenerationRequest): string {
  const pageObjectSnippets = req.pageObjects.map(p => {
    try {
      return `### ${p}\n\`\`\`typescript\n${readFileSync(p, 'utf-8')}\n\`\`\``;
    } catch {
      return `### ${p}\n(dosya okunamadı)`;
    }
  });

  return `
${PROJECT_CONTEXT}

## Mevcut Page Object'ler:
${pageObjectSnippets.join('\n\n')}

## User Story:
${req.userStory}

## Görev:
Bu user story için Playwright test dosyası üret.
- BasePage pattern'ini kullan
- data-testid convention'a uy: {screen}-{element-type}-{identifier}
- Her senaryo için ayrı test('...') bloğu yaz
- Assertion'lar expect ile
- Mevcut page object'lerdeki metotları kullan
- Edge case'leri de kapsa (boş form, geçersiz veri, sınır değerler)
- ${req.language === 'en' ? 'Write in English' : 'Türkçe test isimleri kullan'}

Sadece TypeScript kodu üret, açıklama yazma.
`.trim();
}

export function parseGeneratedTest(code: string, baseName: string): GeneratedTest {
  const scenarios = (code.match(/test\(\s*['"`](.+?)['"`]/g) ?? [])
    .map(s => s.replace(/test\(\s*['"`]|['"`]/g, ''));

  return {
    filename: `${baseName}.spec.ts`,
    content: code,
    scenarios,
  };
}
