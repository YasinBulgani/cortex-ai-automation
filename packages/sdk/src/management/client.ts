/**
 * @cortex/sdk — Test Management API client.
 *
 * Covers all endpoints under /api/v1/test-management/*.
 *
 * @example
 * ```ts
 * import { CortexClient } from "@cortex/sdk";
 * import { ManagementClient } from "@cortex/sdk/management";
 *
 * const http = new CortexClient({ baseUrl: "https://api.cortex.example.com", apiKey: "..." });
 * const mgmt = new ManagementClient(http);
 *
 * const projects = await mgmt.projects.list();
 * const cases    = await mgmt.cases("my-project-id").list();
 * ```
 */

import type { CortexClient } from "../common/client";
import type {
  ManagementProject,
  CreateManagementProjectInput,
  TestSuite,
  CreateTestSuiteInput,
  TestFolder,
  CreateTestFolderInput,
  TestCase,
  CreateTestCaseInput,
  UpdateTestCaseInput,
  TestRun,
  RunDetail,
  CreateTestRunInput,
  UpdateStepResultInput,
  RunCase,
  RequirementLink,
  CreateRequirementLinkInput,
  TraceabilityRow,
  DefectLink,
  CreateDefectLinkInput,
  ExecutionSummary,
  ImportJob,
  ImportJobDetail,
  CreateImportJobInput,
} from "./types";

const BASE = "/api/v1/test-management";
const P = (projectId: string) => `${BASE}/projects/${projectId}`;

// ── Sub-clients ───────────────────────────────────────────────────────────────

class ProjectsClient {
  constructor(private readonly http: CortexClient) {}

  list(): Promise<ManagementProject[]> {
    return this.http.get(`${BASE}/projects`);
  }

  get(projectId: string): Promise<ManagementProject> {
    return this.http.get(`${P(projectId)}`);
  }

  create(input: CreateManagementProjectInput): Promise<ManagementProject> {
    return this.http.post(`${BASE}/projects`, { json: input });
  }
}

class SuitesClient {
  constructor(
    private readonly http: CortexClient,
    private readonly projectId: string,
  ) {}

  create(input: CreateTestSuiteInput): Promise<TestSuite> {
    return this.http.post(`${P(this.projectId)}/suites`, { json: input });
  }
}

class FoldersClient {
  constructor(
    private readonly http: CortexClient,
    private readonly projectId: string,
  ) {}

  create(input: CreateTestFolderInput): Promise<TestFolder> {
    return this.http.post(`${P(this.projectId)}/folders`, { json: input });
  }
}

class CasesClient {
  constructor(
    private readonly http: CortexClient,
    private readonly projectId: string,
  ) {}

  list(options?: { q?: string; includeArchived?: boolean }): Promise<TestCase[]> {
    const params = new URLSearchParams();
    if (options?.q) params.set("q", options.q);
    if (options?.includeArchived) params.set("include_archived", "true");
    const qs = params.toString();
    return this.http.get(`${P(this.projectId)}/cases${qs ? `?${qs}` : ""}`);
  }

  get(caseId: string): Promise<TestCase> {
    return this.http.get(`${P(this.projectId)}/cases/${caseId}`);
  }

  create(input: CreateTestCaseInput): Promise<TestCase> {
    return this.http.post(`${P(this.projectId)}/cases`, { json: input });
  }

  update(caseId: string, input: UpdateTestCaseInput): Promise<TestCase> {
    return this.http.patch(`${P(this.projectId)}/cases/${caseId}`, { json: input });
  }

  archive(caseId: string): Promise<TestCase> {
    return this.http.post(`${P(this.projectId)}/cases/${caseId}/archive`);
  }
}

class RunsClient {
  constructor(
    private readonly http: CortexClient,
    private readonly projectId: string,
  ) {}

  list(statusFilter?: string): Promise<TestRun[]> {
    const qs = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
    return this.http.get(`${P(this.projectId)}/runs${qs}`);
  }

