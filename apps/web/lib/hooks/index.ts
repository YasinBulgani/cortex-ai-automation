/**
 * Neurex TanStack Query Hooks — Barrel Export
 *
 * Kullanim:
 *   import { useProjects, useCurrentUser, usePipelineStatus } from "@/lib/hooks";
 */

export * from "./use-auth";
export * from "./use-profile";
export * from "./use-admin-users";
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
export * from "./use-web-dashboard";
export * from "./use-management-role";
export * from "./use-management-project-id";
export * from "./use-mgmt-comments";
// use-mgmt-design: usePromoteCases conflicts with use-management's usePromoteCases;
// re-exported as usePromoteDesignCases to disambiguate.
export type {
  DesignTechnique,
  DesignDataType,
  DesignFieldSpec,
  GeneratedCaseDraft,
  DesignPartition,
  DesignRun,
  CreateDesignRunInput,
  PromoteCasesInput,
  PromoteCasesResponse,
  CaseParamSet,
  CaseDataRow,
  GenerateDataRowsInput,
  ExpandCaseResponse,
  DesignTemplate,
} from "./use-mgmt-design";
export {
  designKeys,
  useCreateBvaRun,
  useCreateEqRun,
  useCreateDtRun,
  useCreatePairwiseRun,
  useDesignRun,
  useDesignRuns,
  usePromoteCases as usePromoteDesignCases,
  useCaseParamSets,
  useCreateParamSet,
  useDataRows,
  useGenerateDataRows,
  useAddManualRows,
  useExpandCase,
  designTemplateKeys,
  useDesignTemplates,
  useSaveDesignTemplate,
  useDeleteDesignTemplate,
} from "./use-mgmt-design";
export * from "./use-mgmt-notifications";
// use-coverup ve use-locator-intelligence CoverageSummary/TrendResponse çakışması nedeniyle
// doğrudan path üzerinden import edilmeli: "@/lib/hooks/use-coverup" vb.
