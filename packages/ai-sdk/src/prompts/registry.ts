/**
 * Prompt Registry — versionlanmış prompt template'leri.
 *
 * Faydalar:
 * - Promptlar kod (git'te), text dosyaları değil
 * - Versiyon kontrolü (semver)
 * - A/B test yapısı
 * - Per-tenant override
 * - Compile-time validation
 */

export interface PromptTemplate<TVars extends Record<string, string> = Record<string, string>> {
  id: string;
  version: string;        // semver
  description: string;
  template: string;       // {{ variable }} syntax
  variables: Array<keyof TVars>;
  /** Önerilen LLM tier */
  recommended_tier?: "fast" | "balanced" | "premium";
  /** Maksimum input token */
  max_input_tokens?: number;
  /** Maksimum çıktı token */
  max_output_tokens?: number;
}

/**
 * Template'i variable'larla render et.
 * Eksik variable → throw.
 */
export function renderPrompt<TVars extends Record<string, string>>(
  template: PromptTemplate<TVars>,
  variables: TVars,
): string {
  let result = template.template;
  for (const key of template.variables) {
    const value = variables[key];
    if (value === undefined) {
      throw new Error(`Missing variable '${String(key)}' for prompt ${template.id}@${template.version}`);
    }
    const pattern = new RegExp(`\\{\\{\\s*${String(key)}\\s*\\}\\}`, "g");
    result = result.replace(pattern, value);
  }
  // Check no unfilled {{ ... }} remains
  const unfilled = result.match(/\{\{[^}]+\}\}/);
  if (unfilled) {
    throw new Error(`Unfilled placeholder in prompt ${template.id}: ${unfilled[0]}`);
  }
  return result;
}

/**
 * Registry — tüm promptlar tek yerde, type-safe lookup.
 */
export class PromptRegistry {
  private prompts: Map<string, PromptTemplate> = new Map();

  register<T extends Record<string, string>>(prompt: PromptTemplate<T>): void {
    this.prompts.set(`${prompt.id}@${prompt.version}`, prompt as PromptTemplate);
    // Latest pointer
    this.prompts.set(prompt.id, prompt as PromptTemplate);
  }

  get(id: string, version?: string): PromptTemplate | undefined {
    return this.prompts.get(version ? `${id}@${version}` : id);
  }

  list(): PromptTemplate[] {
    const seen = new Set<string>();
    const out: PromptTemplate[] = [];
    for (const p of this.prompts.values()) {
      if (seen.has(p.id)) continue;
      seen.add(p.id);
      out.push(p);
    }
    return out;
  }
}

// Default registry (singleton)
export const defaultRegistry = new PromptRegistry();
