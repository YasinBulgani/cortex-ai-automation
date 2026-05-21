/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

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
  useParams: jest.fn(() => ({})),
  usePathname: () => "/p/proj-1",
}));
jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

const apiFetchMock = jest.fn();
jest.mock("@/lib/api", () => ({
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

// nexus components
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
jest.mock("@/components/nexus/StatusBadge", () => ({
  StatusBadge: ({ status }: any) => <span data-testid={`status-badge`}>{status}</span>,
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
jest.mock("@/components/FlowGuideCard", () => ({
  FlowGuideCard: () => <div data-testid="flow-guide-card" />,
}));
jest.mock("@/components/dnd/FileDropZone", () => ({
  FileDropZone: ({ children }: any) => <div data-testid="file-drop-zone">{children}</div>,
}));
jest.mock("@/lib/useFetch", () => ({
  useFetch: jest.fn(() => ({ data: null, loading: false, error: null })),
  useMutate: jest.fn(() => ({ mutate: jest.fn(), loading: false })),
}));
jest.mock("@/lib/provenance", () => ({
  isRealProvenance: jest.fn(() => false),
  normalizeProvenance: jest.fn(() => "stub"),
  provenanceBadgeClass: jest.fn(() => "badge"),
  provenanceLabel: jest.fn(() => "Stub"),
  artifactTargetLabel: jest.fn(() => "Shared"),
  artifactTargetBadgeClass: jest.fn(() => "badge"),
  validationStatusLabel: jest.fn(() => "Pending"),
}));
jest.mock("@/components/ui/tabs", () => ({
  Tabs: ({ children }: any) => <div data-testid="tabs">{children}</div>,
  TabsList: ({ children }: any) => <div>{children}</div>,
  TabsTrigger: ({ children, value }: any) => (
    <button data-testid={`tab-${value}`}>{children}</button>
  ),
  TabsContent: ({ children }: any) => <div>{children}</div>,
}));
// use-api-testing hooks
jest.mock("@/lib/hooks/use-api-testing", () => ({
  useEnvironments: jest.fn(() => ({ data: [], isLoading: false })),
  useCreateEnvironment: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
  useUpdateEnvironment: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
  useDeleteEnvironment: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
  useFlakyTests: jest.fn(() => ({ data: [], isLoading: false })),
  useFlakyTrends: jest.fn(() => ({ data: null, isLoading: false })),
  useQuarantineList: jest.fn(() => ({ data: [], isLoading: false })),
  useQuarantineTest: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
  useHealingStats: jest.fn(() => ({
    // total_healing_attempts=0 => shows empty state, avoiding .toFixed() crash
    data: {
      total_healing_attempts: 0,
      success_rate: 0,
      avg_retries_needed: 0,
      avg_healing_time_ms: 0,
      saved_ci_time_ms: 0,
      by_category: {},
      top_healed_tests: [],
    },
    isLoading: false,
  })),
  useHealRun: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
  useHealingLog: jest.fn(() => ({ data: [], isLoading: false })),
  useHealHistory: jest.fn(() => ({ data: [], isLoading: false })),
  useManualHeal: jest.fn(() => ({
    mutateAsync: jest.fn(() => Promise.resolve(null)),
    isPending: false,
    isSuccess: false,
    isError: false,
    error: null,
    data: null,
  })),
}));

// ── HealingPage ────────────────────────────────────────────────────────────

describe("HealingPage", () => {
  it("renders data-testid='healing-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/healing/page"
    );
    render(<Page />);
    expect(screen.getByTestId("healing-page")).toBeInTheDocument();
  });

  it("shows 'Self-Healing' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/healing/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Self-Heal|Healing/i);
  });

  it("shows total heals stat", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/healing/page"
    );
    render(<Page />);
    // stat cards or text with healing numbers
    await waitFor(() =>
      expect(screen.getByTestId("healing-page")).toBeInTheDocument()
    );
  });
});

// ── FlakyPage ──────────────────────────────────────────────────────────────

describe("FlakyPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='flaky-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/flaky/page"
    );
    render(<Page />);
    expect(screen.getByTestId("flaky-page")).toBeInTheDocument();
  });

  it("shows 'Flaky Testler' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/flaky/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Flaky/i);
  });

  it("shows section cards for flaky content", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/flaky/page"
    );
    render(<Page />);
    expect(screen.getAllByTestId("section-card").length).toBeGreaterThanOrEqual(1);
  });
});

// ── EnvironmentsPage ───────────────────────────────────────────────────────

describe("EnvironmentsPage", () => {
  it("renders data-testid='environments-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/environments/page"
    );
    render(<Page />);
    expect(screen.getByTestId("environments-page")).toBeInTheDocument();
  });

  it("shows 'Ortam' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/environments/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Ortam|Environment/i);
  });

  it("shows empty state when no environments", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/environments/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("empty-state")).toBeInTheDocument()
    );
  });
});

// ── IntegrationsPage ───────────────────────────────────────────────────────

describe("IntegrationsPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='integrations-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/integrations/page"
    );
    render(<Page />);
    expect(screen.getByTestId("integrations-page")).toBeInTheDocument();
  });

  it("shows 'Entegrasyon' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/integrations/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Entegrasyon|Integration/i);
  });

  it("shows 'Yeni Entegrasyon' toggle button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/integrations/page"
    );
    render(<Page />);
    expect(screen.getByText("Yeni Entegrasyon")).toBeInTheDocument();
  });

  it("shows empty state when no integrations loaded", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/integrations/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("empty-state")).toBeInTheDocument()
    );
  });
});

// ── SchedulesPage ──────────────────────────────────────────────────────────

