/** @jest-environment jsdom */
import { renderHook } from "@testing-library/react";

// ── Mock: @tanstack/react-query ──────────────────────────────────────────────
jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn(),
  useMutation: jest.fn(),
  useQueryClient: jest.fn(() => ({
    invalidateQueries: jest.fn(),
    setQueryData: jest.fn(),
    clear: jest.fn(),
  })),
  useInfiniteQuery: jest.fn(),
  QueryClient: jest.fn().mockImplementation(() => ({})),
  QueryClientProvider: ({ children }: { children: React.ReactNode }) => children,
}));

import { useQuery, useMutation } from "@tanstack/react-query";

// ── Mock: @/lib/api-client ───────────────────────────────────────────────────
jest.mock("@/lib/api-client", () => ({
  apiFetch: jest.fn(),
  getToken: jest.fn(() => "fake-token"),
  setTokens: jest.fn(),
  clearTokens: jest.fn(),
}));

// ── Mock: next/navigation ────────────────────────────────────────────────────
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  useParams: () => ({}),
}));

// ── Imports under test ────────────────────────────────────────────────────────

import {
  useAgentInfo,
  useLLMTraces,
  agentKeys,
} from "../hooks/use-agents";

import {
  useQualityMetrics,
  useLlmTraces,
  useLlmTraceStats,
  useModelRouterStats,
  useCrossAgentMemoryStats,
  useCrossAgentMemoryEntries,
  useFewShotBankStats,
  aiMetricsKeys,
} from "../hooks/use-ai-metrics";

import {
  useApiTestingStats,
  useEnvironments,
  useApiSpecs,
  useApiEndpoints,
  useApiTestCases,
  useImportSpec,
  useCreateEnvironment,
  useUpdateEnvironment,
  useDeleteEnvironment,
  useChains,
  useCreateChain,
  useExecutionHistory,
  useExecutionDetail,
  useTestTrends,
  useFlakyTests,
  useCoverageAnalysis,
  useHealingStats,
  apiTestingKeys,
} from "../hooks/use-api-testing";

import {
  useCurrentUser,
  useLogin,
  useLogout,
  authKeys,
} from "../hooks/use-auth";

import {
  useUploadCoverage,
  useAnalyzeCoverage,
  useGenerateTests,
  useCoverageReports,
  useCoverageReport,
  useCoverageTrends,
  useBankingTargets,
} from "../hooks/use-coverup";

import {
  useFallbackResolve,
  useStabilityAnalysis,
  useImproveSuggestions,
  usePOMGenerate,
  useBreakagePrediction,
  useLocatorTrends,
} from "../hooks/use-locator-intelligence";

import {
  useBankingHealth,
  usePipelineStatus,
  useStartPipeline,
  useCancelPipeline,
  pipelineKeys,
} from "../hooks/use-pipeline";

import {
  usePlaywrightHealth,
  usePlaywrightSessions,
  useCreateSession,
  useCloseSession,
  useNavigate,
  useScreenshot,
  useDOMSnapshot,
  useRunHealPipeline,
  useHealHistory,
  useHealStats,
} from "../hooks/use-playwright-mcp";

// ── Default mock return values ────────────────────────────────────────────────
beforeEach(() => {
  (useQuery as jest.Mock).mockReturnValue({
    data: undefined,
    isLoading: false,
    isFetching: false,
    error: null,
    refetch: jest.fn(),
  });
  (useMutation as jest.Mock).mockReturnValue({
    mutate: jest.fn(),
    mutateAsync: jest.fn(),
    isPending: false,
    error: null,
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// use-agents
// ═════════════════════════════════════════════════════════════════════════════

describe("agentKeys", () => {
  it("all key is ['agents']", () => {
    expect(agentKeys.all).toEqual(["agents"]);
  });

  it("info() returns ['agents', 'info']", () => {
    expect(agentKeys.info()).toEqual(["agents", "info"]);
  });

  it("traces() without params returns key with undefined params", () => {
    const key = agentKeys.traces();
    expect(key[0]).toBe("agents");
    expect(key[1]).toBe("traces");
  });

  it("traces() with params embeds the params object", () => {
    const key = agentKeys.traces({ limit: 10, agent_name: "myAgent" });
    expect(key[2]).toEqual({ limit: 10, agent_name: "myAgent" });
  });
});

describe("useAgentInfo", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useAgentInfo())).not.toThrow();
  });

  it("returns data undefined by default (mocked)", () => {
    const { result } = renderHook(() => useAgentInfo());
    expect(result.current.data).toBeUndefined();
  });

  it("returns isLoading false by default", () => {
    const { result } = renderHook(() => useAgentInfo());
    expect(result.current.isLoading).toBe(false);
  });

  it("returns non-null result object", () => {
    const { result } = renderHook(() => useAgentInfo());
    expect(result.current).not.toBeNull();
  });
});

