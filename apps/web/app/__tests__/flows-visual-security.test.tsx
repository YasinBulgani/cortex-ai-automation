/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

// ── Suppress console noise ────────────────────────────────────────────────────
beforeAll(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  jest.spyOn(console, "warn").mockImplementation(() => {});
});
afterAll(() => {
  (console.error as jest.Mock).mockRestore();
  (console.warn as jest.Mock).mockRestore();
});

// ── Standard mocks ────────────────────────────────────────────────────────────
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
jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn(),
  ENGINE_BASE: "http://localhost:5001",
}));
jest.mock("@/lib/api-client", () => ({
  apiFetch: jest.fn(),
  ENGINE_BASE: "http://localhost:5001",
}));

// nexus barrel mock
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
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
  StatCard: ({ label, value }: any) => (
    <div data-testid={`stat-${label}`}>{String(value)}</div>
  ),
  MetricRow: ({ children }: any) => <div>{children}</div>,
  ToolbarActions: ({ children }: any) => <div>{children}</div>,
  StatusBadge: ({ status }: any) => <span>{status}</span>,
  FilterBar: ({ children }: any) => <div>{children}</div>,
}));

// Individual nexus mocks
jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">
      {title}
      {right}
    </div>
  ),
}));
jest.mock("@/components/nexus/SectionCard", () => ({
  SectionCard: ({ title, children }: any) => (
    <div>
      {title && <div>{title}</div>}
      {children}
    </div>
  ),
}));
jest.mock("@/components/nexus/EmptyState", () => ({
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
}));
jest.mock("@/components/nexus/StatCard", () => ({
  StatCard: ({ label, value }: any) => (
    <div data-testid={`stat-${label}`}>{String(value)}</div>
  ),
}));
jest.mock("@/components/nexus/MetricRow", () => ({
  MetricRow: ({ children }: any) => <div>{children}</div>,
}));
jest.mock("@/components/nexus/StatusBadge", () => ({
  StatusBadge: ({ status }: any) => <span>{status}</span>,
}));

// FlowGuideCard mock
jest.mock("@/components/FlowGuideCard", () => ({
  FlowGuideCard: ({ title }: any) => (
    <div data-testid="flow-guide-card">{title}</div>
  ),
}));

// React Query mock for SecurityPage
jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn(() => ({ data: undefined, isLoading: false })),
  useMutation: jest.fn(() => ({
    mutateAsync: jest.fn(),
    mutate: jest.fn(),
    isPending: false,
    data: undefined,
  })),
  useQueryClient: jest.fn(() => ({ invalidateQueries: jest.fn() })),
}));

// useApiSpecs mock
jest.mock("@/lib/hooks/use-api-testing", () => ({
  useApiSpecs: jest.fn(() => ({ data: [] })),
}));

// ─────────────────────────────────────────────────────────────────────────────
// FlowsListPage — 6 tests
// ─────────────────────────────────────────────────────────────────────────────
import { apiFetch as apiFetchLib } from "@/lib/api";

const mockedApiFetch = apiFetchLib as jest.Mock;