  get(runId: string): Promise<RunDetail> {
    return this.http.get(`${P(this.projectId)}/runs/${runId}`);
  }

  create(input: CreateTestRunInput): Promise<TestRun> {
    return this.http.post(`${P(this.projectId)}/runs`, { json: input });
  }

  updateStepResult(
    runCaseId: string,
    stepNo: number,
    input: UpdateStepResultInput,
  ): Promise<RunCase> {
    return this.http.patch(
      `${P(this.projectId)}/run-cases/${runCaseId}/steps/${stepNo}`,
      { json: input },
    );
  }
}

class RequirementsClient {
  constructor(
    private readonly http: CortexClient,
    private readonly projectId: string,
  ) {}

  list(caseId?: string): Promise<RequirementLink[]> {
    const qs = caseId ? `?case_id=${encodeURIComponent(caseId)}` : "";
    return this.http.get(`${P(this.projectId)}/requirements${qs}`);
  }

  traceability(): Promise<TraceabilityRow[]> {
    return this.http.get(`${P(this.projectId)}/requirements/traceability`);
  }

  create(input: CreateRequirementLinkInput): Promise<RequirementLink> {
    return this.http.post(`${P(this.projectId)}/requirements`, { json: input });
  }
}

class DefectsClient {
  constructor(
    private readonly http: CortexClient,
    private readonly projectId: string,
  ) {}

  list(): Promise<DefectLink[]> {
    return this.http.get(`${P(this.projectId)}/defects`);
  }

  create(input: CreateDefectLinkInput): Promise<DefectLink> {
    return this.http.post(`${P(this.projectId)}/defects`, { json: input });
  }
}

class ImportsClient {
  constructor(
    private readonly http: CortexClient,
    private readonly projectId: string,
  ) {}

  list(): Promise<ImportJob[]> {
    return this.http.get(`${P(this.projectId)}/imports`);
  }

  get(jobId: string): Promise<ImportJobDetail> {
    return this.http.get(`${P(this.projectId)}/imports/${jobId}`);
  }

  create(input: CreateImportJobInput): Promise<ImportJob> {
    return this.http.post(`${P(this.projectId)}/imports`, { json: input });
  }

  commit(jobId: string): Promise<ImportJob> {
    return this.http.post(`${P(this.projectId)}/imports/${jobId}/commit`);
  }
}

class ReportsClient {
  constructor(
    private readonly http: CortexClient,
    private readonly projectId: string,
  ) {}

  executionSummary(): Promise<ExecutionSummary> {
    return this.http.get(`${P(this.projectId)}/reports/execution-summary`);
  }

  export(): Promise<Record<string, unknown>> {
    return this.http.get(`${P(this.projectId)}/export`);
  }
}

// ── Main client ───────────────────────────────────────────────────────────────

/**
 * Top-level Test Management client.
 *
 * Access project-scoped sub-clients via the method overloads:
 *   mgmt.projects.list()
 *   mgmt.cases("project-id").list()
 *   mgmt.runs("project-id").get("run-id")
 */
export class ManagementClient {
  /** Project management (list, get, create). */
  readonly projects: ProjectsClient;

  constructor(private readonly http: CortexClient) {
    this.projects = new ProjectsClient(http);
  }

  suites(projectId: string): SuitesClient {
    return new SuitesClient(this.http, projectId);
  }

  folders(projectId: string): FoldersClient {
    return new FoldersClient(this.http, projectId);
  }

  cases(projectId: string): CasesClient {
    return new CasesClient(this.http, projectId);
  }

  runs(projectId: string): RunsClient {
    return new RunsClient(this.http, projectId);
  }

  requirements(projectId: string): RequirementsClient {
    return new RequirementsClient(this.http, projectId);
  }

  defects(projectId: string): DefectsClient {
    return new DefectsClient(this.http, projectId);
  }

  imports(projectId: string): ImportsClient {
    return new ImportsClient(this.http, projectId);
  }

  reports(projectId: string): ReportsClient {
    return new ReportsClient(this.http, projectId);
  }
}
