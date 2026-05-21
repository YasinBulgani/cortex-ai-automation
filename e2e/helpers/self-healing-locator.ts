/**
 * SelfHealingLocator — Playwright E2E testleri için self-healing locator desteği.
 *
 * Strateji sırası:
 *  1. data-testid (P0)
 *  2. getByRole + name (P1)
 *  3. getByLabel (P2)
 *  4. getByPlaceholder (P3)
 *  5. getByText (P4)
 *  6. CSS fallback (P5)
 *  7. Backend AI heal (son çare)
 */
import { Page, Locator } from '@playwright/test';

export interface LocatorCandidate {
  strategy: string;
  selector: string;
  confidence: number;
}

interface HealingLog {
  elementId: string;
  originalSelector: string;
  healedSelector: string;
  strategy: string;
  timestamp: number;
}

const healingHistory: HealingLog[] = [];
const ENGINE_URL = process.env.ENGINE_BASE || process.env.ENGINE_URL || 'http://127.0.0.1:5001';
const SELF_HEALING_ENABLED = process.env.ENABLE_SELF_HEALING !== 'false';

export async function findWithHealing(
  page: Page,
  elementId: string,
  candidates: LocatorCandidate[],
): Promise<Locator> {
  const sorted = [...candidates].sort((a, b) => b.confidence - a.confidence);

  for (const candidate of sorted) {
    try {
      const locator = resolveLocator(page, candidate);
      const count = await locator.count();
      if (count > 0) {
        await locator.first().waitFor({ state: 'visible', timeout: 3000 });
        return locator.first();
      }
    } catch {
      continue;
    }
  }

  const autoHealed = await tryAutoHeal(page, elementId, sorted[0]?.selector || '');
  if (autoHealed) {
    return autoHealed;
  }

  if (SELF_HEALING_ENABLED) {
    const backendResult = await tryBackendHeal(page, elementId, sorted[0]?.selector || '');
    if (backendResult) {
      return backendResult;
    }
  }

  throw new Error(`Self-healing failed for element: ${elementId}`);
}

function resolveLocator(page: Page, candidate: LocatorCandidate): Locator {
  switch (candidate.strategy) {
    case 'data-testid':
      return page.locator(`[data-testid="${candidate.selector}"]`);
    case 'role':
      return page.getByRole(candidate.selector.split(':')[0] as any, {
        name: candidate.selector.split(':')[1],
      });
    case 'label':
      return page.getByLabel(candidate.selector);
    case 'placeholder':
      return page.getByPlaceholder(candidate.selector);
    case 'text':
      return page.getByText(candidate.selector);
    case 'css':
      return page.locator(candidate.selector);
    default:
      return page.locator(candidate.selector);
  }
}

async function tryAutoHeal(
  page: Page,
  elementId: string,
  originalSelector: string,
): Promise<Locator | null> {
  const strategies = [
    () => page.locator(`[data-testid*="${elementId}"]`),
    () => page.locator(`[aria-label*="${elementId}"]`),
    () => page.getByText(elementId.replace(/-/g, ' ')),
  ];

  for (const strategy of strategies) {
    try {
      const loc = strategy();
      const count = await loc.count();
      if (count === 1) {
        healingHistory.push({
          elementId,
          originalSelector,
          healedSelector: await loc.first().evaluate(
            (el) => el.outerHTML.slice(0, 100),
          ),
          strategy: 'auto-heal',
          timestamp: Date.now(),
        });
        return loc.first();
      }
    } catch {
      continue;
    }
  }

  return null;
}

async function tryBackendHeal(
  page: Page,
  elementId: string,
  originalSelector: string,
): Promise<Locator | null> {
  try {
    const a11ySnapshot = await page.accessibility.snapshot() || {};
    const result = await healViaBackend(
      originalSelector,
      JSON.stringify(a11ySnapshot).slice(0, 8000),
      `Element not found: ${elementId}`,
      page.url(),
    );

    if (result.healed && result.newLocator) {
      const loc = page.locator(result.newLocator);
      const count = await loc.count();
      if (count > 0) {
        healingHistory.push({
          elementId,
          originalSelector,
          healedSelector: result.newLocator,
          strategy: `backend-ai (confidence=${result.confidence})`,
          timestamp: Date.now(),
        });
        return loc.first();
      }
    }
  } catch {
    // Backend unreachable — graceful degradation
  }
  return null;
}

export function getHealingHistory(): HealingLog[] {
  return [...healingHistory];
}

export function clearHealingHistory(): void {
  healingHistory.length = 0;
}

export function createLocatorCandidates(
  testid: string,
  role?: string,
  roleName?: string,
  label?: string,
  text?: string,
  placeholder?: string,
  css?: string,
): LocatorCandidate[] {
  const candidates: LocatorCandidate[] = [];

  if (testid) {
    candidates.push({ strategy: 'data-testid', selector: testid, confidence: 0.95 });
  }
  if (role && roleName) {
    candidates.push({ strategy: 'role', selector: `${role}:${roleName}`, confidence: 0.90 });
  }
  if (label) {
    candidates.push({ strategy: 'label', selector: label, confidence: 0.85 });
  }
  if (placeholder) {
    candidates.push({ strategy: 'placeholder', selector: placeholder, confidence: 0.80 });
  }
  if (text) {
    candidates.push({ strategy: 'text', selector: text, confidence: 0.70 });
  }
  if (css) {
    candidates.push({ strategy: 'css', selector: css, confidence: 0.60 });
  }

  return candidates;
}

export async function healViaBackend(
  failedLocator: string,
  accessibilityTree: string,
  errorMessage: string = '',
  pageUrl: string = '',
): Promise<{ healed: boolean; newLocator: string; confidence: number }> {
  try {
    const resp = await fetch(`${ENGINE_URL}/api/ai/self-heal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        failed_locator: failedLocator,
        accessibility_tree: accessibilityTree,
        error_message: errorMessage,
        page_url: pageUrl,
      }),
    });
    if (!resp.ok) {
      return { healed: false, newLocator: '', confidence: 0 };
    }
    const data = await resp.json();
    return {
      healed: data.healed ?? false,
      newLocator: data.new_locator ?? '',
      confidence: data.confidence ?? 0,
    };
  } catch {
    return { healed: false, newLocator: '', confidence: 0 };
  }
}
