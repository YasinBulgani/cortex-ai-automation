import type { Page, Locator } from '@playwright/test';

export interface HealingRecord {
  original: string;
  healed: string;
  strategy: string;
  timestamp: string;
  url: string;
  confidence: number;
}

type FallbackStrategy = 'accessibility' | 'semantic' | 'structural';

export interface HealingConfig {
  maxRetries: number;
  cacheEnabled: boolean;
  cachePath: string;
  fallbackStrategies: FallbackStrategy[];
  confidenceThreshold: number;
}

const DEFAULT_CONFIG: HealingConfig = {
  maxRetries: 3,
  cacheEnabled: true,
  cachePath: './test-results/healing-cache.json',
  fallbackStrategies: ['accessibility', 'semantic', 'structural'],
  confidenceThreshold: 0.8,
};

export class SelfHealingEngine {
  private cache = new Map<string, string>();
  private log: HealingRecord[] = [];
  private config: HealingConfig;

  constructor(config: Partial<HealingConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  async heal(page: Page, selector: string, description: string): Promise<Locator> {
    // 1. Orijinal locator
    const original = page.locator(selector);
    if (await original.count().catch(() => 0) > 0) return original;

    // 2. Cache
    const key = `${page.url()}::${selector}`;
    const cached = this.cache.get(key);
    if (cached) {
      const loc = page.locator(cached);
      if (await loc.count().catch(() => 0) > 0) return loc;
    }

    // 3. Fallback strategies
    for (const strategy of this.config.fallbackStrategies) {
      const healed = await this.runStrategy(page, selector, description, strategy);
      if (healed) {
        this.record(selector, healed, strategy, page.url());
        if (this.config.cacheEnabled) this.cache.set(key, healed);
        return page.locator(healed);
      }
    }

    throw new Error(`Self-healing başarısız: "${selector}" (${description})`);
  }

  private async runStrategy(
    page: Page,
    selector: string,
    description: string,
    strategy: FallbackStrategy,
  ): Promise<string | null> {
    switch (strategy) {
      case 'accessibility':
        return this.healByAccessibility(page, description);
      case 'semantic':
        return this.healBySemantic(page, selector);
      case 'structural':
        return this.healByStructural(page, selector);
    }
  }

  private async healByAccessibility(page: Page, description: string): Promise<string | null> {
    const snapshot = await page.accessibility.snapshot().catch(() => null);
    if (!snapshot) return null;

    const match = this.searchTree(snapshot, description.toLowerCase());
    if (!match) return null;
    return `role=${match.role}[name="${match.name}"]`;
  }

  private async healBySemantic(page: Page, selector: string): Promise<string | null> {
    const m = selector.match(/data-testid="([^"]+)"/);
    if (!m) return null;

    const prefix = m[1].split('-').slice(0, 2).join('-');
    const candidates: string[] = await page.evaluate((p: string) => {
      return Array.from(document.querySelectorAll(`[data-testid*="${p}"]`))
        .map(el => el.getAttribute('data-testid')!)
        .filter(Boolean);
    }, prefix);

    return candidates.length > 0 ? `[data-testid="${candidates[0]}"]` : null;
  }

  private async healByStructural(page: Page, selector: string): Promise<string | null> {
    // Placeholder — burada DOM proximity / sibling analizi yapılabilir
    return null;
  }

  private searchTree(node: any, text: string): { role: string; name: string } | null {
    if (node.name?.toLowerCase().includes(text)) return node;
    for (const child of node.children ?? []) {
      const found = this.searchTree(child, text);
      if (found) return found;
    }
    return null;
  }

  private record(original: string, healed: string, strategy: string, url: string) {
    this.log.push({
      original,
      healed,
      strategy,
      timestamp: new Date().toISOString(),
      url,
      confidence: strategy === 'accessibility' ? 0.95 : strategy === 'semantic' ? 0.85 : 0.7,
    });
  }

  getHealingLog(): readonly HealingRecord[] {
    return this.log;
  }

  getCacheSize(): number {
    return this.cache.size;
  }
}
