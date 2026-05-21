/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

// ── Suppress console errors ──────────────────────────────────────────────────
let consoleErrorSpy: jest.SpyInstance;
let consoleWarnSpy: jest.SpyInstance;

beforeAll(() => {
  consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
  consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});
});

afterAll(() => {
  consoleErrorSpy.mockRestore();
  consoleWarnSpy.mockRestore();
});

// ── Common mocks ──────────────────────────────────────────────────────────────
jest.mock("next/link", () =>
  function MockLink({ href, children, ...rest }: any) {
    return <a href={href} {...rest}>{children}</a>;
  }
);

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  useParams: () => ({}),
  usePathname: () => "/p/proj-1",
}));

jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

jest.mock("@/lib/api", () => ({ apiFetch: jest.fn(), ENGINE_BASE: "http://localhost:5001" }));

jest.mock("@/lib/api-client", () => ({
  apiFetch: jest.fn(),
  ENGINE_BASE: "http://localhost:5001",
}));

jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">
      {title}
      {right && <div>{right}</div>}
    </div>
  ),
  SectionCard: ({ title, children }: any) => (
    <div>
      {title && <div>{title}</div>}
      {children}
    </div>
  ),
  EmptyState: ({ title, description }: any) => (
    <div data-testid="empty-state">
      {title}
      {description && <p>{description}</p>}
    </div>
  ),
  StatCard: ({ label, value }: any) => (
    <div data-testid={`stat-${label}`}>{String(value)}</div>
  ),
  MetricRow: ({ children }: any) => <div>{children}</div>,
  ToolbarActions: ({ children }: any) => <div>{children}</div>,
  StatusBadge: ({ status }: any) => <span>{status}</span>,
  FilterBar: ({ children }: any) => <div>{children}</div>,
}));

jest.mock("@/components/FlowGuideCard", () => ({
  FlowGuideCard: () => <div data-testid="flow-guide-card" />,
}));

jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">
      {title}
      {right}
    </div>
  ),
}));

// ── Locator Intelligence hooks mock ──────────────────────────────────────────
jest.mock("@/lib/hooks/use-locator-intelligence", () => ({
  useFallbackResolve: jest.fn(),
  useStabilityAnalysis: jest.fn(),
  usePOMGenerate: jest.fn(),
  useBreakagePrediction: jest.fn(),
  useLocatorTrends: jest.fn(),
}));

// ── TanStack Query mock ───────────────────────────────────────────────────────
jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn(),
  useQueryClient: jest.fn(() => ({
    invalidateQueries: jest.fn(),
  })),
  useMutation: jest.fn(() => ({
    mutate: jest.fn(),
    isPending: false,
    isError: false,
    error: null,
  })),
}));

// ─────────────────────────────────────────────────────────────────────────────
// SECTION 1: DebugReportPage
// ─────────────────────────────────────────────────────────────────────────────

import DebugReportPage from "@/app/(dashboard)/p/[projectId]/debug-report/page";

const MOCK_EXECUTIONS = [
  { id: "exec-001", name: "Smoke Test Run", status: "completed", created_at: "2026-01-01T10:00:00Z" },
  { id: "exec-002", name: "Regression Suite", status: "completed", created_at: "2026-01-02T11:00:00Z" },
];

const MOCK_DEBUG_RESPONSE = {
  execution_id: "exec-001",
  overall_health: "at_risk",
  key_patterns: ["Timeout patterns detected", "Network instability"],
  recommended_actions: ["Increase timeout limits", "Add retry logic"],
  ai_provider: "claude",
  fallback_used: false,
  summary: {
    total: 10,
    passed: 7,
    failed: 3,
    skipped: 0,
    pass_rate: 70,
    health: "at_risk",
  },
  generated_at: "2026-01-01T12:00:00Z",
  allure_results: [],
  analyses: [
    {
      test_id: "test-abc",
      root_cause_category: "PRODUCT_BUG",
      root_cause_subcategory: "UI regression",
      confidence: 0.85,
      fix_steps: ["Check element selectors", "Run in headed mode"],
      estimated_fix_time: "2 hours",
      risk_level: "high",
      similar_tests_at_risk: ["test-xyz"],
      explanation: "Element locator changed after deployment",
    },
  ],
};

