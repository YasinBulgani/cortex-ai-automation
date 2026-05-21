/** @jest-environment jsdom */
import { renderHook } from "@testing-library/react";

// ── Mock: @tanstack/react-query ──────────────────────────────────────────────
jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn(),
  useMutation: jest.fn(),
  useQueryClient: jest.fn(() => ({
    invalidateQueries: jest.fn(),
    setQueryData: jest.fn(),
  })),
}));

import { useQuery, useMutation } from "@tanstack/react-query";

// ── Mock: @/lib/dsl-api ───────────────────────────────────────────────────────
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
    getAction: jest.fn(),
    listStats: jest.fn(),
    listActions: jest.fn(),
    search: jest.fn(),
    listCategories: jest.fn(),
  },
}));

// ── Mock: @/lib/api-client ────────────────────────────────────────────────────
jest.mock("@/lib/api-client", () => ({
  apiFetch: jest.fn(),
}));

// ── Imports under test ────────────────────────────────────────────────────────
import {
  dslKeys,
  useDslAction,
  useDslSuggest,
  useDslIndexInfo,
  useDslEditorConfig,
  useDslDeprecateAction,
  useDslProposals,
  useDslProposal,
  useDslApproveProposal,
  useDslRejectProposal,
  useDslGenerateAiAliases,
  useDslAudit,
} from "../hooks/use-dsl";

