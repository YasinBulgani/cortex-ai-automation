/** @jest-environment jsdom */
import { renderHook } from "@testing-library/react";

jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn(() => ({ data: undefined, isLoading: false, error: null, refetch: jest.fn() })),
  useMutation: jest.fn(() => ({ mutate: jest.fn(), mutateAsync: jest.fn(), isPending: false, error: null })),
  useQueryClient: jest.fn(() => ({ invalidateQueries: jest.fn() })),
}));

jest.mock("@/lib/api-client", () => ({
  apiFetch: jest.fn(),
  getToken: jest.fn(() => "tok"),
}));

import { useQuery, useMutation } from "@tanstack/react-query";
import {
  useNLGenerate,
  useNLBatchGenerate,
  useNLSuggestions,
  useKDEFit,
  useKDEGenerate,
  useCTGANTrain,
  useCTGANGenerate,
  useSyntheticQuality,
  useBankingDataset,
  usePrivacyAudit,
  useAnonymize,
  useAddNoise,
  usePrivacyReport,
} from "../hooks/use-synthetic-advanced";

beforeEach(() => {
  jest.clearAllMocks();
  (useQuery as jest.Mock).mockReturnValue({ data: undefined, isLoading: false, error: null, refetch: jest.fn() });
  (useMutation as jest.Mock).mockReturnValue({ mutate: jest.fn(), mutateAsync: jest.fn(), isPending: false, error: null });
});

// ── Mutation hooks ─────────────────────────────────────────────────────────────

describe("useNLGenerate", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => useNLGenerate("proj-1"))).not.toThrow();
  });
  it("returns mutation functions", () => {
    const { result } = renderHook(() => useNLGenerate("proj-1"));
    expect(typeof result.current.mutate === "function" || typeof result.current.mutateAsync === "function").toBe(true);
  });
});

describe("useNLBatchGenerate", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => useNLBatchGenerate("proj-1"))).not.toThrow();
  });
  it("returns mutation object", () => {
    const { result } = renderHook(() => useNLBatchGenerate("proj-1"));
    expect(result.current).toBeDefined();
  });
});

describe("useNLSuggestions", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => useNLSuggestions("proj-1"))).not.toThrow();
  });
  it("returns mutation object", () => {
    const { result } = renderHook(() => useNLSuggestions("proj-1"));
    expect(result.current).toBeDefined();
  });
});

describe("useKDEFit", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => useKDEFit("proj-1"))).not.toThrow();
  });
  it("returns mutation", () => {
    const { result } = renderHook(() => useKDEFit("proj-1"));
    expect(result.current).toBeDefined();
  });
});

describe("useKDEGenerate", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => useKDEGenerate("proj-1"))).not.toThrow();
  });
  it("returns mutation", () => {
    const { result } = renderHook(() => useKDEGenerate("proj-1"));
    expect(result.current).toBeDefined();
  });
});

describe("useCTGANTrain", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => useCTGANTrain("proj-1"))).not.toThrow();
  });
  it("returns mutation", () => {
    const { result } = renderHook(() => useCTGANTrain("proj-1"));
    expect(result.current).toBeDefined();
  });
});

describe("useCTGANGenerate", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => useCTGANGenerate("proj-1"))).not.toThrow();
  });
  it("returns mutation", () => {
    const { result } = renderHook(() => useCTGANGenerate("proj-1"));
    expect(result.current).toBeDefined();
  });
});

describe("useSyntheticQuality", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => useSyntheticQuality("proj-1"))).not.toThrow();
  });
  it("returns mutation", () => {
    const { result } = renderHook(() => useSyntheticQuality("proj-1"));
    expect(result.current).toBeDefined();
  });
});

describe("useBankingDataset", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => useBankingDataset("proj-1"))).not.toThrow();
  });
  it("returns mutation", () => {
    const { result } = renderHook(() => useBankingDataset("proj-1"));
    expect(result.current).toBeDefined();
  });
});

describe("usePrivacyAudit", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => usePrivacyAudit("proj-1"))).not.toThrow();
  });
  it("returns mutation", () => {
    const { result } = renderHook(() => usePrivacyAudit("proj-1"));
    expect(result.current).toBeDefined();
  });
});

describe("useAnonymize", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => useAnonymize("proj-1"))).not.toThrow();
  });
  it("returns mutation", () => {
    const { result } = renderHook(() => useAnonymize("proj-1"));
    expect(result.current).toBeDefined();
  });
});

describe("useAddNoise", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => useAddNoise("proj-1"))).not.toThrow();
  });
  it("returns mutation", () => {
    const { result } = renderHook(() => useAddNoise("proj-1"));
    expect(result.current).toBeDefined();
  });
});

describe("usePrivacyReport", () => {
  it("does not throw", () => {
    expect(() => renderHook(() => usePrivacyReport("proj-1"))).not.toThrow();
  });
  it("returns query result", () => {
    const { result } = renderHook(() => usePrivacyReport("proj-1"));
    expect(result.current.data).toBeUndefined();
    expect(result.current.isLoading).toBe(false);
  });
  it("accepts projectId parameter", () => {
    expect(() => renderHook(() => usePrivacyReport("some-project-id"))).not.toThrow();
  });
});
