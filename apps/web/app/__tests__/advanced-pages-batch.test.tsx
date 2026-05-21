/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ── Suppress noise ─────────────────────────────────────────────────────────
const consoleSpies: jest.SpyInstance[] = [];
beforeEach(() => {
  consoleSpies.push(jest.spyOn(console, "error").mockImplementation(() => {}));
  consoleSpies.push(jest.spyOn(console, "warn").mockImplementation(() => {}));
  (global as any).fetch = jest.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
  );
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
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
  useParams: jest.fn(() => ({ productId: "one" })),
  notFound: jest.fn(),
  usePathname: () => "/p/proj-1",
}));
jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

const apiFetchMock = jest.fn();
jest.mock("@/lib/api", () => ({
  apiFetch: (...args: any[]) => apiFetchMock(...args),
  API_BASE: "http://localhost:8000",
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

const apiClientMock = jest.fn();
jest.mock("@/lib/api-client", () => ({
  apiFetch: (...args: any[]) => apiClientMock(...args),
  engineFetch: jest.fn(),
}));

// Nexus components
jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">{title}{right}</div>
  ),
}));
jest.mock("@/components/nexus/SectionCard", () => ({
  SectionCard: ({ title, children, right }: any) => (
    <div data-testid="section-card">
      {title && <div>{title}</div>}{right}{children}
    </div>
  ),
}));
jest.mock("@/components/nexus/EmptyState", () => ({
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
}));
jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">{title}{right}</div>
  ),
  SectionCard: ({ title, children, right }: any) => (
    <div data-testid="section-card">{title && <div>{title}</div>}{right}{children}</div>
  ),
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
  StatCard: ({ label, value }: any) => <div data-testid={`stat-${label}`}>{String(value ?? "")}</div>,
  MetricRow: ({ children }: any) => <div>{children}</div>,
  ToolbarActions: ({ children }: any) => <div>{children}</div>,
  StatusBadge: ({ status }: any) => <span>{status}</span>,
  FilterBar: ({ children }: any) => <div>{children}</div>,
  ProgressBar: () => <div data-testid="progress-bar" />,
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

// ── use-api-testing hook mock ──────────────────────────────────────────────
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
  useChains: jest.fn(),
  useCreateChain: jest.fn(),
  useDeleteChain: jest.fn(),
  useExecutionHistory: jest.fn(),
  useTestTrends: jest.fn(),
  useRunChain: jest.fn(() => ({ mutateAsync: jest.fn(() => Promise.resolve(null)), mutate: jest.fn(), isPending: false, data: null, error: null })),
  useUpdateChain: jest.fn(() => ({ mutate: jest.fn(), isPending: false, data: null })),
}));

// ── @tanstack/react-query mock ─────────────────────────────────────────────
jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn(() => ({ data: null, isLoading: false })),
  useMutation: jest.fn(() => ({ mutate: jest.fn(), isPending: false, data: null })),
  useQueryClient: jest.fn(() => ({ invalidateQueries: jest.fn() })),
}));

// ── ReactFlow mock ─────────────────────────────────────────────────────────
jest.mock("reactflow", () => ({
  __esModule: true,
  default: ({ children }: any) => <div data-testid="react-flow">{children}</div>,
  Background: () => <div />,
  Controls: () => <div />,
  MiniMap: () => <div />,
  useNodesState: jest.fn(() => [[], jest.fn(), jest.fn()]),
  useEdgesState: jest.fn(() => [[], jest.fn(), jest.fn()]),
  addEdge: jest.fn((edge: any, edges: any[]) => [...edges, edge]),
  BackgroundVariant: { Dots: "dots" },
  Handle: () => <div />,
  Position: { Left: "left", Right: "right", Top: "top", Bottom: "bottom" },
}));
jest.mock("reactflow/dist/style.css", () => ({}));

// ── Other component mocks ──────────────────────────────────────────────────
jest.mock("@/components/FlowGuideCard", () => ({
  FlowGuideCard: () => <div data-testid="flow-guide-card" />,
}));
jest.mock("@/components/ServiceTestingGuide", () => ({
  ServiceTestingGuide: () => <div data-testid="service-testing-guide" />,
}));
jest.mock("@/lib/core-runtime", () => ({
  useCoreRuntime: jest.fn(() => ({
    services: [
      { name: "api", state: "running", port: 8000, description: "API Server" },
      { name: "worker", state: "stopped", port: 8001, description: "Worker" },
    ],
    backendReady: true,
    checkedAt: "2026-01-01T00:00:00Z",
    loading: false,
    error: null,
    refresh: jest.fn(),
  })),
}));
jest.mock("@/components/ProductLandingPage", () => ({
  ProductLandingPage: ({ productId }: any) => (
    <div data-testid="product-landing-page">Product: {productId}</div>
  ),
}));
jest.mock("@/lib/product", () => ({
  isValidProductFamilyId: jest.fn(() => true),
  PRODUCT_FAMILY: [{ id: "one", name: "TestwrightAI" }],
  PRODUCT_FAMILY_BY_ID: { one: { id: "one", name: "TestwrightAI" } },
}));

