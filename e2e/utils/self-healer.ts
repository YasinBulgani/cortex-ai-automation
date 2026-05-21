/**
 * Self-healing middleware for Playwright tests.
 *
 * Başarısız testlerde Engine self-heal API'sini çağırır,
 * locator onarımı dener ve sonuçları loglar.
 */
import { type Page, type TestInfo } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const FETCH_TIMEOUT_MS = 15_000;
const HEALING_LOG_PATH = path.join("reports", "healing-log.json");
const SNAPSHOTS_DIR = path.join("reports", "dom-snapshots");

function getEngineBase(): string {
  return process.env.ENGINE_BASE || "http://127.0.0.1:5001";
}

export interface HealingResult {
  healed: boolean;
  oldLocator: string;
  newLocator: string;
  strategy: string;
  summary: string;
}

/**
 * Başarısız bir test için self-healing dener.
 */
export async function attemptHealing(
  page: Page,
  testInfo: TestInfo,
): Promise<HealingResult> {
  const noHeal: HealingResult = {
    healed: false,
    oldLocator: "",
    newLocator: "",
    strategy: "none",
    summary: "",
  };

  const errorMsg = testInfo.error?.message;
  if (!errorMsg) return { ...noHeal, summary: "Hata mesajı yok" };

  const match = errorMsg.match(
    /locator\('([^']+)'\)|getByTestId\('([^']+)'\)|data-testid="([^"]+)"|Locator\('([^']+)'\)/,
  );
  if (!match) return { ...noHeal, summary: "Locator hatası değil" };

  const oldLocator = match[1] || match[2] || match[3] || match[4] || "";

  let snapshot: unknown = null;
  try {
    snapshot = await page.accessibility.snapshot();
  } catch {
    // snapshot alınamadı
  }

  fs.mkdirSync(SNAPSHOTS_DIR, { recursive: true });
  if (snapshot) {
    const snapshotPath = path.join(SNAPSHOTS_DIR, `${testInfo.testId}.json`);
    fs.writeFileSync(snapshotPath, JSON.stringify(snapshot, null, 2));
  }

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
      const resp = await fetch(`${getEngineBase()}/api/ai/self-heal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          failed_locator: oldLocator,
          accessibility_tree: snapshot ? JSON.stringify(snapshot) : "",
          error_message: errorMsg.slice(0, 500),
          page_url: page.url(),
        }),
        signal: controller.signal,
      });

      if (!resp.ok) {
        return { ...noHeal, oldLocator, strategy: "api-error", summary: "Engine API hatası" };
      }

      const data = await resp.json();
      if (data.healed && data.new_locator) {
        const elem = page.locator(data.new_locator);
        if ((await elem.count()) > 0) {
          const result: HealingResult = {
            healed: true,
            oldLocator,
            newLocator: data.new_locator,
            strategy: data.strategy || "llm",
            summary: `${oldLocator} → ${data.new_locator}`,
          };
          appendHealingLog(testInfo.title, result);
          return result;
        }
      }
    } catch {
      // Engine erişilemedi veya timeout
    } finally {
      clearTimeout(timeout);
    }
  } catch {
    // outer error
  }

  return { ...noHeal, oldLocator, strategy: "failed", summary: "Heal başarısız" };
}

function appendHealingLog(testTitle: string, result: HealingResult) {
  try {
    fs.mkdirSync(path.dirname(HEALING_LOG_PATH), { recursive: true });

    let logs: unknown[] = [];
    if (fs.existsSync(HEALING_LOG_PATH)) {
      try {
        logs = JSON.parse(fs.readFileSync(HEALING_LOG_PATH, "utf-8"));
      } catch {
        logs = [];
      }
    }

    logs.push({
      testTitle,
      timestamp: new Date().toISOString(),
      ...result,
    });

    fs.writeFileSync(HEALING_LOG_PATH, JSON.stringify(logs, null, 2));
  } catch {
    // disk yazma hatası — sessiz devam
  }
}

/**
 * Playwright test.afterEach hook'u olarak kullanılacak fabrika.
 *
 * Kullanım (playwright.config.ts veya fixture):
 *   import { setupSelfHealing } from "./utils/self-healer";
 *   test.afterEach(setupSelfHealing());
 */
export function setupSelfHealing() {
  return async ({ page }: { page: Page }, testInfo: TestInfo) => {
    if (testInfo.status !== "failed") return;
    if (process.env.ENABLE_SELF_HEALING === "false") return;

    const result = await attemptHealing(page, testInfo);
    if (result.healed) {
      testInfo.annotations.push({
        type: "healed",
        description: result.summary,
      });
    }
  };
}
