/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// ── Suppress noise ─────────────────────────────────────────────────────────
const consoleSpies: jest.SpyInstance[] = [];
beforeEach(() => {
  consoleSpies.push(jest.spyOn(console, "error").mockImplementation(() => {}));
  consoleSpies.push(jest.spyOn(console, "warn").mockImplementation(() => {}));
  // jsdom stubs for DOM APIs used by pages
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
  (global as any).fetch = jest.fn(() => Promise.resolve({ json: () => Promise.resolve({}) }));
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
  useRouter: () => ({ push: jest.fn() }),
  useParams: () => ({}),
  usePathname: () => "/p/proj-1",
}));
jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

const apiMock = jest.fn();
jest.mock("@/lib/api", () => ({
  apiFetch: (...args: any[]) => apiMock(...args),
  ENGINE_BASE: "http://localhost:9000",
}));
jest.mock("@/lib/api-client", () => ({
  apiFetch: jest.fn(),
  API_BASE: "http://localhost:8000",
}));

jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title, right }: any) => <div data-testid="page-header">{title}{right}</div>,
  SectionCard: ({ title, children }: any) => (
    <div data-testid="section-card">{title && <div>{title}</div>}{children}</div>
  ),
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
  StatCard: ({ label, value }: any) => <div data-testid={`stat-${label}`}>{String(value)}</div>,
  MetricRow: ({ children }: any) => <div>{children}</div>,
  ToolbarActions: ({ children }: any) => <div>{children}</div>,
  StatusBadge: ({ status }: any) => <span>{status}</span>,
  FilterBar: ({ children }: any) => <div>{children}</div>,
}));
jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, right }: any) => <div data-testid="page-header">{title}{right}</div>,
}));
jest.mock("@/components/nexus/SectionCard", () => ({
  SectionCard: ({ title, children }: any) => (
    <div data-testid="section-card">{title && <div>{title}</div>}{children}</div>
  ),
}));
jest.mock("@/components/nexus/EmptyState", () => ({
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
}));
jest.mock("@/components/nexus/StatCard", () => ({
  StatCard: ({ label, value }: any) => <div data-testid={`stat-${label}`}>{String(value)}</div>,
}));
jest.mock("@/components/nexus/MetricRow", () => ({
  MetricRow: ({ children }: any) => <div>{children}</div>,
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
  Badge: ({ children }: any) => <span>{children}</span>,
}));
jest.mock("@/components/ui/modal", () => ({
  Modal: ({ children, open }: any) => open ? <div data-testid="modal">{children}</div> : null,
  ModalContent: ({ children }: any) => <div>{children}</div>,
  ModalHeader: ({ children }: any) => <div>{children}</div>,
  ModalTitle: ({ children }: any) => <h2>{children}</h2>,
  ModalFooter: ({ children }: any) => <div>{children}</div>,
}));
jest.mock("@/components/FlowGuideCard", () => ({
  FlowGuideCard: ({ title }: any) => <div data-testid="flow-guide-card">{title}</div>,
}));

// dnd-kit
jest.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: any) => <div>{children}</div>,
  closestCenter: jest.fn(),
  KeyboardSensor: jest.fn(),
  PointerSensor: jest.fn(),
  useSensor: jest.fn(),
  useSensors: jest.fn(() => []),
  DragOverlay: ({ children }: any) => <div>{children}</div>,
}));
jest.mock("@dnd-kit/sortable", () => ({
  SortableContext: ({ children }: any) => <div>{children}</div>,
  sortableKeyboardCoordinates: jest.fn(),
  verticalListSortingStrategy: jest.fn(),
  arrayMove: jest.fn((arr: any[]) => arr),
  useSortable: jest.fn(() => ({
    attributes: {},
    listeners: {},
    setNodeRef: jest.fn(),
    transform: null,
    transition: null,
    isDragging: false,
  })),
}));
jest.mock("@dnd-kit/utilities", () => ({
  CSS: { Transform: { toString: jest.fn(() => "") } },
}));

// useFetch / useMutate
jest.mock("@/lib/useFetch", () => ({
  useFetch: jest.fn(() => ({ data: [], loading: false, error: null, refresh: jest.fn() })),
  useMutate: jest.fn(() => ({ mutate: jest.fn(), loading: false, error: null })),
}));

// useWebSocket
jest.mock("@/lib/useWebSocket", () => ({
  useWebSocket: jest.fn(() => ({ connect: jest.fn(), disconnect: jest.fn(), send: jest.fn(), status: "closed" })),
}));

// use-synthetic-advanced
jest.mock("@/lib/hooks/use-synthetic-advanced", () => ({
  useNLGenerate: jest.fn(() => ({ mutate: jest.fn(), loading: false, data: null, error: null })),
  usePrivacyReport: jest.fn(() => ({ data: null, loading: false, error: null })),
  usePrivacyAudit: jest.fn(() => ({ mutate: jest.fn(), loading: false })),
}));

