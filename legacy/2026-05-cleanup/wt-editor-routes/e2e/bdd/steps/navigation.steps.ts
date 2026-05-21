import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { PlaywrightWorld } from "../support/world";

const MENU_TO_TESTID: Record<string, string> = {
  Senaryolar: "sidebar-link-scenarios",
  Kosular: "sidebar-link-executions",
  Akislar: "sidebar-link-flows",
  Onaylar: "sidebar-link-approvals",
  "Ice Aktar": "sidebar-link-import",
  Regresyon: "sidebar-link-regression",
  Projeler: "sidebar-link-projects",
  "API Testleri": "sidebar-link-api-tests",
  "Test Verileri": "sidebar-link-test-data",
  Entegrasyonlar: "sidebar-link-integrations",
};

const PAGE_URL_MAP: Record<string, RegExp> = {
  scenarios: /\/scenarios/,
  executions: /\/executions/,
  flows: /\/flows/,
  approvals: /\/approvals/,
  import: /\/import/,
  regression: /\/regression/,
  projects: /\/projects/,
};

Given(
  "kullanici herhangi bir sayfadadir",
  async function (this: PlaywrightWorld) {
    // already on a page after login
  },
);

Then(
  "sidebar'da {string} linkine tiklar",
  async function (this: PlaywrightWorld, menuLabel: string) {
    const testId = MENU_TO_TESTID[menuLabel];
    if (!testId) throw new Error(`Unknown menu label: ${menuLabel}`);

    const link = await this.selfHealing.findElement(testId, {
      role: "link",
      text: menuLabel,
    });
    await link.click();
    await this.page.waitForLoadState("domcontentloaded");
  },
);

Then(
  "{string} sayfasi yuklenir",
  async function (this: PlaywrightWorld, pageKey: string) {
    const pattern = PAGE_URL_MAP[pageKey];
    if (!pattern) throw new Error(`Unknown page key: ${pageKey}`);
    await expect(this.page).toHaveURL(pattern, { timeout: 15_000 });
  },
);
