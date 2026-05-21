/**
 * Unified Self-Healing Service
 *
 * Consolidates 3 separate healing mechanisms into one:
 *   1. e2e/helpers/self-healing-locator.ts (strategy chain)
 *   2. e2e/utils/self-healer.ts (afterEach hook)
 *   3. engine/core/self_healing/healer.py (6-category engine)
 *
 * 8-layer fallback chain:
 *   P0: data-testid (confidence 0.95)
 *   P1: ARIA role + name (0.90)
 *   P2: label (0.85)
 *   P3: placeholder (0.80)
 *   P4: text (0.70)
 *   P5: AI/LLM DOM analysis (0.60)
 *   P6: CSS fallback (0.40)
 *   P7: XPath (last resort) (0.20)
 */
import { type Page, type Locator } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const ENGINE_URL = process.env.ENGINE_BASE || "http://127.0.0.1:5001";
const HEALING_ENABLED = process.env.ENABLE_SELF_HEALING !== "false";
const HEALING_LOG_PATH = path.join("reports", "bdd", "healing-log.json");
const FETCH_TIMEOUT_MS = 10_000;

export interface HealingResult {
  healed: boolean;
  oldLocator: string;
  newLocator: string;
  strategy: string;
  confidence: number;
  summary: string;
  category: HealingCategory;
  durationMs: number;
}

export type HealingCategory =
  | "selector"
  | "timing"
  | "runtime"
  | "test_data"
  | "visual"
  | "flow_change"
  | "none";

interface LocatorCandidate {
  strategy: string;
  selector: string;
  confidence: number;
}

interface HealingRecord {
  testName: string;
  timestamp: string;
  result: HealingResult;
}

export class SelfHealingService {
  private history: HealingRecord[] = [];

  constructor(private page: Page) {}

  /**
   * Find an element using the 8-layer fallback chain.
   * Tries each strategy in order of confidence.
   */
  async findElement(
    elementId: string,
    options?: {
      role?: string;
      label?: string;
      placeholder?: string;
      text?: string;
      css?: string;
      xpath?: string;
    },
  ): Promise<Locator> {
    const candidates = this.buildCandidates(elementId, options);

    for (const candidate of candidates) {
      try {
        const locator = this.resolveLocator(candidate);
        if ((await locator.count()) > 0) {
          await locator.first().waitFor({ state: "visible", timeout: 3000 });
          return locator.first();
        }
      } catch {
        continue;
      }
    }

    if (HEALING_ENABLED) {
      const healed = await this.tryAIHeal(elementId, candidates[0]?.selector);
      if (healed) return healed;
    }

    throw new Error(
      `[SelfHealingService] Element not found: "${elementId}" - all 8 strategies failed`,
    );
  }

