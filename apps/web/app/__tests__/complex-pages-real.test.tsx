/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// ── Suppress noise ─────────────────────────────────────────────────────────
const consoleSpies: jest.SpyInstance[] = [];
beforeEach(() => {
  consoleSpies.push(jest.spyOn(console, "error").mockImplementation(() => {}));
  consoleSpies.push(jest.spyOn(console, "warn").mockImplementation(() => {}));
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
  (global as any).navigator = { clipboard: { writeText: jest.fn() } };
});
afterEach(() => {
  consoleSpies.forEach((s) => s.mockRestore());
  consoleSpies.length = 0;
  jest.clearAllMocks();
});

// ── Common mocks ───────────────────────────────────────────────────────────
jest.mock("next/link", () =>
  function MockLink({ href, children, ...rest }: any) {
    return <a href={href} {...rest}>{children}</a>;
  }
);
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn() }),
  useParams: () => ({}),
  usePathname: () => "/p/proj-1",
}));
jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

const apiFetchMock = jest.fn();
jest.mock("@/lib/api", () => ({
  apiFetch: (...args: any[]) => apiFetchMock(...args),
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

// Nexus components
jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title }: any) => <div data-testid="page-header">{title}</div>,
}));
jest.mock("@/components/nexus/SectionCard", () => ({
  SectionCard: ({ title, children, right }: any) => (
    <div data-testid="section-card">
      {title && <div>{title}</div>}
      {right && <div>{right}</div>}
      {children}
    </div>
  ),
}));
jest.mock("@/components/nexus/EmptyState", () => ({
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
}));
jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title }: any) => <div data-testid="page-header">{title}</div>,
  SectionCard: ({ title, children, right }: any) => (
    <div data-testid="section-card">
      {title && <div>{title}</div>}
      {right && <div>{right}</div>}
      {children}
    </div>
  ),
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
  StatCard: ({ label, value }: any) => <div data-testid={`stat-${label}`}>{String(value)}</div>,
  MetricRow: ({ children }: any) => <div>{children}</div>,
  ToolbarActions: ({ children }: any) => <div>{children}</div>,
  StatusBadge: ({ status }: any) => <span>{status}</span>,
  FilterBar: ({ children }: any) => <div>{children}</div>,
}));
jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, disabled, ...rest }: any) => (
    <button onClick={onClick} disabled={disabled} {...rest}>{children}</button>
  ),
}));
jest.mock("@/components/ui/input", () => ({
  Input: (props: any) => <input {...props} />,
}));
jest.mock("@/components/ui/badge", () => ({
  Badge: ({ children }: any) => <span className="badge">{children}</span>,
}));

// ── use-api-testing mock ───────────────────────────────────────────────────
jest.mock("@/lib/hooks/use-api-testing", () => ({
  useApiSpecs: jest.fn(),
  useApiEndpoints: jest.fn(),
  useApiTestCases: jest.fn(),
  useApiTestingStats: jest.fn(),
  useImportSpec: jest.fn(),
  useAiGenerate: jest.fn(),
  useExecuteTestCases: jest.fn(),
  useExecuteSingle: jest.fn(),
  useCoverageAnalysis: jest.fn(),
  useCoverageGaps: jest.fn(),
  useCoverageGapSuggestions: jest.fn(),
}));

// ── use-coverup mock ───────────────────────────────────────────────────────
jest.mock("@/lib/hooks/use-coverup", () => ({
  useUploadCoverage: jest.fn(),
  useAnalyzeCoverage: jest.fn(),
  useGenerateTests: jest.fn(),
  useCoverageReports: jest.fn(),
  useCoverageTrends: jest.fn(),
  useBankingTargets: jest.fn(),
}));

// ─── ApiTestingPage ────────────────────────────────────────────────────────