// use-api-testing
jest.mock("@/lib/hooks/use-api-testing", () => ({
  usePrioritizedTests: jest.fn(() => ({ data: null, isLoading: true })),
  usePrioritizationStats: jest.fn(() => ({ data: null, isLoading: true })),
  useOptimalSuite: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
}));

// ai-gateway
jest.mock("@/lib/ai-gateway", () => ({
  nexusCodeStream: jest.fn(),
}));

// product
jest.mock("@/lib/product", () => ({
  PRODUCT_FAMILY: [{ id: "one", name: "TestwrightAI", shortName: "TW", tagline: "", description: "", availability: "ga", defaultEntryKey: "scenarios", routeSegments: [] }],
  PRODUCT_FAMILY_BY_ID: { one: { id: "one", name: "TestwrightAI" } },
  DEFAULT_PRODUCT_FAMILY_ID: "one",
}));

// xlsx (for nexus-code page)
jest.mock("xlsx", () => ({ utils: { aoa_to_sheet: jest.fn(), book_new: jest.fn(), book_append_sheet: jest.fn() }, writeFile: jest.fn() }), { virtual: true });

// ─── ScenarioListPage ──────────────────────────────────────────────────────

describe("ScenarioListPage", () => {
  beforeEach(() => {
    apiMock.mockResolvedValue([
      { id: "s1", title: "Login testi", description: "Login akışı", status: "active", tags: [], created_at: "2026-01-01" },
      { id: "s2", title: "Ödeme testi", description: "Ödeme akışı", status: "draft", tags: [], created_at: "2026-01-02" },
    ]);
  });

  it("renders data-testid='scenarios-page' or page header", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/scenarios/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Senaryolar")).toBeInTheDocument()
    );
  });

  it("shows scenario titles after load", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/scenarios/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByText("Login testi")).toBeInTheDocument());
    expect(screen.getByText("Ödeme testi")).toBeInTheDocument();
  });

  it("shows 'Yeni Senaryo' button", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/scenarios/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("scenarios-new-btn")).toBeInTheDocument()
    );
  });

  it("shows empty state when no scenarios", async () => {
    apiMock.mockResolvedValueOnce([]);
    const { default: Page } = await import("../(dashboard)/p/[projectId]/scenarios/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("empty-state")).toBeInTheDocument()
    );
  });

  it("renders scenario rows with testids", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/scenarios/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("scenarios-row-s1")).toBeInTheDocument()
    );
  });
});

// ─── RequirementsPage ──────────────────────────────────────────────────────

describe("RequirementsPage", () => {
  beforeEach(() => {
    apiMock.mockResolvedValue([
      { id: "req-1", external_id: "REQ-001", title: "Kullanıcı girişi", description: "Login", priority: "high", source: "jira", scenario_count: 2, created_at: "2026-01-01" },
    ]);
  });

  it("renders data-testid='requirements-page'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/requirements/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("requirements-page")).toBeInTheDocument()
    );
  });

  it("shows page heading 'Gereksinimler'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/requirements/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Gereksinimler")).toBeInTheDocument()
    );
  });

  it("shows requirement title after load", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/requirements/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Kullanıcı girişi")).toBeInTheDocument()
    );
  });

  it("renders 'Yeni Gereksinim Ekle' button or equivalent", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/requirements/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("requirements-btn-new")).toBeInTheDocument()
    );
  });

  it("shows create form with title input after clicking new button", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/requirements/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByTestId("requirements-btn-new")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("requirements-btn-new"));
    await waitFor(() =>
      expect(screen.getByTestId("requirements-input-title")).toBeInTheDocument()
    );
  });
});

// ─── TestDataPage ──────────────────────────────────────────────────────────

describe("TestDataPage", () => {
  beforeEach(() => {
    apiMock.mockResolvedValue([
      { id: "ds-1", name: "Users CSV", format: "csv", row_count: 10, created_at: "2026-01-01" },
    ]);
  });

  it("renders data-testid='test-data-page'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/test-data/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("test-data-page")).toBeInTheDocument()
    );
  });

  it("shows heading 'Test Verileri'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/test-data/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Test Verileri")).toBeInTheDocument()
    );
  });

  it("renders dataset name after load", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/test-data/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Users CSV")).toBeInTheDocument()
    );
  });

  it("shows '+ Yeni Veri Seti' button", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/test-data/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("+ Yeni Veri Seti")).toBeInTheDocument()
    );
  });

  it("shows empty state when no datasets", async () => {
    apiMock.mockResolvedValueOnce([]);
    const { default: Page } = await import("../(dashboard)/p/[projectId]/test-data/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Veri seti yok")).toBeInTheDocument()
    );
  });
});

