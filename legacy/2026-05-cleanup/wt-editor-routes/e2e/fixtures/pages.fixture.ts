import { test as aiBase, expect } from "./ai.fixture";
import { LoginPage } from "../pages/login.page";
import { ProjectsPage } from "../pages/projects.page";
import { ScenariosListPage } from "../pages/scenarios-list.page";
import { ScenarioFormPage } from "../pages/scenario-form.page";
import { ExecutionsPage } from "../pages/executions.page";
import { FlowsPage } from "../pages/flows.page";
import { ApprovalsPage } from "../pages/approvals.page";
import { RegressionPage } from "../pages/regression.page";
import { ImportPage } from "../pages/import.page";
import { ReportsPage } from "../pages/reports.page";
import { SchedulesPage } from "../pages/schedules.page";
import { RequirementsPage } from "../pages/requirements.page";
import { TestDataPage } from "../pages/test-data.page";
import { IntegrationsPage } from "../pages/integrations.page";
import { BddGeneratePage } from "../pages/bdd-generate.page";
import { ApiTestsPage } from "../pages/api-tests.page";
import { VisualPage } from "../pages/visual.page";
import { ScenarioVersionsPage } from "../pages/scenario-versions.page";
import { SidebarComponent } from "../pages/components/sidebar.component";
import { HeaderComponent } from "../pages/components/header.component";

type PageFixtures = {
  loginPage: LoginPage;
  projectsPage: ProjectsPage;
  scenariosListPage: ScenariosListPage;
  scenarioFormPage: ScenarioFormPage;
  executionsPage: ExecutionsPage;
  flowsPage: FlowsPage;
  approvalsPage: ApprovalsPage;
  regressionPage: RegressionPage;
  importPage: ImportPage;
  reportsPage: ReportsPage;
  schedulesPage: SchedulesPage;
  requirementsPage: RequirementsPage;
  testDataPage: TestDataPage;
  integrationsPage: IntegrationsPage;
  bddGeneratePage: BddGeneratePage;
  apiTestsPage: ApiTestsPage;
  visualPage: VisualPage;
  scenarioVersionsPage: ScenarioVersionsPage;
  sidebar: SidebarComponent;
  header: HeaderComponent;
};

export const test = aiBase.extend<PageFixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },
  projectsPage: async ({ page }, use) => {
    await use(new ProjectsPage(page));
  },
  scenariosListPage: async ({ page }, use) => {
    await use(new ScenariosListPage(page));
  },
  scenarioFormPage: async ({ page }, use) => {
    await use(new ScenarioFormPage(page));
  },
  executionsPage: async ({ page }, use) => {
    await use(new ExecutionsPage(page));
  },
  flowsPage: async ({ page }, use) => {
    await use(new FlowsPage(page));
  },
  approvalsPage: async ({ page }, use) => {
    await use(new ApprovalsPage(page));
  },
  regressionPage: async ({ page }, use) => {
    await use(new RegressionPage(page));
  },
  importPage: async ({ page }, use) => {
    await use(new ImportPage(page));
  },
  reportsPage: async ({ page }, use) => {
    await use(new ReportsPage(page));
  },
  schedulesPage: async ({ page }, use) => {
    await use(new SchedulesPage(page));
  },
  requirementsPage: async ({ page }, use) => {
    await use(new RequirementsPage(page));
  },
  testDataPage: async ({ page }, use) => {
    await use(new TestDataPage(page));
  },
  integrationsPage: async ({ page }, use) => {
    await use(new IntegrationsPage(page));
  },
  bddGeneratePage: async ({ page }, use) => {
    await use(new BddGeneratePage(page));
  },
  apiTestsPage: async ({ page }, use) => {
    await use(new ApiTestsPage(page));
  },
  visualPage: async ({ page }, use) => {
    await use(new VisualPage(page));
  },
  scenarioVersionsPage: async ({ page }, use) => {
    await use(new ScenarioVersionsPage(page));
  },
  sidebar: async ({ page }, use) => {
    await use(new SidebarComponent(page));
  },
  header: async ({ page }, use) => {
    await use(new HeaderComponent(page));
  },
});

export { expect };
