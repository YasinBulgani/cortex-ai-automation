import { type Page, type Locator, expect } from "@playwright/test";

type SidebarSection =
  | "projects"
  | "scenarios"
  | "requirements"
  | "coverage"
  | "executions"
  | "analytics"
  | "schedules"
  | "flows"
  | "regression"
  | "approvals"
  | "import"
  | "api-tests"
  | "test-data"
  | "integrations"
  | "manual"
  | "automation"
  | "runs"
  | "reports"
  | "cicd"
  | "workflows";

const LABELS: Record<SidebarSection, string> = {
  projects: "Projeler",
  scenarios: "Senaryolar",
  requirements: "Gereksinimler",
  coverage: "Kapsam",
  executions: "Koşular (TSPM)",
  analytics: "Analitik",
  schedules: "Zamanlayıcı",
  flows: "Akışlar",
  regression: "Regresyon",
  approvals: "Onaylar",
  import: "İçe Aktar",
  "api-tests": "API Testleri",
  "test-data": "Test Verileri",
  integrations: "Entegrasyonlar",
  manual: "Manuel Testler",
  automation: "Otomasyonlar",
  runs: "Koşu Geçmişi",
  reports: "Raporlar",
  cicd: "CI/CD",
  workflows: "Workflows",
};

export class SidebarComponent {
  private readonly sidebar: Locator;

  constructor(private readonly page: Page) {
    this.sidebar = page.locator("aside");
  }

  get logo() {
    return this.sidebar.locator("a").first();
  }

  link(section: SidebarSection): Locator {
    return this.sidebar.getByText(LABELS[section], { exact: true });
  }

  async navigateTo(section: SidebarSection) {
    await this.link(section).click();
  }

  async assertLinkVisible(section: SidebarSection) {
    await expect(this.link(section)).toBeVisible();
  }
}