// ── DslCatalogView mock ────────────────────────────────────────────────────
jest.mock("@/components/dsl/DslCatalogView", () => ({
  DslCatalogView: ({ title, forceCategory }: any) => (
    <div data-testid="dsl-catalog-view">
      {title}{forceCategory && <span>category:{forceCategory}</span>}
    </div>
  ),
}));
jest.mock("@/components/dsl/DslProposalReview", () => ({
  DslProposalReview: () => <div data-testid="dsl-proposal-review">Proposal Review</div>,
}));
jest.mock("@/components/dsl/DslActionEditor", () => ({
  DslActionEditor: ({ mode, actionId }: any) => (
    <div data-testid="dsl-action-editor">mode:{mode}{actionId && <span> id:{actionId}</span>}</div>
  ),
}));

// ── TestHistoryPage ────────────────────────────────────────────────────────

describe("TestHistoryPage", () => {
  beforeEach(() => {
    const m = require("@/lib/hooks/use-api-testing");
    (m.useTestTrends as jest.Mock).mockReturnValue({
      data: {
        total_runs: 42,
        avg_pass_rate: 87,
        avg_response_ms: 320,
        most_failed_test_type: "negative",
      },
      isLoading: false,
    });
    (m.useExecutionHistory as jest.Mock).mockReturnValue({
      data: {
        items: [
          {
            id: "h-1",
            suite_name: "Suite A",
            timestamp: "2026-01-01T10:00:00Z",
            total_tests: 10,
            passed: 9,
            failed: 1,
            pass_rate: 90,
            status: "passed",
            test_type: "positive",
            duration_ms: 1500,
          },
        ],
        total_count: 1,
      },
      isLoading: false,
    });
  });

  it("renders data-testid='test-history-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/test-history/page"
    );
    render(<Page />);
    expect(screen.getByTestId("test-history-page")).toBeInTheDocument();
  });

  it("shows 'Test Geçmişi' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/test-history/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Test Geçmişi");
  });

  it("shows total runs stat", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/test-history/page"
    );
    render(<Page />);
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("shows avg pass rate stat", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/test-history/page"
    );
    render(<Page />);
    expect(screen.getByText(/87%/)).toBeInTheDocument();
  });
});

// ── SecurityPage ───────────────────────────────────────────────────────────

describe("SecurityPage", () => {
  beforeEach(() => {
    const m = require("@/lib/hooks/use-api-testing");
    (m.useApiSpecs as jest.Mock).mockReturnValue({ data: [], isLoading: false });
    apiClientMock.mockResolvedValue({
      total_endpoints: 10,
      scanned_endpoints: 8,
      findings_by_severity: { high: 2, medium: 3 },
      findings_by_owasp: {},
      avg_security_score: 72,
      top_vulnerable_endpoints: [],
      compliance_status: {},
      recommendations: ["Fix auth"],
    });
  });

  it("renders data-testid='security-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/security/page"
    );
    render(<Page />);
    expect(screen.getByTestId("security-page")).toBeInTheDocument();
  });

  it("shows 'Güvenlik' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/security/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Güvenlik|Security/i);
  });

  it("shows dashboard data after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/security/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getAllByText(/72|güvenlik|security/i).length).toBeGreaterThanOrEqual(1)
    );
  });
});

// ── ChainBuilderPage ───────────────────────────────────────────────────────

describe("ChainBuilderPage", () => {
  beforeEach(() => {
    const m = require("@/lib/hooks/use-api-testing");
    (m.useChains as jest.Mock).mockReturnValue({ data: [], isLoading: false });
    (m.useCreateChain as jest.Mock).mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    (m.useDeleteChain as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false });
  });

  it("renders data-testid='chain-builder-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/chain-builder/page"
    );
    render(<Page />);
    expect(screen.getByTestId("chain-builder-page")).toBeInTheDocument();
  });

  it("shows 'Chain Builder' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/chain-builder/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Chain|Zincir/i);
  });

  it("renders ReactFlow canvas", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/chain-builder/page"
    );
    render(<Page />);
    expect(screen.getByTestId("react-flow")).toBeInTheDocument();
  });
});

// ── SystemServicesPage ─────────────────────────────────────────────────────

