/**
 * Prompt Injection Detection — bilinen jailbreak/role-bypass kalıpları.
 *
 * NOT: Bu heuristic baseline; production'da ML model (rebuff, Lakera vb.)
 * tercih edilebilir. Skor 0..1 — yüksek = injection olasılığı yüksek.
 */

interface InjectionPattern {
  name: string;
  regex: RegExp;
  weight: number; // 0..1
}

const PATTERNS: InjectionPattern[] = [
  // Klasik "ignore previous"
  { name: "ignore_previous", regex: /ignore\s+(all\s+|the\s+)?(previous|above|prior|earlier)\s+(instruction|prompt|message|rule)s?/i, weight: 0.9 },
  { name: "ignore_previous_tr", regex: /(önceki|yukarıdaki|tüm)\s+(talimat|kural|mesaj|prompt)(lar)?(ı)?\s+(görmezden gel|yok say|unut)/i, weight: 0.9 },
  // Role bypass
  { name: "new_role", regex: /(you|sen)\s+(are|artık|are now)\s+(now\s+)?(a|bir)?\s*(developer|admin|root|jailbroken|dan|sudo)/i, weight: 0.85 },
  { name: "dan_jailbreak", regex: /\b(do\s+anything\s+now|dan\s+mode|developer\s+mode\s+enabled)\b/i, weight: 0.95 },
  // System prompt extraction
  { name: "system_prompt_leak", regex: /(reveal|show|print|tell\s+me)\s+(your|the)\s+(system|initial|original)\s+(prompt|instructions?|message)/i, weight: 0.8 },
  { name: "system_prompt_leak_tr", regex: /(sistem|initial|orijinal)\s+(prompt|talimat|mesaj)(ı|ini|ını|ları|larını)?\s+(göster|söyle|açıkla|yaz|ver)/i, weight: 0.8 },
  // Instruction injection via "actually"
  { name: "actually_override", regex: /^(actually|aslında|wait,?\s+)/i, weight: 0.2 },
  // Markdown/code block escape
  { name: "code_fence_inject", regex: /```\s*\n?(system|assistant|user):/i, weight: 0.7 },
  // Token-bypass tries
  { name: "base64_exec", regex: /(decode|run|execute)\s+(this\s+)?(base64|encoded)/i, weight: 0.6 },
  // Direct file/url request
  { name: "file_exfil", regex: /(read|cat|show)\s+(\/etc\/passwd|\.env|secrets?|credentials?)/i, weight: 0.95 },
];

export interface InjectionResult {
  is_injection: boolean;
  score: number; // 0..1
  matched_patterns: string[];
}

const DEFAULT_THRESHOLD = 0.5;

export function detectInjection(text: string, threshold = DEFAULT_THRESHOLD): InjectionResult {
  let score = 0;
  const matched: string[] = [];

  for (const { name, regex, weight } of PATTERNS) {
    if (regex.test(text)) {
      // Diminishing returns — ardışık match'ler aynı kategoride az ekler
      score = score + weight * (1 - score);
      matched.push(name);
    }
  }

  return {
    is_injection: score >= threshold,
    score: Math.min(1, score),
    matched_patterns: matched,
  };
}
