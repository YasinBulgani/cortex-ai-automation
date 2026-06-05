/**
 * Operations — OpenAPI path & schema'lardan extracted utility types.
 *
 * Kullanım:
 *   import type { Project, Scenario, LoginRequest } from "@neurex/contracts";
 *   import type { paths } from "@neurex/contracts";
 */

import type { components, paths } from "./openapi";

// ─── Schema aliases (sık kullanılan tipler) ──────────────────────────────
type S = components["schemas"];

// Auth
export type LoginRequest    = S["LoginRequest"];
export type TokenResponse   = S["TokenResponse"];
export type UserMeResponse  = S["UserMeResponse"];
export type RegisterRequest = S["RegisterRequest"];
export type RefreshRequest  = S["RefreshRequest"];

// Project — en sık kullanılan
export type ProjectOut       = S["ProjectOut"] extends never ? unknown : S["ProjectOut"];
export type ProjectCreate    = S["ProjectCreate"] extends never ? unknown : S["ProjectCreate"];

// Management — openapi.d.ts içinde var olan schema'lara karşılık gelen tipler
// ManagementProject → ProjectOut (tspm project şeması)
export type ManagementProject      = S["ProjectOut"] extends never ? unknown : S["ProjectOut"];
// ManagementRequirement → RequirementOut
export type ManagementRequirement  = S["RequirementOut"] extends never ? unknown : S["RequirementOut"];
// ManagementRegressionSet → RegressionSetOut
export type ManagementRegressionSet        = S["RegressionSetOut"] extends never ? unknown : S["RegressionSetOut"];
export type ManagementRegressionSetDetail  = S["RegressionSetDetailOut"] extends never ? unknown : S["RegressionSetDetailOut"];
export type ManagementRegressionSetCreate  = S["RegressionSetCreate"] extends never ? unknown : S["RegressionSetCreate"];

// TestCase (tspm domain) — api_testing domain TestCase ile karışmasın
export type TspmTestCaseOut    = S["app__domains__tspm__schemas__TestCaseOut"] extends never ? unknown : S["app__domains__tspm__schemas__TestCaseOut"];
export type TspmTestCaseCreate = S["TestCaseCreate"] extends never ? unknown : S["TestCaseCreate"];
export type TspmTestCaseUpdate = S["app__domains__tspm__schemas__TestCaseUpdate"] extends never ? unknown : S["app__domains__tspm__schemas__TestCaseUpdate"];

// TestRun → ExecutionOut (tspm executions)
export type TestRun            = S["ExecutionOut"] extends never ? unknown : S["ExecutionOut"];
export type TestRunDetail      = S["ExecutionDetailOut"] extends never ? unknown : S["ExecutionDetailOut"];
export type TestRunCreate      = S["ExecutionCreate"] extends never ? unknown : S["ExecutionCreate"];
export type TestRunMetrics     = S["ExecutionMetricsOut"] extends never ? unknown : S["ExecutionMetricsOut"];
export type TestRunStats       = S["ExecutionStatsOut"] extends never ? unknown : S["ExecutionStatsOut"];
export type TestRunSummary     = S["ExecutionSummaryOut"] extends never ? unknown : S["ExecutionSummaryOut"];
export type TestRunTrends      = S["ExecutionTrendsOut"] extends never ? unknown : S["ExecutionTrendsOut"];
export type TestRunResultOut   = S["app__domains__tspm__schemas__ExecutionResultOut"] extends never ? unknown : S["app__domains__tspm__schemas__ExecutionResultOut"];

// ─── Path helpers ─────────────────────────────────────────────────────────
// Sık erişilen endpoint'lere TypeScript helper'ları
export type Paths       = paths;
export type Schemas     = components["schemas"];

// Bir endpoint'in response shape'ini almak için yardımcı:
export type GetResponse<P extends keyof paths, M extends keyof paths[P]> =
  paths[P][M] extends { responses: { 200: { content: { "application/json": infer R } } } }
    ? R
    : never;

// Örnek kullanım:
//   type Projects = GetResponse<"/api/v1/tspm/projects", "get">;