describe("useLLMTraces", () => {
  it("renders without throwing (no params)", () => {
    expect(() => renderHook(() => useLLMTraces())).not.toThrow();
  });

  it("renders without throwing (with params)", () => {
    expect(() =>
      renderHook(() => useLLMTraces({ limit: 20, agent_name: "testAgent" }))
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useLLMTraces());
    expect(result.current.data).toBeUndefined();
  });

  it("isLoading is false by default", () => {
    const { result } = renderHook(() => useLLMTraces({ limit: 10 }));
    expect(result.current.isLoading).toBe(false);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// use-ai-metrics
// ═════════════════════════════════════════════════════════════════════════════

describe("aiMetricsKeys", () => {
  it("all key is ['ai']", () => {
    expect(aiMetricsKeys.all).toEqual(["ai"]);
  });

  it("qualityMetrics key starts with 'ai', 'quality-metrics'", () => {
    const key = aiMetricsKeys.qualityMetrics("proj-1", 30);
    expect(key[0]).toBe("ai");
    expect(key[1]).toBe("quality-metrics");
    expect(key[2]).toBe("proj-1");
    expect(key[3]).toBe(30);
  });

  it("llmTraces key includes projectId", () => {
    const key = aiMetricsKeys.llmTraces("proj-2");
    expect(key[0]).toBe("ai");
    expect(key[2]).toBe("proj-2");
  });

  it("modelRouterStats key shape", () => {
    const key = aiMetricsKeys.modelRouterStats();
    expect(key).toEqual(["ai", "model-router", "stats"]);
  });
});

describe("useQualityMetrics", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useQualityMetrics("proj-1"))
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useQualityMetrics("proj-1", 30));
    expect(result.current.data).toBeUndefined();
  });

  it("renders without throwing when projectId is undefined", () => {
    expect(() =>
      renderHook(() => useQualityMetrics(undefined))
    ).not.toThrow();
  });

  it("accepts optional agent and model filters", () => {
    expect(() =>
      renderHook(() =>
        useQualityMetrics("proj-1", 7, "banking-agent", "gpt-4")
      )
    ).not.toThrow();
  });
});

describe("useLlmTraces", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useLlmTraces("proj-1"))).not.toThrow();
  });

  it("renders without throwing when projectId is undefined", () => {
    expect(() => renderHook(() => useLlmTraces(undefined))).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useLlmTraces("proj-1"));
    expect(result.current.data).toBeUndefined();
  });

  it("accepts optional runId, agentName, and limit", () => {
    expect(() =>
      renderHook(() => useLlmTraces("proj-1", "run-abc", "myAgent", 50))
    ).not.toThrow();
  });
});

describe("useLlmTraceStats", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useLlmTraceStats("proj-1"))).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useLlmTraceStats("proj-1"));
    expect(result.current.data).toBeUndefined();
  });

  it("renders without throwing when projectId is undefined", () => {
    expect(() => renderHook(() => useLlmTraceStats(undefined))).not.toThrow();
  });
});

describe("useModelRouterStats", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useModelRouterStats())).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useModelRouterStats());
    expect(result.current.data).toBeUndefined();
  });

  it("isLoading is false by default", () => {
    const { result } = renderHook(() => useModelRouterStats());
    expect(result.current.isLoading).toBe(false);
  });
});

describe("useCrossAgentMemoryStats", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useCrossAgentMemoryStats())).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useCrossAgentMemoryStats());
    expect(result.current.data).toBeUndefined();
  });
});

describe("useCrossAgentMemoryEntries", () => {
  it("renders without throwing (no filters)", () => {
    expect(() =>
      renderHook(() => useCrossAgentMemoryEntries())
    ).not.toThrow();
  });

  it("renders without throwing (with filters)", () => {
    expect(() =>
      renderHook(() =>
        useCrossAgentMemoryEntries("test_result", "banking-agent", 20)
      )
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useCrossAgentMemoryEntries());
    expect(result.current.data).toBeUndefined();
  });
});

describe("useFewShotBankStats", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useFewShotBankStats())).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useFewShotBankStats());
    expect(result.current.data).toBeUndefined();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// use-api-testing