  /**
   * Attempt to heal a failed test by analyzing the error and page state.
   * Called automatically from After hook on test failure.
   */
  async attemptHeal(testName: string): Promise<HealingResult> {
    const start = Date.now();
    const noHeal: HealingResult = {
      healed: false,
      oldLocator: "",
      newLocator: "",
      strategy: "none",
      confidence: 0,
      summary: "",
      category: "none",
      durationMs: 0,
    };

    if (!HEALING_ENABLED) return noHeal;

    try {
      const snapshot = await this.page.accessibility.snapshot();
      if (!snapshot) return noHeal;

      const resp = await this.fetchWithTimeout(
        `${ENGINE_URL}/api/ai/self-heal`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            accessibility_tree: JSON.stringify(snapshot).slice(0, 8000),
            page_url: this.page.url(),
            test_name: testName,
          }),
        },
      );

      if (!resp || !resp.ok) return noHeal;

      const data = await resp.json();
      if (data.healed && data.new_locator) {
        const loc = this.page.locator(data.new_locator);
        if ((await loc.count()) > 0) {
          const result: HealingResult = {
            healed: true,
            oldLocator: data.failed_locator || "",
            newLocator: data.new_locator,
            strategy: data.strategy || "llm",
            confidence: data.confidence || 0.6,
            summary: `${data.failed_locator || "?"} -> ${data.new_locator}`,
            category: this.classifyError(data.error_type),
            durationMs: Date.now() - start,
          };
          this.recordHealing(testName, result);
          return result;
        }
      }
    } catch {
      // Engine unreachable
    }

    return { ...noHeal, durationMs: Date.now() - start };
  }

  /**
   * Get healing statistics for reporting.
   */
  getStats(): {
    total: number;
    healed: number;
    healRate: number;
    byStrategy: Record<string, number>;
    byCategory: Record<string, number>;
  } {
    const total = this.history.length;
    const healed = this.history.filter((h) => h.result.healed).length;
    const byStrategy: Record<string, number> = {};
    const byCategory: Record<string, number> = {};

    for (const h of this.history) {
      const s = h.result.strategy;
      const c = h.result.category;
      byStrategy[s] = (byStrategy[s] || 0) + 1;
      byCategory[c] = (byCategory[c] || 0) + 1;
    }

    return {
      total,
      healed,
      healRate: total > 0 ? Math.round((healed / total) * 100) : 0,
      byStrategy,
      byCategory,
    };
  }

  private buildCandidates(
    elementId: string,
    options?: {
      role?: string;
      label?: string;
      placeholder?: string;
      text?: string;
      css?: string;
      xpath?: string;
    },
  ): LocatorCandidate[] {
    const candidates: LocatorCandidate[] = [
      { strategy: "data-testid", selector: elementId, confidence: 0.95 },
    ];

    if (options?.role) {
      candidates.push({
        strategy: "role",
        selector: `${options.role}:${elementId.replace(/-/g, " ")}`,
        confidence: 0.9,
      });
    }
    if (options?.label) {
      candidates.push({
        strategy: "label",
        selector: options.label,
        confidence: 0.85,
      });
    }
    if (options?.placeholder) {
      candidates.push({
        strategy: "placeholder",
        selector: options.placeholder,
        confidence: 0.8,
      });
    }
    if (options?.text) {
      candidates.push({
        strategy: "text",
        selector: options.text,
        confidence: 0.7,
      });
    }
    if (options?.css) {
      candidates.push({
        strategy: "css",
        selector: options.css,
        confidence: 0.4,
      });
    }
    if (options?.xpath) {
      candidates.push({
        strategy: "xpath",
        selector: options.xpath,
        confidence: 0.2,
      });
    }

    return candidates.sort((a, b) => b.confidence - a.confidence);
  }

  private resolveLocator(candidate: LocatorCandidate): Locator {
    switch (candidate.strategy) {
      case "data-testid":
        return this.page.getByTestId(candidate.selector);
      case "role": {
        const [role, name] = candidate.selector.split(":");
        return this.page.getByRole(role as any, { name });
      }
      case "label":
        return this.page.getByLabel(candidate.selector);
      case "placeholder":
        return this.page.getByPlaceholder(candidate.selector);
      case "text":
        return this.page.getByText(candidate.selector);
      case "css":
        return this.page.locator(candidate.selector);
      case "xpath":
        return this.page.locator(candidate.selector);
      default:
        return this.page.locator(candidate.selector);
    }
  }

  private async tryAIHeal(
    elementId: string,
    originalSelector?: string,
  ): Promise<Locator | null> {
    const autoStrategies = [
      () => this.page.locator(`[data-testid*="${elementId}"]`),
      () => this.page.locator(`[aria-label*="${elementId}"]`),
      () => this.page.getByText(elementId.replace(/-/g, " ")),
    ];

    for (const strategy of autoStrategies) {
      try {
        const loc = strategy();
        if ((await loc.count()) === 1) return loc.first();
      } catch {
        continue;
      }
    }

    try {
      const snapshot = await this.page.accessibility.snapshot();
      if (!snapshot) return null;

      const resp = await this.fetchWithTimeout(
        `${ENGINE_URL}/api/ai/find-element`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            accessibility_tree: JSON.stringify(snapshot),
            element_intent: elementId,
            original_selector: originalSelector,
          }),
        },
      );

      if (!resp || !resp.ok) return null;
      const data = await resp.json();
      if (data.locator) {
        const loc = this.page.locator(data.locator);
        if ((await loc.count()) > 0) return loc.first();
      }
    } catch {
      // AI service unavailable
    }

    return null;
  }

  private classifyError(errorType?: string): HealingCategory {
    if (!errorType) return "selector";
    const map: Record<string, HealingCategory> = {
      selector: "selector",
      timeout: "timing",
      runtime: "runtime",
      test_data: "test_data",
      visual: "visual",
      flow_change: "flow_change",
    };
    return map[errorType] || "selector";
  }

  private recordHealing(testName: string, result: HealingResult): void {
    const record: HealingRecord = {
      testName,
      timestamp: new Date().toISOString(),
      result,
    };
    this.history.push(record);

    try {
      const dir = path.dirname(HEALING_LOG_PATH);
      fs.mkdirSync(dir, { recursive: true });

      let existing: HealingRecord[] = [];
      if (fs.existsSync(HEALING_LOG_PATH)) {
        try {
          existing = JSON.parse(fs.readFileSync(HEALING_LOG_PATH, "utf-8"));
        } catch {
          existing = [];
        }
      }
      existing.push(record);
      fs.writeFileSync(HEALING_LOG_PATH, JSON.stringify(existing, null, 2));
    } catch {
      // disk write failure
    }
  }

  private async fetchWithTimeout(
    url: string,
    init: RequestInit,
  ): Promise<Response | null> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
      return await fetch(url, { ...init, signal: controller.signal });
    } catch {
      return null;
    } finally {
      clearTimeout(timeout);
    }
  }
}
