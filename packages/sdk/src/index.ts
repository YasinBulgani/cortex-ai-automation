/**
 * @cortex/sdk — Cortex AI Automation public TypeScript SDK.
 *
 * A single `CortexSdk` class provides typed clients for every API domain.
 *
 * @example
 * ```ts
 * import { CortexSdk } from "@cortex/sdk";
 *
 * const sdk = new CortexSdk({
 *   baseUrl: "https://api.cortex.example.com",
 *   apiKey: process.env.CORTEX_API_KEY,
 * });
 *
 * // Test Management
 * const projects = await sdk.management.projects.list();
 * const cases    = await sdk.management.cases("proj-id").list({ q: "login" });
 * const matrix   = await sdk.management.requirements("proj-id").traceability();
 *
 * // Automation
 * const session  = await sdk.automation.playwright.createSession({ headless: true });
 * await sdk.automation.playwright.navigate(session.session_id, { url: "https://example.com" });
 *
 * // Projects
 * const allProjects = await sdk.projects.list();
 * ```
 */

export { CortexClient, CortexApiError } from "./common/client";
export type { CortexClientConfig, RequestOptions } from "./common/client";
export type {
  ISODateTime,
  UUID,
  ManagementStatus,
  TestPriority,
  TestCaseType,
  TestRunStatus,
  CoverageStatus,
  PaginationParams,
  PaginatedResponse,
} from "./common/types";

export { ManagementClient } from "./management/client";
export type {
  ManagementProject,
  TestCase,
  TestCaseStep,
  TestRun,
  RunDetail,
  RunCase,
  StepResult,
  RequirementLink,
  TraceabilityRow,
  TracedCase,
  DefectLink,
  ExecutionSummary,
  ImportJob,
  ImportJobDetail,
} from "./management/types";

export { AutomationClient, PlaywrightClient, NlTestClient } from "./automation/client";
export type {
  PlaywrightSession,
  ScreenshotResult,
  AutomationSuiteHealth,
} from "./automation/types";

export { ProjectsClient } from "./projects/client";
export type { Project, ProjectStats } from "./projects/types";

// ── CortexSdk ─────────────────────────────────────────────────────────────────

import { CortexClient, type CortexClientConfig } from "./common/client";
import { ManagementClient } from "./management/client";
import { AutomationClient } from "./automation/client";
import { ProjectsClient } from "./projects/client";

/**
 * Unified SDK entry point.
 *
 * Pass the same `CortexClientConfig` used for `CortexClient`.
 * All domain clients share the same underlying HTTP client instance.
 */
export class CortexSdk {
  /** Low-level HTTP client (for custom requests). */
  readonly http: CortexClient;
  /** Test Management domain. */
  readonly management: ManagementClient;
  /** Automation & Playwright domain. */
  readonly automation: AutomationClient;
  /** Core project management. */
  readonly projects: ProjectsClient;

  constructor(config: CortexClientConfig) {
    this.http = new CortexClient(config);
    this.management = new ManagementClient(this.http);
    this.automation = new AutomationClient(this.http);
    this.projects = new ProjectsClient(this.http);
  }
}
