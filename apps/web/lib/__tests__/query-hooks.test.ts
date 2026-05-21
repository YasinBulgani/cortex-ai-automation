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

import {
  useQuery,
  useMutation,
  useInfiniteQuery,
} from "@tanstack/react-query";

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

// ── Mock: @/lib/dsl-api (used by use-dsl) ────────────────────────────────────
jest.mock("@/lib/dsl-api", () => ({
  dslApi: {
    suggest: jest.fn(),
    indexInfo: jest.fn(),
    feedback: jest.fn(),
    editorConfig: jest.fn(),
    createAction: jest.fn(),
    updateAction: jest.fn(),
    deleteAction: jest.fn(),
    deprecateAction: jest.fn(),
    listProposals: jest.fn(),
    getProposal: jest.fn(),
    approveProposal: jest.fn(),
    rejectProposal: jest.fn(),
    generateAiAliases: jest.fn(),
    listAudit: jest.fn(),
  },
}));

// ── Imports under test ────────────────────────────────────────────────────────
import {
  useProjects,
  useProject,
  useProjectStats,
  useCreateProject,
  useUpdateProject,
  useDeleteProject,
} from "../hooks/use-projects";

import {
  useScenarios,
  useScenario,
  useScenariosInfinite,
  useCreateScenario,
  useUpdateScenario,
  useDeleteScenario,
} from "../hooks/use-scenarios";

import {
  useDslStats,
  useDslCategories,
  useDslActions,
  useDslSearch,
  useDslFeedback,
  useDslCreateAction,
  useDslUpdateAction,
  useDslDeleteAction,
} from "../hooks/use-dsl";

import {
  useCurrentUser,
  useLogin,
  useLogout,
} from "../hooks/use-auth";

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
  (useInfiniteQuery as jest.Mock).mockReturnValue({
    data: undefined,
    isLoading: false,
    error: null,
    fetchNextPage: jest.fn(),
    hasNextPage: false,
  });
});

// ── use-projects ──────────────────────────────────────────────────────────────

describe("useProjects", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useProjects())).not.toThrow();
  });

  it("returns a non-null result object", () => {
    const { result } = renderHook(() => useProjects());
    expect(result.current).not.toBeNull();
  });

  it("exposes isLoading=false from mocked useQuery", () => {
    const { result } = renderHook(() => useProjects());
    expect(result.current.isLoading).toBe(false);
  });

  it("exposes data=undefined from mocked useQuery", () => {
    const { result } = renderHook(() => useProjects());
    expect(result.current.data).toBeUndefined();
  });

  it("useProject renders without throwing when projectId is provided", () => {
    expect(() => renderHook(() => useProject("proj-123"))).not.toThrow();
  });

  it("useProjectStats renders without throwing when projectId is provided", () => {
    expect(() => renderHook(() => useProjectStats("proj-123"))).not.toThrow();
  });
});

describe("useCreateProject", () => {
  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useCreateProject());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns object with mutateAsync function", () => {
    const { result } = renderHook(() => useCreateProject());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useCreateProject());
    expect(result.current.isPending).toBe(false);
  });
});

describe("useUpdateProject", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useUpdateProject("proj-1"))).not.toThrow();
  });

  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useUpdateProject("proj-1"));
    expect(typeof result.current.mutate).toBe("function");
  });
});

describe("useDeleteProject", () => {
  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useDeleteProject());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns object with mutateAsync function", () => {
    const { result } = renderHook(() => useDeleteProject());
    expect(typeof result.current.mutateAsync).toBe("function");
  });
});

// ── use-scenarios ─────────────────────────────────────────────────────────────

describe("useScenarios", () => {
  it("renders without throwing when projectId is provided", () => {
    expect(() => renderHook(() => useScenarios("proj-1"))).not.toThrow();
  });

  it("returns non-null result object", () => {
    const { result } = renderHook(() => useScenarios("proj-1"));
    expect(result.current).not.toBeNull();
  });

  it("data is undefined before any fetch", () => {
    const { result } = renderHook(() => useScenarios("proj-1"));
    expect(result.current.data).toBeUndefined();
  });

  it("renders without throwing when projectId is undefined", () => {
    expect(() => renderHook(() => useScenarios(undefined))).not.toThrow();
  });

  it("useScenario renders without throwing when scenarioId is provided", () => {
    expect(() => renderHook(() => useScenario("scen-abc"))).not.toThrow();
  });
});

describe("useCreateScenario", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useCreateScenario("proj-1"))).not.toThrow();
  });

  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useCreateScenario("proj-1"));
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns object with mutateAsync function", () => {
    const { result } = renderHook(() => useCreateScenario("proj-1"));
    expect(typeof result.current.mutateAsync).toBe("function");
  });
});

describe("useUpdateScenario / useDeleteScenario", () => {
  it("useUpdateScenario returns mutate function", () => {
    const { result } = renderHook(() => useUpdateScenario("scen-1"));
    expect(typeof result.current.mutate).toBe("function");
  });

  it("useDeleteScenario returns mutate function", () => {
    const { result } = renderHook(() => useDeleteScenario());
    expect(typeof result.current.mutate).toBe("function");
  });
});

// ── use-dsl ───────────────────────────────────────────────────────────────────

describe("useDslStats", () => {
  it("renders without crash", () => {
    expect(() => renderHook(() => useDslStats())).not.toThrow();
  });

  it("data is undefined before fetch", () => {
    const { result } = renderHook(() => useDslStats());
    expect(result.current.data).toBeUndefined();
  });
});