// ─── WorkflowsPage ─────────────────────────────────────────────────────────

describe("WorkflowsPage", () => {
  const { useFetch } = require("@/lib/useFetch");

  beforeEach(() => {
    useFetch.mockImplementation((url: string) => {
      if (url && url.includes("executions")) {
        return { data: [], loading: false, error: null, refresh: jest.fn() };
      }
      return {
        data: [
          { id: "wf-1", name: "Test Workflow", description: "Automation", n8n_workflow_id: "n8n-123", trigger_on: "manual", is_active: true, last_triggered_at: null, created_at: "2026-01-01" },
        ],
        loading: false,
        error: null,
        refresh: jest.fn(),
      };
    });
  });

  it("renders data-testid='workflows-page'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/workflows/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("workflows-page")).toBeInTheDocument()
    );
  });

  it("shows heading 'n8n Workflows'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/workflows/page");
    render(<Page />);
    expect(screen.getByTestId("workflows-heading")).toBeInTheDocument();
  });

  it("shows workflow card", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/workflows/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("workflows-card-wf-1")).toBeInTheDocument()
    );
  });

  it("shows 'Yeni Workflow' button", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/workflows/page");
    render(<Page />);
    expect(screen.getByTestId("workflows-btn-new")).toBeInTheDocument();
  });

  it("shows workflow name", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/workflows/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Test Workflow")).toBeInTheDocument()
    );
  });
});

// ─── AutomationGenPage ─────────────────────────────────────────────────────

describe("AutomationGenPage", () => {
  beforeEach(() => {
    apiMock.mockResolvedValue([]);
  });

  it("renders data-testid='automation-gen-page'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/automation-gen/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("automation-gen-page")).toBeInTheDocument()
    );
  });

  it("shows heading 'Otomasyon Üretimi'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/automation-gen/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Otomasyon Üretimi")).toBeInTheDocument()
    );
  });

  it("renders form with feature-name input", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/automation-gen/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("feature-name-input")).toBeInTheDocument()
    );
  });

  it("renders generate button", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/automation-gen/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("generate-button")).toBeInTheDocument()
    );
  });

  it("shows 'Test Case Kaynağı' label for batch source", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/automation-gen/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Test Case Kaynağı")).toBeInTheDocument()
    );
  });
});

// ─── PrioritizePage ────────────────────────────────────────────────────────

describe("PrioritizePage", () => {
  const { usePrioritizedTests, usePrioritizationStats, useOptimalSuite } = require("@/lib/hooks/use-api-testing");

  beforeEach(() => {
    usePrioritizedTests.mockReturnValue({
      data: {
        items: [
          {
            test_case_id: "tc-1",
            title: "POST /login testi",
            test_type: "api",
            priority_score: 85,
            endpoint_path: "/login",
            endpoint_method: "POST",
            risk_level: "high",
            estimated_duration_ms: 300,
            last_run_status: "pass",
            breakdown: { failure: 30, risk: 25, recency: 15, sensitivity: 10, change_impact: 5 },
          },
        ],
        total_count: 1,
      },
      isLoading: false,
    });
    usePrioritizationStats.mockReturnValue({
      data: {
        total_tests: 10,
        avg_score: 65,
        high_priority_count: 3,
        medium_priority_count: 4,
        low_priority_count: 3,
        quarantined_skipped: 1,
        risk_distribution: { high: 3, medium: 4, low: 3 },
        estimated_total_duration_ms: 30000,
      },
      isLoading: false,
    });
    useOptimalSuite.mockReturnValue({ mutate: jest.fn(), isPending: false });
  });

  it("renders data-testid='prioritize-page'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/prioritize/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("prioritize-page")).toBeInTheDocument()
    );
  });

  it("shows heading 'Test Önceliklendirme'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/prioritize/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Test Önceliklendirme")).toBeInTheDocument()
    );
  });

  it("renders priority table with test data", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/prioritize/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("priority-table")).toBeInTheDocument()
    );
  });

  it("shows test title in table", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/prioritize/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("POST /login testi")).toBeInTheDocument()
    );
  });

  it("shows empty state when no prioritized tests", async () => {
    usePrioritizedTests.mockReturnValueOnce({ data: { items: [], total_count: 0 }, isLoading: false });
    const { default: Page } = await import("../(dashboard)/p/[projectId]/prioritize/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("empty-state")).toBeInTheDocument()
    );
  });
});

// ─── CicdPage ──────────────────────────────────────────────────────────────

