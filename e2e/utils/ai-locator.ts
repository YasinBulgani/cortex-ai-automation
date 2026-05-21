/**
 * AI destekli locator fallback chain.
 *
 * data-testid → role → label → text → AI-generated → CSS
 * sırasıyla dener, ilk eşleşeni döndürür.
 */
import { type Page, type Locator } from "@playwright/test";

export interface LocatorResult {
  locator: Locator;
  strategy: "testId" | "role" | "label" | "text" | "ai-generated" | "css";
  confidence: number;
}

const FETCH_TIMEOUT_MS = 10_000;

function getEngineBase(): string {
  return process.env.ENGINE_BASE || "http://127.0.0.1:5001";
}

/**
 * Verilen intent'e göre en güvenilir locator'ı bulur.
 * 6 stratejiyi sırasıyla dener.
 */
export async function findElement(
  page: Page,
  intent: string,
  options?: { role?: string; fallbackCss?: string },
): Promise<LocatorResult> {
  // 1) data-testid
  const byTestId = page.getByTestId(intent);
  if ((await byTestId.count()) > 0) {
    return { locator: byTestId, strategy: "testId", confidence: 1.0 };
  }

  // 2) ARIA role
  if (options?.role) {
    const byRole = page.getByRole(options.role as any, { name: intent });
    if ((await byRole.count()) > 0) {
      return { locator: byRole, strategy: "role", confidence: 0.9 };
    }
  }

  // 3) Label
  const byLabel = page.getByLabel(intent);
  if ((await byLabel.count()) > 0) {
    return { locator: byLabel, strategy: "label", confidence: 0.85 };
  }

  // 4) Benzersiz metin
  const byText = page.getByText(intent, { exact: false });
  if ((await byText.count()) === 1) {
    return { locator: byText, strategy: "text", confidence: 0.7 };
  }

  // 5) AI fallback — accessibility snapshot + Engine LLM
  if (process.env.ENABLE_SELF_HEALING !== "false") {
    try {
      const snapshot = await page.accessibility.snapshot();
      if (snapshot) {
        const aiLocator = await llmFindElement(snapshot, intent);
        if (aiLocator) {
          const byAi = page.locator(aiLocator);
          if ((await byAi.count()) > 0) {
            return { locator: byAi, strategy: "ai-generated", confidence: 0.6 };
          }
        }
      }
    } catch {
      // AI fallback başarısız — CSS'e düş
    }
  }

  // 6) CSS fallback
  if (options?.fallbackCss) {
    return {
      locator: page.locator(options.fallbackCss),
      strategy: "css",
      confidence: 0.4,
    };
  }

  throw new Error(
    `Element bulunamadı: "${intent}" — tüm stratejiler başarısız`,
  );
}

async function llmFindElement(
  snapshot: unknown,
  intent: string,
): Promise<string | null> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const resp = await fetch(`${getEngineBase()}/api/ai/find-element`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        accessibility_tree: JSON.stringify(snapshot),
        element_intent: intent,
      }),
      signal: controller.signal,
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    return data.locator || null;
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}
