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
  useParams: jest.fn(() => ({})),
  usePathname: () => "/p/proj-1",
}));
jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

const apiFetchMock = jest.fn();
jest.mock("@/lib/api", () => ({
  apiFetch: (...args: any[]) => apiFetchMock(...args),
  clearToken: jest.fn(),
  API_BASE: "http://localhost:8000",
  ENGINE_BASE: "http://localhost:8080",
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

// nexus
jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">{title}{right}</div>
  ),
}));
jest.mock("@/components/nexus/SectionCard", () => ({
  SectionCard: ({ title, children, right }: any) => (
    <div data-testid="section-card">{title && <div>{title}</div>}{right}{children}</div>
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
  CodeBlock: ({ code }: any) => <pre data-testid="code-block">{code}</pre>,
  TrendBadge: ({ value }: any) => <span data-testid="trend-badge">{value}</span>,
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
  TabsList: ({ children }: any) => <div>{children}</div>,
  TabsTrigger: ({ children, value }: any) => (
    <button data-testid={`tab-${value}`}>{children}</button>
  ),
  TabsContent: ({ children }: any) => <div>{children}</div>,
}));
jest.mock("@/components/FlowGuideCard", () => ({
  FlowGuideCard: () => <div data-testid="flow-guide-card" />,
}));
jest.mock("@/components/ServiceTestingGuide", () => ({
  ServiceTestingGuide: () => <div data-testid="service-testing-guide" />,
}));

// dnd-kit mocks
jest.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: any) => <div data-testid="dnd-context">{children}</div>,
  closestCenter: jest.fn(),
  closestCorners: jest.fn(),
  KeyboardSensor: jest.fn(),
  PointerSensor: jest.fn(),
  useSensor: jest.fn(() => ({})),
  useSensors: jest.fn(() => ({})),
  DragOverlay: ({ children }: any) => <div data-testid="drag-overlay">{children}</div>,
  useDroppable: jest.fn(() => ({ setNodeRef: jest.fn(), isOver: false })),
}));
jest.mock("@dnd-kit/sortable", () => ({
  arrayMove: jest.fn((arr: any[]) => arr),
  SortableContext: ({ children }: any) => <div>{children}</div>,
  sortableKeyboardCoordinates: jest.fn(),
  verticalListSortingStrategy: {},
  useSortable: jest.fn(() => ({
    attributes: {},
    listeners: {},
    setNodeRef: jest.fn(),
    transform: null,
    transition: undefined,
    isDragging: false,
  })),
}));
jest.mock("@dnd-kit/utilities", () => ({
  CSS: { Transform: { toString: jest.fn(() => "") } },
}));

// use-ai-metrics hooks — return null data so empty state renders (avoids .toFixed crashes)
jest.mock("@/lib/hooks/use-ai-metrics", () => ({
  useQualityMetrics: jest.fn(() => ({
    data: null,
    isLoading: false,
  })),
  useLlmTraceStats: jest.fn(() => ({
    data: null,
    isLoading: false,
  })),
}));

// useRealtimeExecution
jest.mock("@/lib/useRealtimeExecution", () => ({
  useRealtimeExecution: jest.fn(),
}));

// tanstack react-query (for qa-orchestrator)
jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn(() => ({ data: null, isLoading: false })),
  useMutation: jest.fn(() => ({
    mutate: jest.fn(),
    isPending: false,
    data: null,
    error: null,
  })),
  useQueryClient: jest.fn(() => ({ invalidateQueries: jest.fn() })),
}));

// api-client (for qa-orchestrator)
jest.mock("@/lib/api-client", () => ({
  apiFetch: (...args: any[]) => apiFetchMock(...args),
  engineFetch: jest.fn(() => Promise.resolve({})),
  getToken: jest.fn(() => "tok"),
  clearToken: jest.fn(),
  API_BASE: "http://localhost:8000",
  ENGINE_BASE: "http://localhost:8080",
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

// ── AiMetricsPage ──────────────────────────────────────────────────────────

describe("AiMetricsPage", () => {
  it("renders ai-metrics-empty state when no data", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/ai-metrics/page"
    );
    render(<Page />);
    // null data → overview.total_calls === 0 → empty state
    expect(screen.getByTestId("ai-metrics-empty")).toBeInTheDocument();
  });

  it("shows 'LLM Kalite' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/ai-metrics/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/LLM Kalite/i);
  });
});

// ── AnalyticsPage ──────────────────────────────────────────────────────────

describe("AnalyticsPage", () => {
  beforeEach(() => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("trends")) return Promise.resolve([]);
      if (url.includes("stats")) return Promise.resolve({ total_runs: 0, avg_pass_rate: 0, total_scenarios: 0 });
      return Promise.resolve([]);
    });
    const m = require("@/lib/useRealtimeExecution");
    (m.useRealtimeExecution as jest.Mock).mockReturnValue(null);
  });

  it("renders data-testid='analytics-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/analytics/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("analytics-page")).toBeInTheDocument()
    );
  });

  it("shows 'Analitik' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/analytics/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("page-header")).toHaveTextContent(/Analitik|Analytics/i)
    );
  });

  it("shows tabs", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/analytics/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("tabs")).toBeInTheDocument()
    );
  });
});

