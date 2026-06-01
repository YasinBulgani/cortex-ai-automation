/**
 * Shared types used across all SDK modules.
 */

/** ISO 8601 date-time string */
export type ISODateTime = string;

/** UUID string */
export type UUID = string;

export type ManagementStatus = "draft" | "active" | "archived";
export type TestPriority = "P0" | "P1" | "P2" | "P3";
export type TestCaseType =
  | "manual"
  | "exploratory"
  | "regression"
  | "smoke"
  | "uat";
export type TestRunStatus =
  | "not_run"
  | "running"
  | "passed"
  | "failed"
  | "blocked"
  | "skipped";
export type CoverageStatus = "covered" | "partial" | "not_covered";

// ── Pagination ────────────────────────────────────────────────────────────────

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