describe("FlowsListPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders flows-page container and page header", async () => {
    mockedApiFetch.mockResolvedValueOnce([]);
    const { default: FlowsListPage } = await import(
      "../(dashboard)/p/[projectId]/flows/page"
    );
    await act(async () => {
      render(<FlowsListPage />);
    });
    expect(screen.getByTestId("flows-page")).toBeInTheDocument();
    expect(screen.getByTestId("page-header")).toBeInTheDocument();
    expect(screen.getByText("Test Akışları")).toBeInTheDocument();
  });

  it("renders create form with name input and submit button", async () => {
    mockedApiFetch.mockResolvedValueOnce([]);
    const { default: FlowsListPage } = await import(
      "../(dashboard)/p/[projectId]/flows/page"
    );
    await act(async () => {
      render(<FlowsListPage />);
    });
    expect(screen.getByTestId("flows-form")).toBeInTheDocument();
    expect(screen.getByTestId("flows-input-name")).toBeInTheDocument();
    expect(screen.getByTestId("flows-btn-create")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Akış adı…")).toBeInTheDocument();
  });

  it("shows empty state when no flows are returned", async () => {
    mockedApiFetch.mockResolvedValueOnce([]);
    const { default: FlowsListPage } = await import(
      "../(dashboard)/p/[projectId]/flows/page"
    );
    await act(async () => {
      render(<FlowsListPage />);
    });
    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    });
    expect(screen.getByText("Henüz akış yok")).toBeInTheDocument();
  });

  it("renders flow cards when flows exist", async () => {
    const flows = [
      { id: "f1", name: "Login Flow", description: "Login tests", created_at: "2026-01-01" },
      { id: "f2", name: "Checkout Flow", description: "", created_at: "2026-01-02" },
    ];
    mockedApiFetch.mockResolvedValueOnce(flows);
    const { default: FlowsListPage } = await import(
      "../(dashboard)/p/[projectId]/flows/page"
    );
    await act(async () => {
      render(<FlowsListPage />);
    });
    await waitFor(() => {
      expect(screen.getByTestId("flows-grid")).toBeInTheDocument();
    });
    expect(screen.getByTestId("flows-card-f1")).toBeInTheDocument();
    expect(screen.getByTestId("flows-card-f2")).toBeInTheDocument();
    expect(screen.getByText("Login Flow")).toBeInTheDocument();
    expect(screen.getByText("Checkout Flow")).toBeInTheDocument();
  });

  it("stat cards display correct flow count", async () => {
    const flows = [
      { id: "f1", name: "Flow 1", description: "", created_at: new Date().toISOString() },
      { id: "f2", name: "Flow 2", description: "", created_at: new Date().toISOString() },
    ];
    mockedApiFetch.mockResolvedValueOnce(flows);
    const { default: FlowsListPage } = await import(
      "../(dashboard)/p/[projectId]/flows/page"
    );
    await act(async () => {
      render(<FlowsListPage />);
    });
    await waitFor(() => {
      expect(screen.getByTestId("stat-Toplam Akış")).toHaveTextContent("2");
    });
  });

  it("updates name input when user types", async () => {
    mockedApiFetch.mockResolvedValueOnce([]);
    const { default: FlowsListPage } = await import(
      "../(dashboard)/p/[projectId]/flows/page"
    );
    await act(async () => {
      render(<FlowsListPage />);
    });
    const input = screen.getByTestId("flows-input-name");
    fireEvent.change(input, { target: { value: "My New Flow" } });
    expect((input as HTMLInputElement).value).toBe("My New Flow");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// VisualRegressionPage — 6 tests
// ─────────────────────────────────────────────────────────────────────────────
import { apiFetch as apiFetchLib2 } from "@/lib/api";

describe("VisualRegressionPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedApiFetch.mockResolvedValue([]);
  });

  it("renders visual-regression-page container", async () => {
    const { default: VisualRegressionPage } = await import(
      "../(dashboard)/p/[projectId]/visual/page"
    );
    await act(async () => {
      render(<VisualRegressionPage />);
    });
    expect(screen.getByTestId("visual-regression-page")).toBeInTheDocument();
  });

  it("renders page header with 'Visual Regression' title", async () => {
    const { default: VisualRegressionPage } = await import(
      "../(dashboard)/p/[projectId]/visual/page"
    );
    await act(async () => {
      render(<VisualRegressionPage />);
    });
    expect(screen.getByTestId("page-header")).toBeInTheDocument();
    expect(screen.getByText("Visual Regression")).toBeInTheDocument();
  });

  it("renders FlowGuideCard component", async () => {
    const { default: VisualRegressionPage } = await import(
      "../(dashboard)/p/[projectId]/visual/page"
    );
    await act(async () => {
      render(<VisualRegressionPage />);
    });
    expect(screen.getByTestId("flow-guide-card")).toBeInTheDocument();
  });

  it("shows 'Henüz baseline yok' when no baselines loaded", async () => {
    mockedApiFetch.mockResolvedValueOnce([]);
    const { default: VisualRegressionPage } = await import(
      "../(dashboard)/p/[projectId]/visual/page"
    );
    await act(async () => {
      render(<VisualRegressionPage />);
    });
    await waitFor(() => {
      expect(screen.getByText("Henüz baseline yok")).toBeInTheDocument();
    });
  });

  it("renders baseline table rows when baselines exist", async () => {
    const baselines = [
      { id: "b1", page: "home", url: "http://example.com", created_at: "2026-01-01T00:00:00Z" },
      { id: "b2", page: "login", url: "http://example.com/login", created_at: "2026-01-02T00:00:00Z" },
    ];
    mockedApiFetch.mockResolvedValueOnce(baselines);
    const { default: VisualRegressionPage } = await import(
      "../(dashboard)/p/[projectId]/visual/page"
    );
    await act(async () => {
      render(<VisualRegressionPage />);
    });
    await waitFor(() => {
      expect(screen.getByText("home")).toBeInTheDocument();
    });
    expect(screen.getByText("login")).toBeInTheDocument();
  });

  it("shows baseline count in header area", async () => {
    const baselines = [
      { id: "b1", page: "home", url: "http://example.com", created_at: "2026-01-01T00:00:00Z" },
    ];
    mockedApiFetch.mockResolvedValueOnce(baselines);
    const { default: VisualRegressionPage } = await import(
      "../(dashboard)/p/[projectId]/visual/page"
    );
    await act(async () => {
      render(<VisualRegressionPage />);
    });
    await waitFor(() => {
      // "1 kayıt" text should appear in the baselines list header
      expect(screen.getByText("1 kayıt")).toBeInTheDocument();
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// SecurityPage — 6 tests
// ─────────────────────────────────────────────────────────────────────────────
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiSpecs } from "@/lib/hooks/use-api-testing";

const mockedUseQuery = useQuery as jest.Mock;
const mockedUseMutation = useMutation as jest.Mock;
const mockedUseApiSpecs = useApiSpecs as jest.Mock;

describe("SecurityPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseMutation.mockReturnValue({
      mutateAsync: jest.fn(),
      mutate: jest.fn(),
      isPending: false,
      data: undefined,
    });
    (useQueryClient as jest.Mock).mockReturnValue({ invalidateQueries: jest.fn() });
    mockedUseApiSpecs.mockReturnValue({ data: [] });
  });

  it("renders security-page container", async () => {
    mockedUseQuery.mockReturnValue({ data: undefined, isLoading: false });
    const { default: SecurityPage } = await import(
      "../(dashboard)/p/[projectId]/security/page"
    );
    await act(async () => {
      render(<SecurityPage />);
    });
    expect(screen.getByTestId("security-page")).toBeInTheDocument();
  });

  it("renders page header with 'Güvenlik Tarama' title", async () => {
    mockedUseQuery.mockReturnValue({ data: undefined, isLoading: false });
    const { default: SecurityPage } = await import(
      "../(dashboard)/p/[projectId]/security/page"
    );
    await act(async () => {
      render(<SecurityPage />);
    });
    expect(screen.getByText("Güvenlik Tarama")).toBeInTheDocument();
  });

  it("shows empty state when dashboard data is not available", async () => {
    mockedUseQuery.mockReturnValue({ data: undefined, isLoading: false });
    const { default: SecurityPage } = await import(
      "../(dashboard)/p/[projectId]/security/page"
    );
    await act(async () => {
      render(<SecurityPage />);
    });
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByText("Güvenlik verisi yok")).toBeInTheDocument();
  });

  it("renders Dashboard and Tarama Sonuçları tab buttons", async () => {
    mockedUseQuery.mockReturnValue({ data: undefined, isLoading: false });
    const { default: SecurityPage } = await import(
      "../(dashboard)/p/[projectId]/security/page"
    );
    await act(async () => {
      render(<SecurityPage />);
    });
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Tarama Sonuçları")).toBeInTheDocument();
  });

  it("renders security score and severity stats when dashboard data exists", async () => {
    const dashboard = {
      total_endpoints: 10,
      scanned_endpoints: 8,
      findings_by_severity: { critical: 2, high: 5, medium: 3, low: 1 },
      findings_by_owasp: {},
      avg_security_score: 75,
      top_vulnerable_endpoints: [],
      compliance_status: {},
      recommendations: [],
    };
    mockedUseQuery.mockReturnValue({ data: dashboard, isLoading: false });
    const { default: SecurityPage } = await import(
      "../(dashboard)/p/[projectId]/security/page"
    );
    await act(async () => {
      render(<SecurityPage />);
    });
    expect(screen.getByText("75/100")).toBeInTheDocument();
    expect(screen.getByText("Güvenlik Skoru")).toBeInTheDocument();
  });

  it("switches to scan results tab when tab button clicked (tab disabled without scan result)", async () => {
    mockedUseQuery.mockReturnValue({ data: undefined, isLoading: false });
    const { default: SecurityPage } = await import(
      "../(dashboard)/p/[projectId]/security/page"
    );
    await act(async () => {
      render(<SecurityPage />);
    });
    const scanTab = screen.getByText("Tarama Sonuçları");
    // Tab is disabled without a scan result
    expect(scanTab.closest("button")).toBeDisabled();
  });
});