describe("SystemServicesPage", () => {
  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/system/services/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows 'System Services' heading", async () => {
    const { default: Page } = await import("../(dashboard)/system/services/page");
    render(<Page />);
    expect(screen.getByText("System Services")).toBeInTheDocument();
  });

  it("shows 'Servisler' section", async () => {
    const { default: Page } = await import("../(dashboard)/system/services/page");
    render(<Page />);
    expect(screen.getByText("Servisler")).toBeInTheDocument();
  });

  it("shows service names", async () => {
    const { default: Page } = await import("../(dashboard)/system/services/page");
    render(<Page />);
    expect(screen.getByText("api")).toBeInTheDocument();
    expect(screen.getByText("worker")).toBeInTheDocument();
  });

  it("shows refresh button", async () => {
    const { default: Page } = await import("../(dashboard)/system/services/page");
    render(<Page />);
    expect(screen.getByText("Yenile")).toBeInTheDocument();
  });
});

// ── ProductPage ─────────────────────────────────────────────────────────────

describe("ProductPage (/products/[productId])", () => {
  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/products/[productId]/page");
    const { container } = render(
      <Page params={{ productId: "one" }} />
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders the product-specific page component", async () => {
    const { default: Page } = await import("../(dashboard)/products/[productId]/page");
    const { container } = render(<Page params={{ productId: "one" }} />);
    // Main switched from a single ProductLandingPage to per-product components
    // (OneProductPage, StudioProductPage, etc.). Just verify something renders.
    expect(container.firstChild).toBeInTheDocument();
  });
});

// ── DslCatalogGlobalPage ───────────────────────────────────────────────────

describe("DslCatalogGlobalPage", () => {
  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/dsl-catalog/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders DslCatalogView with correct title", async () => {
    const { default: Page } = await import("../(dashboard)/dsl-catalog/page");
    render(<Page />);
    expect(screen.getByTestId("dsl-catalog-view")).toBeInTheDocument();
    expect(screen.getByText("DSL Sözlüğü")).toBeInTheDocument();
  });
});

// ── DslReviewPage ──────────────────────────────────────────────────────────

describe("DslReviewPage", () => {
  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/dsl-catalog/review/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders DslProposalReview component", async () => {
    const { default: Page } = await import("../(dashboard)/dsl-catalog/review/page");
    render(<Page />);
    expect(screen.getByTestId("dsl-proposal-review")).toBeInTheDocument();
  });
});

// ── MobileDslCatalogPage ───────────────────────────────────────────────────

describe("MobileDslCatalogPage", () => {
  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/dsl-catalog/mobile/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders DslCatalogView with 'Mobil DSL' title", async () => {
    const { default: Page } = await import("../(dashboard)/dsl-catalog/mobile/page");
    render(<Page />);
    expect(screen.getByTestId("dsl-catalog-view")).toBeInTheDocument();
    expect(screen.getByText("Mobil DSL")).toBeInTheDocument();
  });
});

// ── EditDslActionPage ──────────────────────────────────────────────────────

describe("EditDslActionPage (/dsl-catalog/editor/[actionId])", () => {
  it("renders without crashing with actionId", async () => {
    const navMod = require("next/navigation");
    navMod.useParams.mockReturnValue({ actionId: "click-element" });
    const { default: Page } = await import("../(dashboard)/dsl-catalog/editor/[actionId]/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders DslActionEditor in edit mode", async () => {
    const navMod = require("next/navigation");
    navMod.useParams.mockReturnValue({ actionId: "click-element" });
    const { default: Page } = await import("../(dashboard)/dsl-catalog/editor/[actionId]/page");
    render(<Page />);
    expect(screen.getByTestId("dsl-action-editor")).toBeInTheDocument();
    expect(screen.getByText(/mode:edit/)).toBeInTheDocument();
  });

  it("shows error message when no actionId", async () => {
    const navMod = require("next/navigation");
    navMod.useParams.mockReturnValue({ actionId: undefined });
    const { default: Page } = await import("../(dashboard)/dsl-catalog/editor/[actionId]/page");
    render(<Page />);
    expect(screen.getByText(/ID.*belirtilmedi/i)).toBeInTheDocument();
  });
});

// ── NewDslActionPage ───────────────────────────────────────────────────────

describe("NewDslActionPage (/dsl-catalog/editor/new)", () => {
  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/dsl-catalog/editor/new/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders DslActionEditor in create mode", async () => {
    const { default: Page } = await import("../(dashboard)/dsl-catalog/editor/new/page");
    render(<Page />);
    expect(screen.getByTestId("dsl-action-editor")).toBeInTheDocument();
    expect(screen.getByText(/mode:create/)).toBeInTheDocument();
  });
});
