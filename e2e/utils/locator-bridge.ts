/**
 * LocatorBridge — Unified locator resolution layer.
 *
 * Bridges the gap between:
 *   1. engine/locators/locator_repository.json (central source of truth)
 *   2. e2e/pages/*.page.ts (TypeScript POM)
 *   3. Self-healing service
 *
 * Loads the JSON locator repository and provides typed access to
 * all locator strategies (test_id, css, xpath) for any page/element.
 */
import * as fs from "fs";
import * as path from "path";
import { type Page, type Locator } from "@playwright/test";

const REPO_PATH = path.resolve(
  __dirname,
  "../../engine/locators/locator_repository.json",
);

interface LocatorEntry {
  css: string;
  xpath: string;
  test_id: string;
  description: string;
  wait_strategy: "visible" | "attached" | "domcontentloaded";
}

interface PageDefinition {
  url_pattern: string;
  description: string;
  elements: Record<string, LocatorEntry>;
}

type LocatorRepository = Record<string, PageDefinition>;

let _cache: LocatorRepository | null = null;

function loadRepository(): LocatorRepository {
  if (_cache) return _cache;
  try {
    const raw = fs.readFileSync(REPO_PATH, "utf-8");
    _cache = JSON.parse(raw);
    return _cache!;
  } catch {
    console.warn(
      `[LocatorBridge] Could not load ${REPO_PATH}, using empty repository`,
    );
    _cache = {};
    return _cache;
  }
}

export function getLocator(
  pageName: string,
  elementName: string,
  strategy: "test_id" | "css" | "xpath" = "test_id",
): string | null {
  const repo = loadRepository();
  const pageDef = repo[pageName];
  if (!pageDef) return null;
  const element = pageDef.elements[elementName];
  if (!element) return null;
  return element[strategy] || null;
}

export function getPageElements(
  pageName: string,
): Record<string, LocatorEntry> | null {
  const repo = loadRepository();
  return repo[pageName]?.elements || null;
}

export function getAllPages(): string[] {
  return Object.keys(loadRepository());
}

/**
 * Resolve a locator from the repository using the priority chain:
 * test_id -> css -> xpath
 */
export function resolveFromRepo(
  page: Page,
  pageName: string,
  elementName: string,
): Locator | null {
  const entry = loadRepository()[pageName]?.elements[elementName];
  if (!entry) return null;

  if (entry.test_id) {
    return page.getByTestId(entry.test_id);
  }
  if (entry.css) {
    return page.locator(entry.css);
  }
  if (entry.xpath) {
    return page.locator(entry.xpath);
  }
  return null;
}

/**
 * Validate all locators in the repository against the current page.
 * Returns a health report for CI/monitoring.
 */
export async function validateLocators(
  page: Page,
  pageName: string,
): Promise<{
  total: number;
  found: number;
  missing: string[];
  healthPercent: number;
}> {
  const elements = getPageElements(pageName);
  if (!elements) return { total: 0, found: 0, missing: [], healthPercent: 0 };

  const entries = Object.entries(elements);
  const missing: string[] = [];

  for (const [name, entry] of entries) {
    try {
      const loc = page.getByTestId(entry.test_id);
      const count = await loc.count();
      if (count === 0) missing.push(name);
    } catch {
      missing.push(name);
    }
  }

  const total = entries.length;
  const found = total - missing.length;
  return {
    total,
    found,
    missing,
    healthPercent: total > 0 ? Math.round((found / total) * 100) : 0,
  };
}

export function clearCache(): void {
  _cache = null;
}
