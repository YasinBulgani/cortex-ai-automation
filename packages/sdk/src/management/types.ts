/**
 * Test Management domain types — mirrors the FastAPI schemas.
 */

import type {
  UUID,
  ISODateTime,
  ManagementStatus,
  TestPriority,
  TestCaseType,
  TestRunStatus,
  CoverageStatus,
} from "../common/types";

// ── Project ───────────────────────────────────────────────────────────────────

export interface ManagementProject {
  id: UUID;
  tenant_id: UUID;
  tspm_project_id?: string | null;
  key: string;
  name: string;
  description?: string | null;
  status: ManagementStatus;
  created_by?: UUID | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface CreateManagementProjectInput {
  key: string;
  name: string;
  description?: string | null;
  tspm_project_id?: string | null;
}

// ── Suite / Folder ────────────────────────────────────────────────────────────

export interface TestSuite {
  id: UUID;
  project_id: UUID;
  name: string;
  description?: string | null;
  order_index: number;
  status: ManagementStatus;
  created_at: ISODateTime;
}

export interface CreateTestSuiteInput {
  name: string;
  description?: string | null;
  order_index?: number;
}

export interface TestFolder {
  id: UUID;
  suite_id: UUID;
  parent_id?: UUID | null;
  name: string;
  path: string;
  order_index: number;
  created_at: ISODateTime;
}

export interface CreateTestFolderInput {
  suite_id: UUID;
  parent_id?: UUID | null;
  name: string;
  order_index?: number;
}

// ── Case ──────────────────────────────────────────────────────────────────────

export interface TestCaseStep {
  id: UUID;
  case_id: UUID;
  step_no: number;
  action: string;
  expected_result: string;
  test_data: Record<string, unknown>;
  notes?: string | null;
  is_required: boolean;
}

export interface TestCase {
  id: UUID;
  project_id: UUID;
  suite_id?: UUID | null;
  folder_id?: UUID | null;
  case_key: string;
  title: string;
  objective?: string | null;
  preconditions?: string | null;
  test_data: Record<string, unknown>;
  priority: TestPriority;
  severity: string;
  type: TestCaseType;
  automation_status: string;
  status: ManagementStatus;
  source_type: string;
  source_ref?: string | null;
  tags: string[];
  custom_fields: Record<string, unknown>;
  current_version: number;
  last_run_status?: TestRunStatus | null;
  last_run_at?: ISODateTime | null;
  owner_id?: UUID | null;
  archived: boolean;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  steps: TestCaseStep[];
}

export interface CreateTestCaseInput {
  suite_id?: UUID | null;
  folder_id?: UUID | null;
  case_key?: string | null;
  title: string;
  objective?: string | null;
  preconditions?: string | null;
  test_data?: Record<string, unknown>;
  priority?: TestPriority;
  severity?: string;
  type?: TestCaseType;
  automation_status?: string;
  status?: ManagementStatus;
  source_type?: string;
  source_ref?: string | null;
  tags?: string[];
  custom_fields?: Record<string, unknown>;
  owner_id?: UUID | null;
  steps?: Array<{
    step_no: number;
    action: string;
    expected_result: string;
    test_data?: Record<string, unknown>;
    notes?: string | null;
    is_required?: boolean;
  }>;
}

export type UpdateTestCaseInput = Partial<CreateTestCaseInput>;

// ── Run ───────────────────────────────────────────────────────────────────────

export interface StepResult {
  id: UUID;
  run_case_id: UUID;
  step_no: number;
  status: TestRunStatus;
  actual_result?: string | null;
  comment?: string | null;
  executed_at?: ISODateTime | null;
}

export interface RunCase {
  id: UUID;
  run_id: UUID;
  case_id: UUID;
  case_version_no: number;
  assigned_to?: UUID | null;
  status: TestRunStatus;
  actual_result?: string | null;
  execution_notes?: string | null;
  started_at?: ISODateTime | null;
  completed_at?: ISODateTime | null;
  duration_seconds?: number | null;
  step_results: StepResult[];
}

export interface TestRun {
  id: UUID;
  cycle_id: UUID;
  name: string;
  status: TestRunStatus;
  started_at?: ISODateTime | null;
  completed_at?: ISODateTime | null;
  created_at: ISODateTime;
}

export interface RunDetail extends TestRun {
  run_cases: RunCase[];
}

export interface CreateTestRunInput {
  cycle_id: UUID;
  name: string;
  case_ids?: UUID[];
}

export interface UpdateStepResultInput {
  status: TestRunStatus;
  actual_result?: string | null;
  comment?: string | null;
}

// ── Requirement links ─────────────────────────────────────────────────────────

export interface RequirementLink {
  id: UUID;
  project_id: UUID;
  case_id: UUID;
  external_source: string;
  external_key: string;
  title_snapshot: string;
  url?: string | null;
  source_updated_at?: ISODateTime | null;
  coverage_status: CoverageStatus;
}

export interface CreateRequirementLinkInput {
  case_id: UUID;
  external_source: string;
  external_key: string;
  title_snapshot: string;
  url?: string | null;
  coverage_status?: CoverageStatus;
}

export interface TracedCase {
  case_id: UUID;
  case_key?: string | null;
  title: string;
  last_run_status?: TestRunStatus | null;
  coverage_status: CoverageStatus;
}

export interface TraceabilityRow {
  requirement_key: string;
  title: string;
  source: string;
  url?: string | null;
  covered: boolean;
  stale: boolean;
  cases: TracedCase[];
}

// ── Defect links ──────────────────────────────────────────────────────────────

export interface DefectLink {
  id: UUID;
  run_case_id: UUID;
  step_result_id?: UUID | null;
  external_source: string;
  external_key: string;
  title: string;
  status: string;
  url?: string | null;
  created_at: ISODateTime;
}

export interface CreateDefectLinkInput {
  run_case_id: UUID;
  step_result_id?: UUID | null;
  external_source: string;
  external_key: string;
  title: string;
  status: string;
  url?: string | null;
}

// ── Execution summary ─────────────────────────────────────────────────────────

export interface ExecutionSummary {
  total: number;
  not_run: number;
  passed: number;
  failed: number;
  blocked: number;
  skipped: number;
  retest: number;
  progress_pct: number;
  pass_rate_pct: number;
}

// ── Import jobs ───────────────────────────────────────────────────────────────

export interface ImportJobRow {
  id: UUID;
  job_id: UUID;
  row_no: number;
  parsed_data: Record<string, unknown>;
  validation_errors: Record<string, unknown>[];
  status: string;
  conflict_key?: string | null;
}

export interface ImportJob {
  id: UUID;
  project_id: UUID;
  filename: string;
  status: string;
  mapping: Record<string, unknown>;
  totals: Record<string, unknown>;
  created_by?: UUID | null;
  created_at: ISODateTime;
}

export interface ImportJobDetail extends ImportJob {
  rows: ImportJobRow[];
}

export interface CreateImportJobInput {
  filename: string;
  mapping?: Record<string, unknown>;
  rows?: Record<string, unknown>[];
}