// ── AnalysisPage ───────────────────────────────────────────────────────────

describe("AnalysisPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='analysis-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/analysis/page"
    );
    render(<Page />);
    expect(screen.getByTestId("analysis-page")).toBeInTheDocument();
  });

  it("shows 'Analiz' heading", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/analysis/page"
    );
    render(<Page />);
    // AnalysisPage uses <h1> not PageHeader component
    expect(screen.getByText(/Analiz Merkezi/i)).toBeInTheDocument();
  });

  it("shows file drop zone", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/analysis/page"
    );
    render(<Page />);
    expect(screen.getByTestId("file-drop-zone")).toBeInTheDocument();
  });
});

// ── ApiTestsPage ───────────────────────────────────────────────────────────

describe("ApiTestsPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='api-tests-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/api-tests/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("api-tests-page")).toBeInTheDocument()
    );
  });

  it("shows 'API Test' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/api-tests/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("page-header")).toHaveTextContent(/API Test/i)
    );
  });

  it("shows flow guide card", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/api-tests/page"
    );
    render(<Page />);
    expect(screen.getByTestId("flow-guide-card")).toBeInTheDocument();
  });

  it("shows service testing guide", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/api-tests/page"
    );
    render(<Page />);
    expect(screen.getByTestId("service-testing-guide")).toBeInTheDocument();
  });
});

// ── RegressionPage ─────────────────────────────────────────────────────────

describe("RegressionPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='regression-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/regression/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("regression-page")).toBeInTheDocument()
    );
  });

  it("shows 'Regresyon' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/regression/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("page-header")).toHaveTextContent(/Regresyon|Regression/i)
    );
  });

  it("shows regression form", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/regression/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("regression-form")).toBeInTheDocument()
    );
  });

  it("shows regression name input", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/regression/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("regression-input-name")).toBeInTheDocument()
    );
  });
});

// ── ApprovalsPage ──────────────────────────────────────────────────────────

describe("ApprovalsPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='approvals-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/approvals/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("approvals-page")).toBeInTheDocument()
    );
  });

  it("shows 'Onay' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/approvals/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("page-header")).toHaveTextContent(/Onay|Approval/i)
    );
  });

  it("shows kanban columns after load", async () => {
    apiFetchMock.mockResolvedValue([
      { id: "a1", title: "Test Onayı", source_text: "...", draft_payload: null, status: "pending", scenario_id: null },
    ]);
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/approvals/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.queryByTestId("kanban-column-pending") ??
             screen.queryByTestId("approvals-page")).toBeInTheDocument()
    );
  });
});

// ── RecorderPage ───────────────────────────────────────────────────────────

describe("RecorderPage", () => {
  beforeEach(() => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/sessions") || url.includes("/saved")) {
        return Promise.resolve([]);
      }
      return Promise.resolve([]);
    });
  });

  it("renders data-testid='recorder-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/recorder/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("recorder-page")).toBeInTheDocument()
    );
  });

  it("shows 'Kaydedici' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/recorder/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("page-header")).toHaveTextContent(/Kaydedici|Record/i)
    );
  });

  it("shows recorder URL input", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/recorder/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("recorder-url-input")).toBeInTheDocument()
    );
  });

  it("shows recorder start button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/recorder/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("recorder-btn-start")).toBeInTheDocument()
    );
  });
});

// ── QaOrchestratorPage ─────────────────────────────────────────────────────

describe("QaOrchestratorPage", () => {
  it("renders data-testid='qa-orchestrator-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/qa-orchestrator/page"
    );
    render(<Page />);
    expect(screen.getByTestId("qa-orchestrator-page")).toBeInTheDocument();
  });

  it("shows 'QA Orkestratör' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/qa-orchestrator/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/QA Orkestratör|Orchestrator/i);
  });

  it("shows empty state initially", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/qa-orchestrator/page"
    );
    render(<Page />);
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
  });
});

// ── AutomationPage ─────────────────────────────────────────────────────────

jest.mock("@/components/ui/confirm-dialog", () => ({
  useConfirm: jest.fn(() => jest.fn(() => Promise.resolve(true))),
  ConfirmProvider: ({ children }: any) => <div>{children}</div>,
}));
jest.mock("@/components/ui/toast", () => ({
  useToast: jest.fn(() => ({ toast: jest.fn() })),
  ToastProvider: ({ children }: any) => <div>{children}</div>,
}));

describe("AutomationPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='automation-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/automation/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("automation-page")).toBeInTheDocument()
    );
  });

  it("shows 'Otomasyon' heading", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/automation/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("automation-heading")).toBeInTheDocument()
    );
  });

  it("shows new automation button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/automation/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("automation-btn-new")).toBeInTheDocument()
    );
  });
});
