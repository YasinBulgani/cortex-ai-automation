export interface AssertionSuggestion {
  line: number;
  suggestion: string;
  reason: string;
  confidence: 'high' | 'medium' | 'low';
  category: 'missing' | 'weak' | 'incomplete';
}

/**
 * Regex-based lightweight assertion analyzer.
 * Daha derin analiz için AST parser (ts-morph) kullanılabilir.
 */
export class AssertionAdvisor {
  analyze(sourceCode: string, filePath: string): AssertionSuggestion[] {
    const lines = sourceCode.split('\n');
    const suggestions: AssertionSuggestion[] = [];
    const testBlocks = this.findTestBlocks(lines);

    for (const block of testBlocks) {
      const body = block.lines.join('\n');
      const actions = (body.match(/\.(click|fill|check|press|selectOption|type|dblclick|hover)\(/g) ?? []).length;
      const asserts = (body.match(/(expect|assert|should|toHave|toBe|toContain|toBeVisible|toBeHidden)/g) ?? []).length;

      if (actions > 0 && asserts === 0) {
        suggestions.push({
          line: block.startLine,
          suggestion: 'Bu test bloğunda assertion yok — en az bir expect() ekleyin',
          reason: 'Assertion olmadan test her koşulda geçer',
          confidence: 'high',
          category: 'missing',
        });
      }

      if (/\.goto\(|\.click\(.*link|\.click\(.*nav/i.test(body) && !/toHaveURL/.test(body)) {
        suggestions.push({
          line: block.startLine,
          suggestion: 'Navigation sonrası URL doğrulaması ekleyin: await expect(page).toHaveURL(...)',
          reason: 'Sayfa geçişi sonrası hedef URL kontrol edilmiyor',
          confidence: 'high',
          category: 'missing',
        });
      }

      if (/submit|kaydet|gönder|save/i.test(body) && !/toBeVisible|toContainText|toHaveText/.test(body)) {
        suggestions.push({
          line: block.startLine,
          suggestion: 'Form submit sonrası başarı/hata mesajı kontrolü ekleyin',
          reason: 'Submit sonrası kullanıcı geri bildirimi doğrulanmıyor',
          confidence: 'medium',
          category: 'incomplete',
        });
      }

      if (actions > 3 && asserts < 2) {
        suggestions.push({
          line: block.startLine,
          suggestion: `${actions} aksiyon var ama sadece ${asserts} assertion — ara doğrulamalar ekleyin`,
          reason: 'Aksiyonlar arasında ara durum doğrulaması güvenilirliği artırır',
          confidence: 'medium',
          category: 'weak',
        });
      }
    }

    return suggestions;
  }

  private findTestBlocks(lines: string[]): Array<{ startLine: number; lines: string[] }> {
    const blocks: Array<{ startLine: number; lines: string[] }> = [];
    let current: { startLine: number; lines: string[] } | null = null;
    let depth = 0;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (/\btest\s*\(|it\s*\(/.test(line) && !current) {
        current = { startLine: i + 1, lines: [] };
        depth = 0;
      }

      if (current) {
        current.lines.push(line);
        depth += (line.match(/{/g) ?? []).length;
        depth -= (line.match(/}/g) ?? []).length;

        if (depth <= 0 && current.lines.length > 1) {
          blocks.push(current);
          current = null;
        }
      }
    }

    if (current) blocks.push(current);
    return blocks;
  }
}