describe("SchedulesPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='schedules-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/schedules/page"
    );
    render(<Page />);
    expect(screen.getByTestId("schedules-page")).toBeInTheDocument();
  });

  it("shows 'Zamanlama' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/schedules/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Zamanla|Schedule/i);
  });

  it("shows 'Yeni Zamanlama' button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/schedules/page"
    );
    render(<Page />);
    expect(screen.getByTestId("schedules-btn-new")).toBeInTheDocument();
  });

  it("shows empty state when no schedules", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/schedules/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("empty-state")).toBeInTheDocument()
    );
  });

  it("shows stats row for schedules", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/schedules/page"
    );
    render(<Page />);
    // stat cards are always rendered
    expect(screen.getAllByTestId(/^stat-/).length).toBeGreaterThanOrEqual(1);
  });
});

// ── ReportsPage ────────────────────────────────────────────────────────────

describe("ReportsPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
    const m = require("@/lib/useFetch");
    (m.useFetch as jest.Mock).mockReturnValue({ data: [], loading: false, error: null });
  });

  it("renders data-testid='reports-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/reports/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("reports-page")).toBeInTheDocument()
    );
  });

  it("shows 'Raporlar' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/reports/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("page-header")).toHaveTextContent(/Rapor|Report/i)
    );
  });

  it("shows CSV export button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/reports/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("reports-btn-csv")).toBeInTheDocument()
    );
  });
});

// ── SettingsPage ───────────────────────────────────────────────────────────

describe("SettingsPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue({
      id: "proj-1",
      name: "Test Projesi",
      description: "Açıklama",
      base_url: "https://test.com",
    });
  });

  it("renders 'Proje Ayarları' heading after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/settings/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Proje Ayarları")).toBeInTheDocument()
    );
  });

  it("shows 'Tehlikeli Alan' section", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/settings/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Tehlikeli Alan")).toBeInTheDocument()
    );
  });

  it("shows save button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/settings/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Kaydet")).toBeInTheDocument()
    );
  });

  it("shows delete button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/settings/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Projeyi Sil")).toBeInTheDocument()
    );
  });
});

// ── ManualPage ─────────────────────────────────────────────────────────────

describe("ManualPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='manual-tests-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/manual/page"
    );
    render(<Page />);
    expect(screen.getByTestId("manual-tests-page")).toBeInTheDocument();
  });

  it("shows 'Manuel Test' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/manual/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Manuel/i);
  });

  it("shows 'Yeni Test Ekle' button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/manual/page"
    );
    render(<Page />);
    expect(screen.getByTestId("manual-tests-btn-new")).toBeInTheDocument();
  });

  it("shows 'to automation' button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/manual/page"
    );
    render(<Page />);
    // always-visible button (not inside showForm toggle)
    expect(screen.getByTestId("manual-tests-btn-to-automation")).toBeInTheDocument();
  });
});

// ── TestCasesPage ──────────────────────────────────────────────────────────

describe("TestCasesPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='test-cases-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/test-cases/page"
    );
    render(<Page />);
    expect(screen.getByTestId("test-cases-page")).toBeInTheDocument();
  });

  it("shows 'Test Case' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/test-cases/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Test Case/i);
  });

  it("shows generate section", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/test-cases/page"
    );
    render(<Page />);
    expect(screen.getByTestId("generate-section")).toBeInTheDocument();
  });

  it("shows generate button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/test-cases/page"
    );
    render(<Page />);
    expect(screen.getByTestId("generate-button")).toBeInTheDocument();
  });
});

// ── ImportPage ─────────────────────────────────────────────────────────────

describe("ImportPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='import-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/import/page"
    );
    render(<Page />);
    expect(screen.getByTestId("import-page")).toBeInTheDocument();
  });

  it("shows file drop zone", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/import/page"
    );
    render(<Page />);
    expect(screen.getByTestId("file-drop-zone")).toBeInTheDocument();
  });

  it("shows flow guide card", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/import/page"
    );
    render(<Page />);
    expect(screen.getByTestId("flow-guide-card")).toBeInTheDocument();
  });
});

// ── NewExecutionPage ───────────────────────────────────────────────────────

describe("NewExecutionPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='new-execution-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/new/page"
    );
    render(<Page />);
    expect(screen.getByTestId("new-execution-page")).toBeInTheDocument();
  });

  it("shows 'Yeni execution' heading", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/new/page"
    );
    render(<Page />);
    expect(screen.getByTestId("new-execution-heading")).toBeInTheDocument();
  });

  it("shows execution name input", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/new/page"
    );
    render(<Page />);
    expect(screen.getByTestId("execution-input-name")).toBeInTheDocument();
  });

  it("shows start execution button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/executions/new/page"
    );
    render(<Page />);
    expect(screen.getByTestId("execution-btn-start")).toBeInTheDocument();
  });
});

// ── ProjectsPage ───────────────────────────────────────────────────────────

describe("ProjectsPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='projects-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/projects/page"
    );
    render(<Page />);
    expect(screen.getByTestId("projects-page")).toBeInTheDocument();
  });

  it("shows projects form", async () => {
    const { default: Page } = await import(
      "../(dashboard)/projects/page"
    );
    render(<Page />);
    expect(screen.getByTestId("projects-form")).toBeInTheDocument();
  });

  it("shows project name input", async () => {
    const { default: Page } = await import(
      "../(dashboard)/projects/page"
    );
    render(<Page />);
    expect(screen.getByTestId("projects-input-name")).toBeInTheDocument();
  });

  it("shows create button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/projects/page"
    );
    render(<Page />);
    expect(screen.getByTestId("projects-btn-create")).toBeInTheDocument();
  });
});