// ═════════════════════════════════════════════════════════════════════════════

describe("apiTestingKeys", () => {
  it("all key includes projectId", () => {
    expect(apiTestingKeys.all("proj-1")).toEqual(["api-testing", "proj-1"]);
  });

  it("stats key extends all key", () => {
    const key = apiTestingKeys.stats("proj-1");
    expect(key[0]).toBe("api-testing");
    expect(key[2]).toBe("stats");
  });

  it("environments key is correct", () => {
    const key = apiTestingKeys.environments("proj-1");
    expect(key).toEqual(["api-testing", "proj-1", "environments"]);
  });

  it("specs key is correct", () => {
    const key = apiTestingKeys.specs("proj-2");
    expect(key[2]).toBe("specs");
  });
});

describe("useApiTestingStats", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useApiTestingStats("proj-1"))
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useApiTestingStats("proj-1"));
    expect(result.current.data).toBeUndefined();
  });

  it("renders without throwing when projectId is undefined", () => {
    expect(() =>
      renderHook(() => useApiTestingStats(undefined))
    ).not.toThrow();
  });
});

describe("useEnvironments", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useEnvironments("proj-1"))
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useEnvironments("proj-1"));
    expect(result.current.data).toBeUndefined();
  });

  it("renders without throwing when projectId is undefined", () => {
    expect(() => renderHook(() => useEnvironments(undefined))).not.toThrow();
  });
});

describe("useApiSpecs", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useApiSpecs("proj-1"))).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useApiSpecs("proj-1"));
    expect(result.current.data).toBeUndefined();
  });

  it("isLoading is false by default", () => {
    const { result } = renderHook(() => useApiSpecs("proj-1"));
    expect(result.current.isLoading).toBe(false);
  });
});

describe("useApiEndpoints", () => {
  it("renders without throwing (no filters)", () => {
    expect(() =>
      renderHook(() => useApiEndpoints("proj-1"))
    ).not.toThrow();
  });

  it("renders without throwing (with filters)", () => {
    expect(() =>
      renderHook(() =>
        useApiEndpoints("proj-1", { spec_id: "spec-abc", risk_level: "high" })
      )
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useApiEndpoints("proj-1"));
    expect(result.current.data).toBeUndefined();
  });
});

describe("useApiTestCases", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useApiTestCases("proj-1"))
    ).not.toThrow();
  });

  it("renders with filters without throwing", () => {
    expect(() =>
      renderHook(() =>
        useApiTestCases("proj-1", {
          endpoint_id: "ep-1",
          test_type: "security",
        })
      )
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useApiTestCases("proj-1"));
    expect(result.current.data).toBeUndefined();
  });
});

describe("useImportSpec", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useImportSpec("proj-1"))
    ).not.toThrow();
  });

  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useImportSpec("proj-1"));
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns object with mutateAsync function", () => {
    const { result } = renderHook(() => useImportSpec("proj-1"));
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useImportSpec("proj-1"));
    expect(result.current.isPending).toBe(false);
  });
});

describe("useCreateEnvironment", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useCreateEnvironment("proj-1"))
    ).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useCreateEnvironment("proj-1"));
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns mutateAsync function", () => {
    const { result } = renderHook(() => useCreateEnvironment("proj-1"));
    expect(typeof result.current.mutateAsync).toBe("function");
  });
});

describe("useUpdateEnvironment", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useUpdateEnvironment("proj-1"))
    ).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useUpdateEnvironment("proj-1"));
    expect(typeof result.current.mutate).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useUpdateEnvironment("proj-1"));
    expect(result.current.isPending).toBe(false);
  });
});

describe("useDeleteEnvironment", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useDeleteEnvironment("proj-1"))
    ).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useDeleteEnvironment("proj-1"));
    expect(typeof result.current.mutate).toBe("function");
  });
});

describe("useChains", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useChains("proj-1"))).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useChains("proj-1"));
    expect(result.current.data).toBeUndefined();
  });

  it("renders without throwing when projectId is undefined", () => {
    expect(() => renderHook(() => useChains(undefined))).not.toThrow();
  });
});

describe("useCreateChain", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useCreateChain("proj-1"))).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useCreateChain("proj-1"));
    expect(typeof result.current.mutate).toBe("function");
  });
});