// ── Default mock return values ────────────────────────────────────────────────
beforeEach(() => {
  jest.clearAllMocks();
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

// ── dslKeys query key factory ──────────────────────────────────────────────────

describe("dslKeys", () => {
  it("dslKeys.all is ['dsl']", () => {
    expect(dslKeys.all).toEqual(["dsl"]);
  });

  it("dslKeys.stats() contains 'stats'", () => {
    expect(dslKeys.stats()).toEqual(["dsl", "stats"]);
  });

  it("dslKeys.categories() contains 'categories'", () => {
    expect(dslKeys.categories()).toEqual(["dsl", "categories"]);
  });

  it("dslKeys.actions() contains 'actions'", () => {
    expect(dslKeys.actions()).toEqual(["dsl", "actions"]);
  });

  it("dslKeys.actionList includes filters object", () => {
    const filters = { category: "ui", page: 2, page_size: 20 };
    const key = dslKeys.actionList(filters);
    expect(key).toContain("list");
    expect(key).toContainEqual(filters);
  });

  it("dslKeys.actionDetail includes action id", () => {
    const key = dslKeys.actionDetail("my-action");
    expect(key).toContain("my-action");
    expect(key).toContain("detail");
  });

  it("dslKeys.search includes query and lang", () => {
    const key = dslKeys.search("click element", "tr");
    expect(key).toContain("search");
    expect(key).toContain("click element");
    expect(key).toContain("tr");
  });

  it("dslKeys.search uses 'all' when lang is omitted", () => {
    const key = dslKeys.search("find element");
    expect(key).toContain("all");
  });

  it("dslKeys.suggest includes mode and query", () => {
    const key = dslKeys.suggest("tıkla", "auto");
    expect(key).toContain("suggest");
    expect(key).toContain("auto");
    expect(key).toContain("tıkla");
  });

  it("dslKeys.indexInfo returns correct shape", () => {
    expect(dslKeys.indexInfo()).toEqual(["dsl", "index-info"]);
  });

  it("dslKeys.editorConfig returns correct shape", () => {
    expect(dslKeys.editorConfig()).toEqual(["dsl", "editor-config"]);
  });

  it("dslKeys.proposals includes filters object", () => {
    const filters = { status: "pending" as const };
    const key = dslKeys.proposals(filters);
    expect(key).toContain("proposals");
    expect(key).toContainEqual(filters);
  });

  it("dslKeys.proposals uses empty object when no filters given", () => {
    const key = dslKeys.proposals();
    expect(key).toContain("proposals");
  });

  it("dslKeys.proposalDetail includes proposal id", () => {
    const key = dslKeys.proposalDetail("prop-xyz");
    expect(key).toContain("prop-xyz");
    expect(key).toContain("detail");
  });

  it("dslKeys.audit uses 'all' when no action_id given", () => {
    const key = dslKeys.audit();
    expect(key).toEqual(["dsl", "audit", "all"]);
  });

  it("dslKeys.audit includes action_id when provided", () => {
    const key = dslKeys.audit("action-123");
    expect(key).toEqual(["dsl", "audit", "action-123"]);
  });
});

// ── useDslAction ───────────────────────────────────────────────────────────────

describe("useDslAction", () => {
  it("renders without throwing when actionId is provided", () => {
    expect(() => renderHook(() => useDslAction("action-1"))).not.toThrow();
  });

  it("renders without throwing when actionId is undefined", () => {
    expect(() => renderHook(() => useDslAction(undefined))).not.toThrow();
  });

  it("returns data=undefined from mocked useQuery", () => {
    const { result } = renderHook(() => useDslAction("action-1"));
    expect(result.current.data).toBeUndefined();
  });

  it("returns isLoading=false from mocked useQuery", () => {
    const { result } = renderHook(() => useDslAction("action-1"));
    expect(result.current.isLoading).toBe(false);
  });

  it("useQuery is called once per hook render", () => {
    renderHook(() => useDslAction("action-abc"));
    expect(useQuery).toHaveBeenCalledTimes(1);
  });
});

// ── useDslSuggest ──────────────────────────────────────────────────────────────

describe("useDslSuggest", () => {
  it("renders without throwing with a description string", () => {
    expect(() => renderHook(() => useDslSuggest("tıkla"))).not.toThrow();
  });

  it("renders without throwing with empty description", () => {
    expect(() => renderHook(() => useDslSuggest(""))).not.toThrow();
  });

  it("accepts mode, limit, enabled, minLength options", () => {
    expect(() =>
      renderHook(() =>
        useDslSuggest("kaydet", { mode: "hybrid", limit: 5, enabled: true, minLength: 2 })
      )
    ).not.toThrow();
  });

  it("returns data=undefined from mocked useQuery", () => {
    const { result } = renderHook(() => useDslSuggest("tıkla düğme"));
    expect(result.current.data).toBeUndefined();
  });

  it("returns isLoading=false from mocked useQuery", () => {
    const { result } = renderHook(() => useDslSuggest("tıkla"));
    expect(result.current.isLoading).toBe(false);
  });
});

// ── useDslIndexInfo ────────────────────────────────────────────────────────────

describe("useDslIndexInfo", () => {
  it("renders without throwing with default enabled=true", () => {
    expect(() => renderHook(() => useDslIndexInfo())).not.toThrow();
  });

  it("renders without throwing when enabled=false", () => {
    expect(() => renderHook(() => useDslIndexInfo(false))).not.toThrow();
  });

  it("returns data=undefined from mocked useQuery", () => {
    const { result } = renderHook(() => useDslIndexInfo());
    expect(result.current.data).toBeUndefined();
  });

  it("returns isLoading=false from mocked useQuery", () => {
    const { result } = renderHook(() => useDslIndexInfo());
    expect(result.current.isLoading).toBe(false);
  });
});

// ── useDslEditorConfig ─────────────────────────────────────────────────────────

describe("useDslEditorConfig", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useDslEditorConfig())).not.toThrow();
  });

  it("returns data=undefined from mocked useQuery", () => {
    const { result } = renderHook(() => useDslEditorConfig());
    expect(result.current.data).toBeUndefined();
  });

  it("returns isLoading=false from mocked useQuery", () => {
    const { result } = renderHook(() => useDslEditorConfig());
    expect(result.current.isLoading).toBe(false);
  });

  it("useQuery is called once per render", () => {
    renderHook(() => useDslEditorConfig());
    expect(useQuery).toHaveBeenCalled();
  });
});

// ── useDslDeprecateAction ──────────────────────────────────────────────────────

describe("useDslDeprecateAction", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useDslDeprecateAction())).not.toThrow();
  });

  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useDslDeprecateAction());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns object with mutateAsync function", () => {
    const { result } = renderHook(() => useDslDeprecateAction());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useDslDeprecateAction());
    expect(result.current.isPending).toBe(false);
  });
});