describe("DebugReportPage", () => {
  let fetchMock: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    fetchMock = jest.fn();
    global.fetch = fetchMock;
    // Default: executions load successfully
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => MOCK_EXECUTIONS,
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test("1. page renders without crashing", async () => {
    await act(async () => {
      render(<DebugReportPage />);
    });
    // The page root div is always present
    expect(document.querySelector(".min-h-screen")).toBeInTheDocument();
  });

  test("2. shows 'AI Debug Report' title in PageHeader", async () => {
    await act(async () => {
      render(<DebugReportPage />);
    });
    expect(screen.getByTestId("page-header")).toHaveTextContent("AI Debug Report");
  });

  test("3. calls fetch on mount to load executions", async () => {
    await act(async () => {
      render(<DebugReportPage />);
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/executions"),
        expect.objectContaining({ credentials: "include" })
      );
    });
  });

  test("4. shows execution options in select dropdown after load", async () => {
    await act(async () => {
      render(<DebugReportPage />);
    });
    await waitFor(() => {
      expect(screen.getByText(/Smoke Test Run/i)).toBeInTheDocument();
    });
  });

  test("5. shows FlowGuideCard and AI analyze button", async () => {
    await act(async () => {
      render(<DebugReportPage />);
    });
    expect(screen.getByTestId("flow-guide-card")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /AI Analizi Başlat/i })).toBeInTheDocument();
  });

  test("6. shows analysis results after clicking analyze button", async () => {
    // First call: executions list; second call: debug analysis
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => MOCK_EXECUTIONS,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => MOCK_DEBUG_RESPONSE,
      });

    await act(async () => {
      render(<DebugReportPage />);
    });

    // Wait for executions to load and button to become enabled
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /AI Analizi Başlat/i })).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /AI Analizi Başlat/i }));
    });

    await waitFor(() => {
      // The explanation text from the analysis should appear
      expect(screen.getByText("Element locator changed after deployment")).toBeInTheDocument();
    });
  });

  test("7. shows error message when debug API fails", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => MOCK_EXECUTIONS,
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Analiz başarısız" }),
        statusText: "Internal Server Error",
      });

    await act(async () => {
      render(<DebugReportPage />);
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /AI Analizi Başlat/i })).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /AI Analizi Başlat/i }));
    });

    await waitFor(() => {
      expect(screen.getByText(/Analiz başarısız/i)).toBeInTheDocument();
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// SECTION 2: LocatorsPage
// ─────────────────────────────────────────────────────────────────────────────

import LocatorsPage from "@/app/(dashboard)/p/[projectId]/locators/page";
import { useQuery } from "@tanstack/react-query";
import {
  useFallbackResolve,
  useStabilityAnalysis,
  usePOMGenerate,
  useBreakagePrediction,
  useLocatorTrends,
} from "@/lib/hooks/use-locator-intelligence";

const mockUseQuery = useQuery as jest.MockedFunction<typeof useQuery>;
const mockUseFallbackResolve = useFallbackResolve as jest.MockedFunction<typeof useFallbackResolve>;
const mockUseStabilityAnalysis = useStabilityAnalysis as jest.MockedFunction<typeof useStabilityAnalysis>;
const mockUsePOMGenerate = usePOMGenerate as jest.MockedFunction<typeof usePOMGenerate>;
const mockUseBreakagePrediction = useBreakagePrediction as jest.MockedFunction<typeof useBreakagePrediction>;
const mockUseLocatorTrends = useLocatorTrends as jest.MockedFunction<typeof useLocatorTrends>;

const MOCK_LOCATORS = [
  { id: "loc-1", name: "loginButton", selector: "[data-testid='login']", type: "testid", page: "Login", status: "healthy" },
  { id: "loc-2", name: "submitForm", selector: "#submit-btn", type: "css", page: "Login", status: "broken" },
  { id: "loc-3", name: "headerTitle", selector: "//h1[@class='title']", type: "xpath", page: "Home", status: "warning" },
];

function setupLocatorMocks(overrides: { data?: any; isLoading?: boolean } = {}) {
  const idleMutation = {
    mutate: jest.fn(),
    isPending: false,
    isError: false,
    error: null,
  } as any;

  mockUseQuery.mockReturnValue({
    data: overrides.data !== undefined ? overrides.data : MOCK_LOCATORS,
    isLoading: overrides.isLoading ?? false,
    isError: false,
    error: null,
  } as any);

  mockUseFallbackResolve.mockReturnValue(idleMutation);
  mockUseStabilityAnalysis.mockReturnValue(idleMutation);
  mockUsePOMGenerate.mockReturnValue(idleMutation);
  mockUseBreakagePrediction.mockReturnValue(idleMutation);
  mockUseLocatorTrends.mockReturnValue({ data: undefined, isLoading: false } as any);
}

describe("LocatorsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupLocatorMocks();
  });

  test("1. page renders with data-testid='locators-page'", () => {
    render(<LocatorsPage />);
    expect(screen.getByTestId("locators-page")).toBeInTheDocument();
  });

  test("2. shows 'Locator Zekasi' title in PageHeader", () => {
    render(<LocatorsPage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Locator Zekasi");
  });

  test("3. renders all five tab buttons", () => {
    render(<LocatorsPage />);
    expect(screen.getByTestId("tab-management")).toBeInTheDocument();
    expect(screen.getByTestId("tab-stability")).toBeInTheDocument();
    expect(screen.getByTestId("tab-fallback")).toBeInTheDocument();
    expect(screen.getByTestId("tab-pom")).toBeInTheDocument();
    expect(screen.getByTestId("tab-breakage")).toBeInTheDocument();
  });

  test("4. management tab shows locators table with data-testid='locators-table'", () => {
    render(<LocatorsPage />);
    expect(screen.getByTestId("locators-table")).toBeInTheDocument();
    // locator names appear in the table
    expect(screen.getByText("loginButton")).toBeInTheDocument();
    expect(screen.getByText("submitForm")).toBeInTheDocument();
  });

  test("5. loading state shows spinner text instead of table", () => {
    setupLocatorMocks({ data: undefined, isLoading: true });
    render(<LocatorsPage />);
    expect(screen.getByText(/Yükleniyor/i)).toBeInTheDocument();
    expect(screen.queryByTestId("locators-table")).not.toBeInTheDocument();
  });

  test("6. empty state shown when no locators exist", () => {
    setupLocatorMocks({ data: [] });
    render(<LocatorsPage />);
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByText(/Henuz locator yok/i)).toBeInTheDocument();
  });

  test("7. clicking Stability tab switches tab content", () => {
    render(<LocatorsPage />);
    fireEvent.click(screen.getByTestId("tab-stability"));
    // The stability tab description text should appear
    expect(
      screen.getByText(/stabilite analizi/i)
    ).toBeInTheDocument();
  });
});
