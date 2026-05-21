const PII_PATTERNS: ReadonlyMap<string, RegExp> = new Map([
  ['tc_kimlik', /\b[1-9]\d{10}\b/g],
  ['email', /\b[\w.+-]+@[\w-]+\.[\w.]+\b/g],
  ['phone', /\b0?\d{3}\s?\d{3}\s?\d{2}\s?\d{2}\b/g],
  ['iban', /\bTR\d{24}\b/gi],
  ['credit_card', /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g],
  ['ip_address', /\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g],
]);

export class DataMasker {
  private auditLog: Array<{ timestamp: string; fieldsMasked: number; types: string[] }> = [];

  mask(text: string): string {
    let masked = text;
    const typesFound: string[] = [];

    for (const [type, pattern] of PII_PATTERNS) {
      const placeholder = `[MASKED_${type.toUpperCase()}]`;
      const before = masked;
      masked = masked.replace(pattern, placeholder);
      if (masked !== before) typesFound.push(type);
    }

    if (typesFound.length > 0) {
      this.auditLog.push({
        timestamp: new Date().toISOString(),
        fieldsMasked: typesFound.length,
        types: typesFound,
      });
    }

    return masked;
  }

  maskObject<T extends Record<string, unknown>>(obj: T): T {
    const result = {} as Record<string, unknown>;

    for (const [key, value] of Object.entries(obj)) {
      if (typeof value === 'string') {
        result[key] = this.mask(value);
      } else if (Array.isArray(value)) {
        result[key] = value.map(item =>
          typeof item === 'string'
            ? this.mask(item)
            : typeof item === 'object' && item !== null
              ? this.maskObject(item as Record<string, unknown>)
              : item,
        );
      } else if (typeof value === 'object' && value !== null) {
        result[key] = this.maskObject(value as Record<string, unknown>);
      } else {
        result[key] = value;
      }
    }

    return result as T;
  }

  containsSensitiveData(text: string): boolean {
    for (const [, pattern] of PII_PATTERNS) {
      pattern.lastIndex = 0;
      if (pattern.test(text)) return true;
    }
    return false;
  }

  getAuditLog() {
    return [...this.auditLog];
  }
}

export const dataMasker = new DataMasker();
