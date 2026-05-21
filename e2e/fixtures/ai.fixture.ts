/**
 * AI-enhanced test fixtures.
 *
 * Mevcut base.ts fixture'ını genişleterek:
 * - afterEach self-healing hook (başarısız testleri Engine LLM ile onarma)
 * - AI locator helper (findElement 6-strateji zinciri)
 * - Healing log yazma
 */
import { test as base, expect, type Page, type Locator } from "@playwright/test";
import { findElement, type LocatorResult } from "../utils/ai-locator";
import { attemptHealing, type HealingResult } from "../utils/self-healer";
import {
  findWithHealing,
  createLocatorCandidates,
  getHealingHistory,
  clearHealingHistory,
  type LocatorCandidate,
} from "../helpers/self-healing-locator";

interface AIFixtures {
  aiFind: (intent: string, options?: { role?: string; fallbackCss?: string }) => Promise<LocatorResult>;
  selfHeal: {
    find(elementId: string, candidates: LocatorCandidate[]): Promise<Locator>;
    candidates: typeof createLocatorCandidates;
    history(): ReturnType<typeof getHealingHistory>;
  };
}

export const test = base.extend<AIFixtures>({
  aiFind: async ({ page }, use) => {
    const finder = (intent: string, options?: { role?: string; fallbackCss?: string }) =>
      findElement(page, intent, options);
    await use(finder);
  },

  selfHeal: async ({ page }, use) => {
    clearHealingHistory();
    const helper = {
      find: (elementId: string, candidates: LocatorCandidate[]) =>
        findWithHealing(page, elementId, candidates),
      candidates: createLocatorCandidates,
      history: getHealingHistory,
    };
    await use(helper);
  },
});

test.afterEach(async ({ page }, testInfo) => {
  if (testInfo.status !== "failed") return;
  if (process.env.ENABLE_SELF_HEALING === "false") return;

  const result = await attemptHealing(page, testInfo);
  if (result.healed) {
    testInfo.annotations.push({
      type: "healed",
      description: result.summary,
    });
  }
});

export { expect };
export type { LocatorCandidate };