describe("useExecutionHistory", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useExecutionHistory("proj-1"))
    ).not.toThrow();
  });

  it("renders with filters without throwing", () => {
    expect(() =>
      renderHook(() =>
        useExecutionHistory("proj-1", { page: 1, per_page: 20 })
      )
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useExecutionHistory("proj-1"));
    expect(result.current.data).toBeUndefined();
  });
});

describe("useExecutionDetail", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useExecutionDetail("proj-1", "run-abc"))
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() =>
      useExecutionDetail("proj-1", "run-abc")
    );
    expect(result.current.data).toBeUndefined();
  });

  it("renders without throwing when runId is undefined", () => {
    expect(() =>
      renderHook(() => useExecutionDetail("proj-1", undefined))
    ).not.toThrow();
  });
});

describe("useTestTrends", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useTestTrends("proj-1"))).not.toThrow();
  });

  it("renders with days param without throwing", () => {
    expect(() =>
      renderHook(() => useTestTrends("proj-1", 14))
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useTestTrends("proj-1"));
    expect(result.current.data).toBeUndefined();
  });
});

describe("useFlakyTests", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useFlakyTests("proj-1"))).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useFlakyTests("proj-1"));
    expect(result.current.data).toBeUndefined();
  });

  it("renders with windowDays param without throwing", () => {
    expect(() =>
      renderHook(() => useFlakyTests("proj-1", 7))
    ).not.toThrow();
  });
});

describe("useCoverageAnalysis", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useCoverageAnalysis("proj-1"))
    ).not.toThrow();
  });

  it("renders with specId param without throwing", () => {
    expect(() =>
      renderHook(() => useCoverageAnalysis("proj-1", "spec-abc"))
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useCoverageAnalysis("proj-1"));
    expect(result.current.data).toBeUndefined();
  });
});

describe("useHealingStats (api-testing)", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useHealingStats("proj-1"))).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useHealingStats("proj-1"));
    expect(result.current.data).toBeUndefined();
  });

  it("accepts days param without throwing", () => {
    expect(() =>
      renderHook(() => useHealingStats("proj-1", 60))
    ).not.toThrow();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// use-auth
// ═════════════════════════════════════════════════════════════════════════════

describe("authKeys", () => {
  it("all key is ['auth']", () => {
    expect(authKeys.all).toEqual(["auth"]);
  });

  it("me() returns ['auth', 'me']", () => {
    expect(authKeys.me()).toEqual(["auth", "me"]);
  });
});

describe("useCurrentUser (use-auth)", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useCurrentUser())).not.toThrow();
  });

  it("user is null when data is undefined", () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.user).toBeNull();
  });

  it("loading is false by default", () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.loading).toBe(false);
  });

  it("error is null by default", () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.error).toBeNull();
  });

  it("exposes refetch as a function", () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(typeof result.current.refetch).toBe("function");
  });

  it("exposes hasPermission as a function", () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(typeof result.current.hasPermission).toBe("function");
  });

  it("hasPermission returns false when user is null", () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.hasPermission("any.perm")).toBe(false);
  });

  it("hasPermission returns true when user has admin.* permission", () => {
    (useQuery as jest.Mock).mockReturnValueOnce({
      data: {
        id: "u1",
        email: "admin@test.com",
        roles: ["admin"],
        permissions: ["admin.*"],
      },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.hasPermission("anything")).toBe(true);
  });

  it("hasPermission returns true for exact match", () => {
    (useQuery as jest.Mock).mockReturnValueOnce({
      data: {
        id: "u2",
        email: "user@test.com",
        roles: ["qa"],
        permissions: ["scenarios.read", "projects.read"],
      },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.hasPermission("scenarios.read")).toBe(true);
  });

  it("hasPermission returns false when permission not in list", () => {
    (useQuery as jest.Mock).mockReturnValueOnce({
      data: {
        id: "u3",
        email: "viewer@test.com",
        roles: ["viewer"],
        permissions: ["projects.read"],
      },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.hasPermission("projects.delete")).toBe(false);
  });

  it("loading is true when query isLoading is true", () => {
    (useQuery as jest.Mock).mockReturnValueOnce({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: jest.fn(),
    });
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.loading).toBe(true);
  });

  it("error surfaces message string from query.error", () => {
    (useQuery as jest.Mock).mockReturnValueOnce({
      data: undefined,
      isLoading: false,
      error: { message: "Unauthorized" },
      refetch: jest.fn(),
    });
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.error).toBe("Unauthorized");
  });
});

