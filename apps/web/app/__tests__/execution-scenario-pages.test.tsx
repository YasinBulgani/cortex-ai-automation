/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ── Suppress noise ─────────────────────────────────────────────────────────
const consoleSpies: jest.SpyInstance[] = [];
beforeEach(() => {
  consoleSpies.push(jest.spyOn(console, "error").mockImplementation(() => {}));
  consoleSpies.push(jest.spyOn(console, "warn").mockImplementation(() => {}));
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
  useParams: () => ({}),
  usePathname: () => "/p/proj-1/executions",
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
jest.mock("@/components/nexus/StatusBadge", () => ({
  StatusBadge: ({ status }: any) => <span>{status}</span>,
}));
jest.mock("@/components/nexus/ProgressBar", () => ({
  ProgressBar: () => <div data-testid="progress-bar" />,
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
jest.mock("@/components/ui/tabs", () => ({
  Tabs: ({ children }: any) => <div data-testid="tabs">{children}</div>,
  TabsList: ({ children }: any) => <div data-testid="tabs-list">{children}</div>,
  TabsTrigger: ({ children, value }: any) => (
    <button data-testid={`tab-${value}`}>{children}</button>
  ),
}));
jest.mock("@/components/FlowGuideCard", () => ({
  FlowGuideCard: () => <div data-testid="flow-guide-card" />,
}));
jest.mock("@/lib/useRealtimeExecution", () => ({
  useRealtimeExecution: jest.fn(),
}));

// ── ExecutionsListPage ─────────────────────────────────────────────────────

describe("ExecutionsListPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='executions-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/page"
    );
    render(<Page />);
    expect(screen.getByTestId("executions-page")).toBeInTheDocument();
  });

  it("shows 'Koşumlar' page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Koşum|Execution/i);
  });

  it("shows 'Yeni Koşum' button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/page"
    );
    render(<Page />);
    expect(screen.getByTestId("executions-btn-new")).toBeInTheDocument();
  });

  it("renders executions table container", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("executions-table")).toBeInTheDocument()
    );
  });

  it("shows CSV export button when executions exist", async () => {
    apiFetchMock.mockResolvedValue([
      {
        id: "run-csv",
        name: "CSV Test Run",
        status: "passed",
        created_at: "2026-01-01T10:00:00Z",
        scenario_total: 3,
        passed_count: 3,
        failed_count: 0,
        platform: "desktop",
        device_name: null,
      },
    ]);
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("executions-btn-export-csv")).toBeInTheDocument()
    );
  });

  it("shows platform tabs", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/page"
    );
    render(<Page />);
    expect(screen.getByTestId("tabs")).toBeInTheDocument();
  });

  it("shows execution rows when data available", async () => {
    apiFetchMock.mockResolvedValue([
      {
        id: "run-1",
        name: "Sprint Run",
        status: "passed",
        created_at: "2026-01-01T10:00:00Z",
        scenario_total: 5,
        passed_count: 4,
        failed_count: 1,
        platform: "desktop",
        device_name: null,
      },
    ]);
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("executions-row-run-1")).toBeInTheDocument()
    );
    expect(screen.getByText("Sprint Run")).toBeInTheDocument();
  });
});

// ── ExecutionDetailPage ────────────────────────────────────────────────────

describe("ExecutionDetailPage (runId)", () => {
  beforeEach(() => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/metrics")) {
        return Promise.resolve({
          total: 1,
          passed: 1,
          failed: 0,
          skipped: 0,
          pass_rate: 100,
          duration_seconds: null,
        });
      }
      return Promise.resolve({
        id: "run-1",
        name: "Sprint Run",
        status: "passed",
        created_at: "2026-01-01T10:00:00Z",
        results: [
          {
            id: "res-1",
            scenario_id: "s-1",
            scenario_title: "Login Test",
            status: "passed",
            note: null,
          },
        ],
      });
    });
  });

  it("renders data-testid='execution-detail-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/[runId]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("execution-detail-page")).toBeInTheDocument()
    );
  });

  it("shows execution name after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/[runId]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Sprint Run")).toBeInTheDocument()
    );
  });

  it("shows results table after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/[runId]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("results-table")).toBeInTheDocument()
    );
  });

  it("shows scenario title in results", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/[runId]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Login Test")).toBeInTheDocument()
    );
  });
});

// ── ScenarioEditPage ───────────────────────────────────────────────────────

describe("ScenarioEditPage (/scenarios/edit/[id])", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue({
      id: "s-1",
      title: "Login Testi",
      description: "Kullanıcı giriş senaryosu",
      status: "draft",
      steps: [],
      tags: [],
    });
  });

  it("renders data-testid='scenario-edit-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/edit/[id]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("scenario-edit-page")).toBeInTheDocument()
    );
  });

  it("shows 'Senaryo düzenle' heading", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/edit/[id]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("scenario-edit-heading")).toBeInTheDocument()
    );
  });

  it("shows scenario edit form", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/edit/[id]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("scenario-edit-form")).toBeInTheDocument()
    );
  });

  it("shows title input pre-filled after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/edit/[id]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("scenario-edit-input-title")).toHaveValue("Login Testi")
    );
  });
});

// ── ScenarioVersionsPage ───────────────────────────────────────────────────

describe("ScenarioVersionsPage (/scenarios/[id]/versions)", () => {
  beforeEach(() => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/versions")) {
        return Promise.resolve([
          {
            id: "v-1",
            version_number: 1,
            title: "Login Testi",
            created_at: "2026-01-01T00:00:00Z",
            created_by: "admin@test.com",
            change_summary: "Initial version",
          },
        ]);
      }
      return Promise.resolve({ id: "s-1", title: "Login Testi" });
    });
  });

  it("renders data-testid='versions-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/[id]/versions/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("versions-page")).toBeInTheDocument()
    );
  });

  it("shows 'Sürüm Geçmişi' heading", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/[id]/versions/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("versions-heading")).toBeInTheDocument()
    );
  });

  it("shows back button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/[id]/versions/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("versions-btn-back")).toBeInTheDocument()
    );
  });

  it("shows version entries after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/[id]/versions/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText(/v1|Sürüm 1|Initial version/i)).toBeInTheDocument()
    );
  });
});

// ── RegressionDetailPage ───────────────────────────────────────────────────

describe("RegressionDetailPage (/regression/[setId])", () => {
  beforeEach(() => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/regression-sets/")) {
        return Promise.resolve({
          id: "rs-1",
          name: "Sprint Regresyon",
          description: "Sprint testi için",
          scenarios: [
            { item_id: "item-1", scenario_id: "s-1", title: "Login Testi" },
          ],
        });
      }
      if (url.includes("/scenarios")) {
        return Promise.resolve([
          { id: "s-1", title: "Login Testi" },
          { id: "s-2", title: "Çıkış Testi" },
        ]);
      }
      return Promise.resolve([]);
    });
  });

  it("renders data-testid='regression-detail-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/regression/[setId]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("regression-detail-page")).toBeInTheDocument()
    );
  });

  it("shows regression set name after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/regression/[setId]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Sprint Regresyon")).toBeInTheDocument()
    );
  });

  it("shows back button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/regression/[setId]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("regression-detail-btn-back")).toBeInTheDocument()
    );
  });
});