describe("useDslCategories", () => {
  it("renders without crash", () => {
    expect(() => renderHook(() => useDslCategories())).not.toThrow();
  });

  it("isLoading defaults to false (mocked)", () => {
    const { result } = renderHook(() => useDslCategories());
    expect(result.current.isLoading).toBe(false);
  });
});

describe("useDslActions", () => {
  it("renders without crash (no filters)", () => {
    expect(() => renderHook(() => useDslActions())).not.toThrow();
  });

  it("renders without crash (with category filter)", () => {
    expect(() => renderHook(() => useDslActions({ category: "ui" }))).not.toThrow();
  });

  it("data is undefined before fetch", () => {
    const { result } = renderHook(() => useDslActions());
    expect(result.current.data).toBeUndefined();
  });
});

describe("useDslSearch", () => {
  it("renders without crash", () => {
    expect(() => renderHook(() => useDslSearch("test"))).not.toThrow();
  });

  it("returns non-null result", () => {
    const { result } = renderHook(() => useDslSearch("test"));
    expect(result.current).not.toBeNull();
  });
});

describe("useDslFeedback", () => {
  it("renders without crash", () => {
    expect(() => renderHook(() => useDslFeedback())).not.toThrow();
  });

  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useDslFeedback());
    expect(typeof result.current.mutate).toBe("function");
  });
});

describe("useDslCreateAction", () => {
  it("renders without crash", () => {
    expect(() => renderHook(() => useDslCreateAction())).not.toThrow();
  });

  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useDslCreateAction());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns object with mutateAsync function", () => {
    const { result } = renderHook(() => useDslCreateAction());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useDslCreateAction());
    expect(result.current.isPending).toBe(false);
  });
});

describe("useDslUpdateAction / useDslDeleteAction", () => {
  it("useDslUpdateAction returns mutate function", () => {
    const { result } = renderHook(() => useDslUpdateAction());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("useDslDeleteAction returns mutate function", () => {
    const { result } = renderHook(() => useDslDeleteAction());
    expect(typeof result.current.mutate).toBe("function");
  });
});

// ── use-auth ──────────────────────────────────────────────────────────────────

describe("useCurrentUser", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useCurrentUser())).not.toThrow();
  });

  it("user is null when useQuery returns data: undefined", () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.user).toBeNull();
  });

  it("loading is false when useQuery returns isLoading: false", () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.loading).toBe(false);
  });

  it("error is null when useQuery returns error: null", () => {
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
    expect(result.current.hasPermission("admin.*")).toBe(false);
  });

  it("hasPermission returns false for any perm when user is null", () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.hasPermission("scenarios.create")).toBe(false);
  });

  it("hasPermission returns true when user has admin.* permission", () => {
    (useQuery as jest.Mock).mockReturnValueOnce({
      data: { id: "u1", email: "admin@example.com", roles: ["admin"], permissions: ["admin.*"] },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.hasPermission("any.permission")).toBe(true);
  });

  it("hasPermission returns true when user has exact matching permission", () => {
    (useQuery as jest.Mock).mockReturnValueOnce({
      data: {
        id: "u2",
        email: "user@example.com",
        roles: ["qa"],
        permissions: ["scenarios.create", "scenarios.read"],
      },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.hasPermission("scenarios.create")).toBe(true);
  });

  it("hasPermission returns false when user lacks the specific permission", () => {
    (useQuery as jest.Mock).mockReturnValueOnce({
      data: {
        id: "u3",
        email: "readonly@example.com",
        roles: ["viewer"],
        permissions: ["scenarios.read"],
      },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.hasPermission("scenarios.delete")).toBe(false);
  });

  it("loading is true when useQuery returns isLoading: true", () => {
    (useQuery as jest.Mock).mockReturnValueOnce({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: jest.fn(),
    });
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.loading).toBe(true);
  });

  it("error surfaces the message string from query.error", () => {
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

describe("useLogin", () => {
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

describe("useLogout", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useLogout())).not.toThrow();
  });

  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useLogout());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns object with mutateAsync function", () => {
    const { result } = renderHook(() => useLogout());
    expect(typeof result.current.mutateAsync).toBe("function");
  });
});

// ── useScenariosInfinite ───────────────────────────────────────────────────────

describe("useScenariosInfinite", () => {
  it("renders without throwing when projectId is provided", () => {
    expect(() =>
      renderHook(() => useScenariosInfinite("proj-1"))
    ).not.toThrow();
  });

  it("renders without throwing when projectId is undefined", () => {
    expect(() =>
      renderHook(() => useScenariosInfinite(undefined))
    ).not.toThrow();
  });

  it("returns data=undefined from mocked useInfiniteQuery", () => {
    const { result } = renderHook(() => useScenariosInfinite("proj-1"));
    expect(result.current.data).toBeUndefined();
  });

  it("returns isLoading=false from mocked useInfiniteQuery", () => {
    const { result } = renderHook(() => useScenariosInfinite("proj-1"));
    expect(result.current.isLoading).toBe(false);
  });

  it("returns hasNextPage=false from mocked useInfiniteQuery", () => {
    const { result } = renderHook(() => useScenariosInfinite("proj-2"));
    expect(result.current.hasNextPage).toBe(false);
  });

  it("returns fetchNextPage function", () => {
    const { result } = renderHook(() => useScenariosInfinite("proj-3"));
    expect(typeof result.current.fetchNextPage).toBe("function");
  });

  it("useInfiniteQuery is called per render", () => {
    renderHook(() => useScenariosInfinite("proj-abc"));
    expect(useInfiniteQuery).toHaveBeenCalled();
  });
});
