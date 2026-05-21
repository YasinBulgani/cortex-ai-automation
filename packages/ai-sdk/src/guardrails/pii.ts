/**
 * PII Redaction — Türkçe ve evrensel PII kalıplarını maskeler.
 *
 * Production'da Microsoft Presidio gibi tam ML-based çözüm tercih edilir,
 * burada hızlı + sıfır-dep regex baseline.
 */

export interface RedactionResult {
  redacted: string;
  matches: Array<{ type: string; original: string; replacement: string }>;
}

const PATTERNS: Array<{ type: string; regex: RegExp; replacement: string }> = [
  // Türkiye T.C. Kimlik No (11 hane, 1. hane ≠ 0)
  { type: "tckn", regex: /\b[1-9]\d{10}\b/g, replacement: "[TCKN]" },
  // IBAN (TR ve diğer) — basit format
  { type: "iban", regex: /\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b/g, replacement: "[IBAN]" },
  // Email
  { type: "email", regex: /\b[\w.+-]+@[\w-]+\.[\w.-]+\b/gi, replacement: "[EMAIL]" },
  // Türkiye GSM (+90 5XX XXX XX XX, 05XX XXX XX XX, vs.)
  { type: "phone_tr", regex: /\b(?:\+?90[\s-]?)?0?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b/g, replacement: "[PHONE]" },
  // Genel uluslararası telefon (e.164 light)
  { type: "phone", regex: /\b\+\d{1,3}[\s-]?\d{1,4}[\s-]?\d{1,4}[\s-]?\d{1,9}\b/g, replacement: "[PHONE]" },
  // Kredi kartı (luhn check yok, görsel format yeter)
  { type: "credit_card", regex: /\b(?:\d[ -]*?){13,19}\b/g, replacement: "[CARD]" },
  // IPv4
  { type: "ipv4", regex: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g, replacement: "[IP]" },
  // JWT (üç base64 segment, noktayla ayrılmış)
  { type: "jwt", regex: /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/g, replacement: "[JWT]" },
  // Anthropic API key
  { type: "api_key_anthropic", regex: /sk-ant-[A-Za-z0-9_-]{32,}/g, replacement: "[KEY]" },
  // OpenAI API key
  { type: "api_key_openai", regex: /sk-[A-Za-z0-9_-]{32,}/g, replacement: "[KEY]" },
  // AWS Access Key
  { type: "api_key_aws", regex: /\bAKIA[0-9A-Z]{16}\b/g, replacement: "[KEY]" },
];

export function redactPII(text: string): RedactionResult {
  let redacted = text;
  const matches: RedactionResult["matches"] = [];

  for (const { type, regex, replacement } of PATTERNS) {
    redacted = redacted.replace(regex, (match) => {
      matches.push({ type, original: match, replacement });
      return replacement;
    });
  }

  return { redacted, matches };
}

/**
 * Hızlı predicate — text içinde PII tespit edilip edilmediği.
 */
export function containsPII(text: string): boolean {
  return PATTERNS.some(({ regex }) => regex.test(text));
}