// ── useDslProposals ────────────────────────────────────────────────────────────

describe("useDslProposals", () => {
  it("renders without throwing with no filters", () => {
    expect(() => renderHook(() => useDslProposals())).not.toThrow();
  });

  it("renders without throwing with status filter", () => {
    expect(() => renderHook(() => useDslProposals({ status: "pending" }))).not.toThrow();
  });

  it("renders without throwing with action_id filter", () => {
    expect(() => renderHook(() => useDslProposals({ action_id: "act-1" }))).not.toThrow();
  });

  it("returns data=undefined from mocked useQuery", () => {
    const { result } = renderHook(() => useDslProposals());
    expect(result.current.data).toBeUndefined();
  });

  it("returns isLoading=false from mocked useQuery", () => {
    const { result } = renderHook(() => useDslProposals({ limit: 10 }));
    expect(result.current.isLoading).toBe(false);
  });
});

// ── useDslProposal ─────────────────────────────────────────────────────────────

describe("useDslProposal", () => {
  it("renders without throwing when proposalId is provided", () => {
    expect(() => renderHook(() => useDslProposal("prop-1"))).not.toThrow();
  });

  it("renders without throwing when proposalId is undefined", () => {
    expect(() => renderHook(() => useDslProposal(undefined))).not.toThrow();
  });

  it("returns data=undefined from mocked useQuery", () => {
    const { result } = renderHook(() => useDslProposal("prop-1"));
    expect(result.current.data).toBeUndefined();
  });

  it("returns isLoading=false from mocked useQuery", () => {
    const { result } = renderHook(() => useDslProposal("prop-1"));
    expect(result.current.isLoading).toBe(false);
  });
});

// ── useDslApproveProposal ──────────────────────────────────────────────────────

describe("useDslApproveProposal", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useDslApproveProposal())).not.toThrow();
  });

  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useDslApproveProposal());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns object with mutateAsync function", () => {
    const { result } = renderHook(() => useDslApproveProposal());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useDslApproveProposal());
    expect(result.current.isPending).toBe(false);
  });
});

// ── useDslRejectProposal ───────────────────────────────────────────────────────

describe("useDslRejectProposal", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useDslRejectProposal())).not.toThrow();
  });

  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useDslRejectProposal());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns object with mutateAsync function", () => {
    const { result } = renderHook(() => useDslRejectProposal());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useDslRejectProposal());
    expect(result.current.isPending).toBe(false);
  });
});

// ── useDslGenerateAiAliases ────────────────────────────────────────────────────

describe("useDslGenerateAiAliases", () => {
  it("renders without throwing", () => {
    expect(() => renderHook(() => useDslGenerateAiAliases())).not.toThrow();
  });

  it("returns object with mutate function", () => {
    const { result } = renderHook(() => useDslGenerateAiAliases());
    expect(typeof result.current.mutate).toBe("function");
  });

  it("returns object with mutateAsync function", () => {
    const { result } = renderHook(() => useDslGenerateAiAliases());
    expect(typeof result.current.mutateAsync).toBe("function");
  });

  it("isPending defaults to false", () => {
    const { result } = renderHook(() => useDslGenerateAiAliases());
    expect(result.current.isPending).toBe(false);
  });
});

// ── useDslAudit ────────────────────────────────────────────────────────────────

describe("useDslAudit", () => {
  it("renders without throwing with no arguments", () => {
    expect(() => renderHook(() => useDslAudit())).not.toThrow();
  });

  it("renders without throwing with action_id", () => {
    expect(() => renderHook(() => useDslAudit("action-123"))).not.toThrow();
  });

  it("renders without throwing with action_id and custom limit", () => {
    expect(() => renderHook(() => useDslAudit("action-123", 50))).not.toThrow();
  });

  it("returns data=undefined from mocked useQuery", () => {
    const { result } = renderHook(() => useDslAudit());
    expect(result.current.data).toBeUndefined();
  });

  it("returns isLoading=false from mocked useQuery", () => {
    const { result } = renderHook(() => useDslAudit("action-123", 20));
    expect(result.current.isLoading).toBe(false);
  });
});
