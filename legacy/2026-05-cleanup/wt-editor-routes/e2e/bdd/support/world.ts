import { setWorldConstructor, World, IWorldOptions } from "@cucumber/cucumber";
import {
  chromium,
  firefox,
  webkit,
  type Browser,
  type BrowserContext,
  type Page,
} from "@playwright/test";
import { LoginPage } from "../../pages/login.page";
import { ProjectsPage } from "../../pages/projects.page";
import { ScenariosListPage } from "../../pages/scenarios-list.page";
import { ExecutionsPage } from "../../pages/executions.page";
import { FlowsPage } from "../../pages/flows.page";
import { ApprovalsPage } from "../../pages/approvals.page";
import { ImportPage } from "../../pages/import.page";
import { RegressionPage } from "../../pages/regression.page";
import { SidebarComponent } from "../../pages/components/sidebar.component";
import { HeaderComponent } from "../../pages/components/header.component";
import { SelfHealingService } from "./self-healing-service";

const BROWSER_TYPE = process.env.BROWSER || "chromium";
const HEADLESS = process.env.HEADLESS !== "false";
const BASE_URL =
  process.env.APP_URL || process.env.BASE_URL || "http://127.0.0.1:3417";

export class PlaywrightWorld extends World {
  browser!: Browser;
  context!: BrowserContext;
  page!: Page;

  loginPage!: LoginPage;
  projectsPage!: ProjectsPage;
  scenariosListPage!: ScenariosListPage;
  executionsPage!: ExecutionsPage;
  flowsPage!: FlowsPage;
  approvalsPage!: ApprovalsPage;
  importPage!: ImportPage;
  regressionPage!: RegressionPage;
  sidebar!: SidebarComponent;
  header!: HeaderComponent;
  selfHealing!: SelfHealingService;

  testData: Record<string, unknown> = {};

  constructor(options: IWorldOptions) {
    super(options);
  }

  async init() {
    const launcher =
      BROWSER_TYPE === "firefox"
        ? firefox
        : BROWSER_TYPE === "webkit"
          ? webkit
          : chromium;

    this.browser = await launcher.launch({ headless: HEADLESS });
    this.context = await this.browser.newContext({
      baseURL: BASE_URL,
      viewport: { width: 1280, height: 720 },
      ignoreHTTPSErrors: true,
    });
    this.page = await this.context.newPage();

    this.loginPage = new LoginPage(this.page);
    this.projectsPage = new ProjectsPage(this.page);
    this.scenariosListPage = new ScenariosListPage(this.page);
    this.executionsPage = new ExecutionsPage(this.page);
    this.flowsPage = new FlowsPage(this.page);
    this.approvalsPage = new ApprovalsPage(this.page);
    this.importPage = new ImportPage(this.page);
    this.regressionPage = new RegressionPage(this.page);
    this.sidebar = new SidebarComponent(this.page);
    this.header = new HeaderComponent(this.page);
    this.selfHealing = new SelfHealingService(this.page);
  }

  async cleanup() {
    await this.page?.close();
    await this.context?.close();
    await this.browser?.close();
  }
}

setWorldConstructor(PlaywrightWorld);
