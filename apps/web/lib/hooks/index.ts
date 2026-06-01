/**
 * TestwrightAI TanStack Query Hooks — Barrel Export
 *
 * Kullanim:
 *   import { useProjects, useCurrentUser, usePipelineStatus } from "@/lib/hooks";
 */

export * from "./use-auth";
export * from "./use-projects";
export * from "./use-scenarios";
export * from "./use-pipeline";
export * from "./use-agents";
export * from "./use-api-testing";
export * from "./use-ai-metrics";
export * from "./use-dsl";
export * from "./use-management";
export {
  useBrowserAction,
  useCloseSession,
  useCreateSession,
  useDOMSnapshot,
  useHealHistory as usePlaywrightHealHistory,
  useHealStats,
  useNavigate,
  usePlaywrightHealth,
  usePlaywrightSessions,
  useRunHealPipeline,
  useScreenshot,
  useSuggestSelectors,
  useValidateSelectors,
  useVerifyHeal,
} from "./use-playwright-mcp";
export type {
  BrowserActionRequest,
  BrowserActionResponse,
  CreateSessionRequest,
  CreateSessionResponse,
  DOMNode,
  DOMSnapshotRequest,
  DOMSnapshotResponse,
  HealHistoryItem,
  HealResult,
  HealStatsResponse,
  NavigateRequest,
  NavigateResponse,
  PlaywrightHealthResponse,
  PlaywrightSession,
  RunHealPipelineRequest,
  RunHealPipelineResponse,
  ScreenshotResponse,
  SelectorValidationItem,
  SuggestSelectorsRequest,
  SuggestSelectorsResponse,
  ValidateSelectorsRequest,
  ValidateSelectorsResponse,
  VerifyHealRequest,
  VerifyHealResponse,
} from "./use-playwright-mcp";
export * from "./use-synthetic-advanced";
// use-coverup ve use-locator-intelligence CoverageSummary/TrendResponse çakışması nedeniyle
// doğrudan path üzerinden import edilmeli: "@/lib/hooks/use-coverup" vb.