describe("ApiTestingPage", () => {
  beforeEach(() => {
    const m = require("@/lib/hooks/use-api-testing");
    (m.useApiSpecs as jest.Mock).mockReturnValue({ data: [], isLoading: false });
    (m.useApiEndpoints as jest.Mock).mockReturnValue({ data: [], isLoading: false });
    (m.useApiTestCases as jest.Mock).mockReturnValue({ data: [], isLoading: false });
    (m.useApiTestingStats as jest.Mock).mockReturnValue({ data: null });
    (m.useImportSpec as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false, error: null });
    (m.useAiGenerate as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false, data: null, error: null });
    (m.useExecuteTestCases as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false, data: null });
    (m.useExecuteSingle as jest.Mock).mockReturnValue({ mutate: jest.fn() });
  });

  it("renders data-testid='api-testing-page'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/api-testing/page");
    render(<Page />);
    expect(screen.getByTestId("api-testing-page")).toBeInTheDocument();
  });

  it("shows 'API Testing Intelligence' title", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/api-testing/page");
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("API Testing Intelligence");
  });

  it("renders 'Endpoints' tab button", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/api-testing/page");
    render(<Page />);
    expect(screen.getByText("Endpoints")).toBeInTheDocument();
  });

  it("renders 'Test Cases' tab button", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/api-testing/page");
    render(<Page />);
    expect(screen.getByText("Test Cases")).toBeInTheDocument();
  });

  it("shows ai-generate-btn on default endpoints tab", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/api-testing/page");
    render(<Page />);
    expect(screen.getByTestId("ai-generate-btn")).toBeInTheDocument();
  });

  it("shows 'Endpoint Envanteri' section when on endpoints tab", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/api-testing/page");
    render(<Page />);
    expect(screen.getByText("Endpoint Envanteri")).toBeInTheDocument();
  });

  it("shows endpoint-table when endpoints exist", async () => {
    const m = require("@/lib/hooks/use-api-testing");
    (m.useApiEndpoints as jest.Mock).mockReturnValue({
      data: [
        {
          id: "ep-1",
          method: "GET",
          path: "/users",
          risk_level: "medium",
          test_case_count: 2,
          has_pii: false,
          has_financial: false,
          compliance_tags: [],
          parameters: [],
          summary: "Get users",
          spec_id: "spec-1",
        },
      ],
      isLoading: false,
    });
    const { default: Page } = await import("../(dashboard)/p/[projectId]/api-testing/page");
    render(<Page />);
    expect(screen.getByTestId("endpoint-table")).toBeInTheDocument();
    expect(screen.getByText("/users")).toBeInTheDocument();
  });

  it("shows run-tests-btn after switching to Test Cases tab with test data", async () => {
    const m = require("@/lib/hooks/use-api-testing");
    (m.useApiTestCases as jest.Mock).mockReturnValue({
      data: [
        {
          id: "tc-1",
          title: "GET /users testi",
          test_type: "positive",
          priority: "P1",
          request_method: "GET",
          request_path: "/users",
          last_run_status: "pass",
          ai_generated: true,
          assertions: [],
          request_headers: {},
          request_body: null,
        },
      ],
      isLoading: false,
    });
    const { default: Page } = await import("../(dashboard)/p/[projectId]/api-testing/page");
    render(<Page />);
    fireEvent.click(screen.getByText("Test Cases"));
    expect(screen.getByTestId("run-tests-btn")).toBeInTheDocument();
  });

  it("shows 'Tumu' risk filter button", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/api-testing/page");
    render(<Page />);
    expect(screen.getByText("Tumu")).toBeInTheDocument();
  });
});

// ─── CoveragePage ──────────────────────────────────────────────────────────

describe("CoveragePage", () => {
  const coverageMatrix = {
    coverage_percentage: 75,
    total_requirements: 20,
    covered_count: 15,
    matrix: [
      {
        requirement_id: "r1",
        external_id: "REQ-001",
        title: "Login test",
        is_covered: true,
        scenario_ids: ["s1"],
      },
    ],
    gaps: [
      {
        requirement_id: "r2",
        external_id: "REQ-002",
        title: "Password reset testi",
        is_covered: false,
        scenario_ids: [],
      },
    ],
  };

  beforeEach(() => {
    apiFetchMock.mockResolvedValue(coverageMatrix);

    const m = require("@/lib/hooks/use-api-testing");
    (m.useCoverageAnalysis as jest.Mock).mockReturnValue({ data: null, isLoading: false });
    (m.useCoverageGaps as jest.Mock).mockReturnValue({ data: [], isLoading: false });
    (m.useCoverageGapSuggestions as jest.Mock).mockReturnValue({ mutate: jest.fn(), data: null });

    const cu = require("@/lib/hooks/use-coverup");
    (cu.useUploadCoverage as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false });
    (cu.useAnalyzeCoverage as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false, data: null });
    (cu.useGenerateTests as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false, data: null });
    (cu.useCoverageReports as jest.Mock).mockReturnValue({ data: [] });
    (cu.useCoverageTrends as jest.Mock).mockReturnValue({ data: null, isLoading: false });
    (cu.useBankingTargets as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false });
  });

  it("renders data-testid='coverage-page'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/coverage/page");
    render(<Page />);
    expect(screen.getByTestId("coverage-page")).toBeInTheDocument();
  });

  it("shows 'Kapsam Analizi' title", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/coverage/page");
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Kapsam Analizi");
  });

  it("renders 'BDD Kapsam' tab", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/coverage/page");
    render(<Page />);
    expect(screen.getByText("BDD Kapsam")).toBeInTheDocument();
  });

  it("renders 'API Kapsam' tab", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/coverage/page");
    render(<Page />);
    expect(screen.getByText("API Kapsam")).toBeInTheDocument();
  });

  it("renders 'Kod Kapsam' tab", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/coverage/page");
    render(<Page />);
    expect(screen.getByText("Kod Kapsam")).toBeInTheDocument();
  });

  it("renders 'Test Üretici' tab", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/coverage/page");
    render(<Page />);
    expect(screen.getByText("Test Üretici")).toBeInTheDocument();
  });

  it("shows coverage-gauge after BDD data loads", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/coverage/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("coverage-gauge")).toBeInTheDocument()
    );
  });

  it("shows '75%' coverage rate after data loads", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/coverage/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("75%")).toBeInTheDocument()
    );
  });

  it("shows BDD gaps section when BDD data has gaps", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/coverage/page");
    render(<Page />);
    // "BDD Kapsam Boşlukları" SectionCard title appears in BDD tab when gaps exist
    await waitFor(() =>
      expect(screen.getByText("BDD Kapsam Boşlukları")).toBeInTheDocument()
    );
  });

  it("shows gap item title in BDD tab after load", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/coverage/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Password reset testi")).toBeInTheDocument()
    );
  });

  it("shows coverage-gaps when API Kapsam tab is active", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/coverage/page");
    render(<Page />);
    // Wait for BDD data to load first
    await waitFor(() =>
      expect(screen.getByTestId("coverage-gauge")).toBeInTheDocument()
    );
    // Switch to API Kapsam tab
    fireEvent.click(screen.getByText("API Kapsam"));
    await waitFor(() =>
      expect(screen.getByTestId("coverage-gaps")).toBeInTheDocument()
    );
  });
});