describe("useLogin (use-auth)", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useLogin())).not.toThrow();
  });

  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useLogin());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns object with mutateAsync function", () => {
    const { result } = renderHook(() => useLogin());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useLogin());
    expect(result.current.isPending).toBe(false);
  });
});

describe("useLogout (use-auth)", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useLogout())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useLogout());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns mutateAsync function", () => {
    const { result } = renderHook(() => useLogout());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useLogout());
    expect(result.current.isPending).toBe(false);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// use-coverup
// ═════════════════════════════════════════════════════════════════════════════

describe("useUploadCoverage", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useUploadCoverage())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useUploadCoverage());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns mutateAsync function", () => {
    const { result } = renderHook(() => useUploadCoverage());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useUploadCoverage());
    expect(result.current.isPending).toBe(false);
  });
});

describe("useAnalyzeCoverage", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useAnalyzeCoverage())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useAnalyzeCoverage());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useAnalyzeCoverage());
    expect(result.current.isPending).toBe(false);
  });
});

describe("useGenerateTests", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useGenerateTests())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useGenerateTests());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns mutateAsync function", () => {
    const { result } = renderHook(() => useGenerateTests());
    expect(typeof result.current.mutateAsync).toBe("function");
  });
});

describe("useCoverageReports", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useCoverageReports())).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useCoverageReports());
    expect(result.current.data).toBeUndefined();
  });

  it("isLoading is false by default", () => {
    const { result } = renderHook(() => useCoverageReports());
    expect(result.current.isLoading).toBe(false);
  });
});

describe("useCoverageReport", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useCoverageReport("report-123"))
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useCoverageReport("report-123"));
    expect(result.current.data).toBeUndefined();
  });
});

describe("useCoverageTrends", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useCoverageTrends())).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useCoverageTrends());
    expect(result.current.data).toBeUndefined();
  });
});

describe("useBankingTargets", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useBankingTargets())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useBankingTargets());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useBankingTargets());
    expect(result.current.isPending).toBe(false);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// use-locator-intelligence
// ═════════════════════════════════════════════════════════════════════════════

describe("useFallbackResolve", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useFallbackResolve())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useFallbackResolve());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns mutateAsync function", () => {
    const { result } = renderHook(() => useFallbackResolve());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useFallbackResolve());
    expect(result.current.isPending).toBe(false);
  });
});

describe("useStabilityAnalysis", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useStabilityAnalysis())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useStabilityAnalysis());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useStabilityAnalysis());
    expect(result.current.isPending).toBe(false);
  });
});

describe("useImproveSuggestions", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useImproveSuggestions())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useImproveSuggestions());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns mutateAsync function", () => {
    const { result } = renderHook(() => useImproveSuggestions());
    expect(typeof result.current.mutateAsync).toBe("function");
  });
});

describe("usePOMGenerate", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => usePOMGenerate())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => usePOMGenerate());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => usePOMGenerate());
    expect(result.current.isPending).toBe(false);
  });
});

describe("useBreakagePrediction", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useBreakagePrediction())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useBreakagePrediction());
    expect(typeof result.current.mutate).toBe("function");
  });
});

describe("useLocatorTrends", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useLocatorTrends())).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useLocatorTrends());
    expect(result.current.data).toBeUndefined();
  });

  it("isLoading is false by default", () => {
    const { result } = renderHook(() => useLocatorTrends());
    expect(result.current.isLoading).toBe(false);
  });

  it("returns non-null result object", () => {
    const { result } = renderHook(() => useLocatorTrends());
    expect(result.current).not.toBeNull();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// use-pipeline
// ═════════════════════════════════════════════════════════════════════════════

describe("pipelineKeys", () => {
  it("all key is ['pipeline']", () => {
    expect(pipelineKeys.all).toEqual(["pipeline"]);
  });

  it("health() returns ['pipeline', 'health']", () => {
    expect(pipelineKeys.health()).toEqual(["pipeline", "health"]);
  });

  it("status() returns ['pipeline', 'status']", () => {
    expect(pipelineKeys.status()).toEqual(["pipeline", "status"]);
  });

  it("history() returns ['pipeline', 'history']", () => {
    expect(pipelineKeys.history()).toEqual(["pipeline", "history"]);
  });
});

describe("useBankingHealth", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useBankingHealth())).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useBankingHealth());
    expect(result.current.data).toBeUndefined();
  });

  it("isLoading is false by default", () => {
    const { result } = renderHook(() => useBankingHealth());
    expect(result.current.isLoading).toBe(false);
  });
});