describe("CicdPage", () => {
  const { useFetch } = require("@/lib/useFetch");

  beforeEach(() => {
    useFetch.mockReturnValue({
      data: { events: [], total: 0 },
      loading: false,
      error: null,
      refresh: jest.fn(),
    });
    apiMock.mockResolvedValue({});
  });

  it("renders data-testid='cicd-page'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/cicd/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("cicd-page")).toBeInTheDocument()
    );
  });

  it("shows heading 'CI/CD Entegrasyonu'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/cicd/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("CI/CD Entegrasyonu")).toBeInTheDocument()
    );
  });

  it("shows 'CI/CD ve otomatik koşu akisi' section", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/cicd/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("CI/CD ve otomatik koşu akisi")).toBeInTheDocument()
    );
  });

  it("renders empty-state when no events", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/cicd/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("empty-state")).toBeInTheDocument()
    );
  });

  it("renders GitHub Actions integration section", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/cicd/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Webhook URL'leri")).toBeInTheDocument()
    );
  });
});

// ─── NlTestGenPage ─────────────────────────────────────────────────────────

describe("NlTestGenPage", () => {
  const { useNLGenerate } = require("@/lib/hooks/use-synthetic-advanced");

  beforeEach(() => {
    useNLGenerate.mockReturnValue({ mutate: jest.fn(), loading: false, data: null, error: null });
  });

  it("renders data-testid='nl-test-gen-page'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/nl-test-gen/page");
    render(<Page />);
    expect(screen.getByTestId("nl-test-gen-page")).toBeInTheDocument();
  });

  it("shows heading 'Dogal Dil Test Uretici'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/nl-test-gen/page");
    render(<Page />);
    expect(screen.getByText("Dogal Dil Test Uretici")).toBeInTheDocument();
  });

  it("renders format selector buttons (Pytest, Playwright...)", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/nl-test-gen/page");
    render(<Page />);
    expect(screen.getByText(/Pytest/i)).toBeInTheDocument();
  });

  it("renders language selector", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/nl-test-gen/page");
    render(<Page />);
    expect(screen.getByText("Python")).toBeInTheDocument();
  });

  it("shows result empty state when no generation", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/nl-test-gen/page");
    render(<Page />);
    expect(screen.getByText("Dogal Dil ile Test Ureti")).toBeInTheDocument();
  });
});

// ─── BankingTeamPage ───────────────────────────────────────────────────────

describe("BankingTeamPage", () => {
  const { useWebSocket } = require("@/lib/useWebSocket");

  beforeEach(() => {
    useWebSocket.mockReturnValue({
      connect: jest.fn(),
      disconnect: jest.fn(),
      send: jest.fn(),
      status: "closed",
    });
    apiMock.mockResolvedValue({});
  });

  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/banking-team/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows 'Banking QA Ekibi' heading", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/banking-team/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Banking QA Ekibi")).toBeInTheDocument()
    );
  });

  it("shows start button in initial state", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/banking-team/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("banking-team-start")).toBeInTheDocument()
    );
  });

  it("renders Konfigürasyon section when not started", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/banking-team/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Konfigürasyon")).toBeInTheDocument()
    );
  });

  it("renders tab navigation (Canlı Log, Final Rapor, Senaryolar)", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/banking-team/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Canlı Log")).toBeInTheDocument()
    );
    expect(screen.getByText("Final Rapor")).toBeInTheDocument();
    expect(screen.getAllByText("Senaryolar").length).toBeGreaterThanOrEqual(1);
  });
});

// ─── NexusCodePage ─────────────────────────────────────────────────────────

describe("NexusCodePage", () => {
  const { nexusCodeStream } = require("@/lib/ai-gateway");

  beforeEach(() => {
    (nexusCodeStream as jest.Mock).mockResolvedValue({ content: "test output" });
  });

  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/nexus-code/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows mode selector buttons (Kod Analizi, Web Analizi, Bitbucket)", async () => {
    const { default: Page } = await import("../(dashboard)/nexus-code/page");
    render(<Page />);
    expect(screen.getAllByText("Kod Analizi").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Web Analizi").length).toBeGreaterThanOrEqual(1);
  });

  it("shows domain options (Bankacılık, Finans)", async () => {
    const { default: Page } = await import("../(dashboard)/nexus-code/page");
    render(<Page />);
    expect(screen.getByText("Bankacılık")).toBeInTheDocument();
    expect(screen.getByText("Finans")).toBeInTheDocument();
  });

  it("renders quick suggestion buttons", async () => {
    const { default: Page } = await import("../(dashboard)/nexus-code/page");
    render(<Page />);
    expect(screen.getByText("Sayfa Yapısı Analizi")).toBeInTheDocument();
  });

  it("shows generate button", async () => {
    const { default: Page } = await import("../(dashboard)/nexus-code/page");
    render(<Page />);
    const generateBtns = screen.getAllByRole("button");
    expect(generateBtns.length).toBeGreaterThan(0);
  });
});