describe("usePipelineStatus", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => usePipelineStatus())).not.toThrow();
  });

  it("renders with enabled=false without throwing", () => {
    expect(() => renderHook(() => usePipelineStatus(false))).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => usePipelineStatus());
    expect(result.current.data).toBeUndefined();
  });

  it("returns non-null result object", () => {
    const { result } = renderHook(() => usePipelineStatus());
    expect(result.current).not.toBeNull();
  });
});

describe("useStartPipeline", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useStartPipeline())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useStartPipeline());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns mutateAsync function", () => {
    const { result } = renderHook(() => useStartPipeline());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useStartPipeline());
    expect(result.current.isPending).toBe(false);
  });
});

describe("useCancelPipeline", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useCancelPipeline())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useCancelPipeline());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useCancelPipeline());
    expect(result.current.isPending).toBe(false);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// use-playwright-mcp
// ═════════════════════════════════════════════════════════════════════════════

describe("usePlaywrightHealth", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => usePlaywrightHealth())).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => usePlaywrightHealth());
    expect(result.current.data).toBeUndefined();
  });

  it("isLoading is false by default", () => {
    const { result } = renderHook(() => usePlaywrightHealth());
    expect(result.current.isLoading).toBe(false);
  });

  it("returns non-null result object", () => {
    const { result } = renderHook(() => usePlaywrightHealth());
    expect(result.current).not.toBeNull();
  });
});

describe("usePlaywrightSessions", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => usePlaywrightSessions())).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => usePlaywrightSessions());
    expect(result.current.data).toBeUndefined();
  });

  it("isLoading is false by default", () => {
    const { result } = renderHook(() => usePlaywrightSessions());
    expect(result.current.isLoading).toBe(false);
  });
});

describe("useCreateSession", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useCreateSession())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useCreateSession());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns mutateAsync function", () => {
    const { result } = renderHook(() => useCreateSession());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useCreateSession());
    expect(result.current.isPending).toBe(false);
  });
});

describe("useCloseSession", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useCloseSession())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useCloseSession());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns mutateAsync function", () => {
    const { result } = renderHook(() => useCloseSession());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useCloseSession());
    expect(result.current.isPending).toBe(false);
  });
});

describe("useNavigate", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useNavigate("session-abc"))
    ).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useNavigate("session-abc"));
    expect(typeof result.current.mutate).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useNavigate("session-abc"));
    expect(result.current.isPending).toBe(false);
  });
});

describe("useScreenshot", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useScreenshot("session-abc"))
    ).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useScreenshot("session-abc"));
    expect(result.current.data).toBeUndefined();
  });

  it("isLoading is false by default", () => {
    const { result } = renderHook(() => useScreenshot("session-abc"));
    expect(result.current.isLoading).toBe(false);
  });
});

describe("useDOMSnapshot", () => {
  it("renders without throwing", () => {
    expect(() =>
      renderHook(() => useDOMSnapshot("session-abc"))
    ).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useDOMSnapshot("session-abc"));
    expect(typeof result.current.mutate).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useDOMSnapshot("session-abc"));
    expect(result.current.isPending).toBe(false);
  });
});

describe("useRunHealPipeline", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useRunHealPipeline())).not.toThrow();
  });

  it("returns mutate function", () => {
    const { result } = renderHook(() => useRunHealPipeline());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns mutateAsync function", () => {
    const { result } = renderHook(() => useRunHealPipeline());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useRunHealPipeline());
    expect(result.current.isPending).toBe(false);
  });
});

describe("useHealHistory", () => {
  it("renders without throwing (no limit)", () => {
    expect(() => renderHook(() => useHealHistory())).not.toThrow();
  });

  it("renders without throwing (with limit)", () => {
    expect(() => renderHook(() => useHealHistory(10))).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useHealHistory());
    expect(result.current.data).toBeUndefined();
  });

  it("isLoading is false by default", () => {
    const { result } = renderHook(() => useHealHistory());
    expect(result.current.isLoading).toBe(false);
  });
});

describe("useHealStats", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useHealStats())).not.toThrow();
  });

  it("data is undefined by default", () => {
    const { result } = renderHook(() => useHealStats());
    expect(result.current.data).toBeUndefined();
  });

  it("isLoading is false by default", () => {
    const { result } = renderHook(() => useHealStats());
    expect(result.current.isLoading).toBe(false);
  });

  it("returns non-null result object", () => {
    const { result } = renderHook(() => useHealStats());
    expect(result.current).not.toBeNull();
  });
});
