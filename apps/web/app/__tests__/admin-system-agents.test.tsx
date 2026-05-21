/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// ─── Suppress console noise ────────────────────────────────────────────────
beforeAll(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  jest.spyOn(console, "warn").mockImplementation(() => {});
});

// global fetch — AdminSettingsPage on main calls fetch() for pm2/health status.
// Return well-formed payloads so the page can iterate over processes/services.
beforeEach(() => {
  (global as any).fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          processes: [],
          services: [],
          summary: { total: 0, online: 0 },
        }),
    })
  );
});
afterAll(() => {
  (console.error as jest.Mock).mockRestore();
  (console.warn as jest.Mock).mockRestore();
});

// ─── Standard mocks ────────────────────────────────────────────────────────
jest.mock("next/link", () =>
  function MockLink({ href, children, ...rest }: any) {
    return <a href={href} {...rest}>{children}</a>;
  }
);

jest.mock("next/navigation", () => {
  const useParamsMock = jest.fn(() => ({ agentId: "monkey-testing" }));
  const pushMock = jest.fn();
  return {
    __useParamsMock: useParamsMock,
    __pushMock: pushMock,
    useRouter: () => ({ push: pushMock }),
    useParams: () => useParamsMock(),
  };
});

jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
  usePathname: () => "/p/proj-1",
}));

jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn(),
  ENGINE_BASE: "http://localhost:5001",
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

jest.mock("@/lib/api-client", () => ({
  apiFetch: jest.fn(),
  getToken: jest.fn(() => "fake-token"),
}));

jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">{title}{right}</div>
  ),
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

jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">{title}{right}</div>
  ),
  SectionCard: ({ title, children, right }: any) => (
    <div data-testid="section-card">
      {title && <div>{title}</div>}
      {right && <div>{right}</div>}
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
}));

jest.mock("@/lib/hooks/use-agents", () => ({
  useAgents: jest.fn(() => ({ data: undefined, isLoading: false })),
  useAgent: jest.fn(() => ({ data: undefined, isLoading: false })),
  useRunAgent: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
  useStopAgent: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
  useAgentRecentRuns: jest.fn(() => ({ data: { runs: [] }, isLoading: false })),
  useAgentsCatalog: jest.fn(() => ({ agents: [], isLive: false })),
  useAgentRun: jest.fn(() => ({ mutateAsync: jest.fn(() => Promise.resolve(null)), isPending: false })),
}));

// core-runtime mock – used by SystemServicesPage
jest.mock("@/lib/core-runtime", () => ({
  useCoreRuntime: jest.fn(() => ({
    loading: false,
    backendReady: false,
    services: [],
    checkedAt: null,
    authState: "ready",
    canQueryProjects: true,
    blockingReason: null,
    error: null,
    refresh: jest.fn(),
  })),
}));

// ─── Lazy imports (after mocks) ────────────────────────────────────────────
import { apiFetch } from "@/lib/api";
import { useCoreRuntime } from "@/lib/core-runtime";

const mockApiFetch = apiFetch as jest.Mock;
const mockUseCoreRuntime = useCoreRuntime as jest.Mock;

// =============================================================================
// 1. ADMIN AUDIT PAGE
// =============================================================================
describe("AuditLogPage", () => {
  beforeEach(() => {
    mockApiFetch.mockResolvedValue([]);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the page container with data-testid", async () => {
    const { default: AuditLogPage } = await import(
      "@/app/(dashboard)/admin/audit/page"
    );
    render(<AuditLogPage />);
    expect(screen.getByTestId("audit-page")).toBeInTheDocument();
  });

  it("renders the PageHeader with correct title", async () => {
    const { default: AuditLogPage } = await import(
      "@/app/(dashboard)/admin/audit/page"
    );
    render(<AuditLogPage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(
      "Denetim Günlüğü"
    );
  });

  it("renders the audit table", async () => {
    const { default: AuditLogPage } = await import(
      "@/app/(dashboard)/admin/audit/page"
    );
    render(<AuditLogPage />);
    expect(screen.getByTestId("audit-table")).toBeInTheDocument();
  });

  it("shows 'Kayıt bulunamadı' when no events are returned", async () => {
    const { default: AuditLogPage } = await import(
      "@/app/(dashboard)/admin/audit/page"
    );
    render(<AuditLogPage />);
    await waitFor(() => {
      expect(screen.getByText("Kayıt bulunamadı")).toBeInTheDocument();
    });
  });

  it("renders audit rows when events are returned", async () => {
    mockApiFetch.mockResolvedValueOnce([
      {
        id: "evt-1",
        ts: new Date().toISOString(),
        actor_email: "admin@test.com",
        actor_name: "Admin User",
        action: "create",
        resource_type: "project",
        resource_id: "abcdefgh1234",
      },
    ]);
    const { default: AuditLogPage } = await import(
      "@/app/(dashboard)/admin/audit/page"
    );
    render(<AuditLogPage />);
    await waitFor(() => {
      expect(screen.getByTestId("audit-row-evt-1")).toBeInTheDocument();
    });
    expect(screen.getByText("Admin User")).toBeInTheDocument();
  });
});

// =============================================================================
// 2. ADMIN SETTINGS PAGE
// =============================================================================
describe("AdminSettingsPage", () => {
  beforeEach(() => {
    mockApiFetch.mockResolvedValue({
      providers: [
        { id: "openai", name: "openai", configured: true },
        { id: "ollama", name: "ollama", configured: false },
      ],
      active: "openai",
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the page container with data-testid", async () => {
    const { default: AdminSettingsPage } = await import(
      "@/app/(dashboard)/admin/settings/page"
    );
    render(<AdminSettingsPage />);
    expect(screen.getByTestId("admin-settings-page")).toBeInTheDocument();
  });

  it("renders the PageHeader with 'AI Ayarları' title", async () => {
    const { default: AdminSettingsPage } = await import(
      "@/app/(dashboard)/admin/settings/page"
    );
    render(<AdminSettingsPage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("AI Ayarları");
  });

  it("renders provider buttons after data loads", async () => {
    const { default: AdminSettingsPage } = await import(
      "@/app/(dashboard)/admin/settings/page"
    );
    render(<AdminSettingsPage />);
    await waitFor(() => {
      expect(screen.getByTestId("settings-provider-openai")).toBeInTheDocument();
    });
    expect(screen.getByTestId("settings-provider-ollama")).toBeInTheDocument();
  });

  it("renders the save button", async () => {
    const { default: AdminSettingsPage } = await import(
      "@/app/(dashboard)/admin/settings/page"
    );
    render(<AdminSettingsPage />);
    await waitFor(() => {
      expect(screen.getByTestId("settings-btn-save-provider")).toBeInTheDocument();
    });
  });

  it("save button is disabled when already-active provider is selected", async () => {
    const { default: AdminSettingsPage } = await import(
      "@/app/(dashboard)/admin/settings/page"
    );
    render(<AdminSettingsPage />);
    await waitFor(() => {
      expect(screen.getByTestId("settings-provider-openai")).toBeInTheDocument();
    });
    // openai is active — save button should be disabled
    const saveBtn = screen.getByTestId("settings-btn-save-provider");
    expect(saveBtn).toBeDisabled();
  });
});

// =============================================================================
// 3. SYSTEM SERVICES PAGE
// =============================================================================
describe("SystemServicesPage", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the page main content and 'System Services' heading", async () => {
    const { default: SystemServicesPage } = await import(
      "@/app/(dashboard)/system/services/page"
    );
    render(<SystemServicesPage />);
    expect(screen.getByText("System Services")).toBeInTheDocument();
  });

  it("renders backend status card", async () => {
    const { default: SystemServicesPage } = await import(
      "@/app/(dashboard)/system/services/page"
    );
    render(<SystemServicesPage />);
    expect(screen.getByText("Backend")).toBeInTheDocument();
  });

  it("renders 'Yenile' (refresh) button", async () => {
    const { default: SystemServicesPage } = await import(
      "@/app/(dashboard)/system/services/page"
    );
    render(<SystemServicesPage />);
    expect(screen.getByText("Yenile")).toBeInTheDocument();
  });

  it("shows bulk action buttons (Start all / Restart all / Stop all)", async () => {
    const { default: SystemServicesPage } = await import(
      "@/app/(dashboard)/system/services/page"
    );
    render(<SystemServicesPage />);
    expect(screen.getByText("Start all")).toBeInTheDocument();
    expect(screen.getByText("Restart all")).toBeInTheDocument();
    expect(screen.getByText("Stop all")).toBeInTheDocument();
  });

  it("clicking 'Start all' opens the confirmation modal", async () => {
    const mockServices = [
      {
        name: "api",
        state: "stopped" as const,
        running: false,
        healthOk: null,
        healthDetail: "n/a",
      },
    ];
    mockUseCoreRuntime.mockReturnValue({
      loading: false,
      backendReady: true,
      services: mockServices,
      checkedAt: null,
      authState: "ready",
      canQueryProjects: true,
      blockingReason: null,
      error: null,
      refresh: jest.fn(),
    });

    const { default: SystemServicesPage } = await import(
      "@/app/(dashboard)/system/services/page"
    );
    render(<SystemServicesPage />);
    fireEvent.click(screen.getByText("Start all"));
    await waitFor(() => {
      expect(screen.getByText("Onay gerekli")).toBeInTheDocument();
    });
  });
});

// =============================================================================
// 4. AI AGENTS HUB PAGE
// =============================================================================
describe("AIAgentsHubPage", () => {
  it("renders the page with 'Neurex AI Ajanları' heading", async () => {
    const { default: AIAgentsHubPage } = await import(
      "@/app/(dashboard)/ai-agents/page"
    );
    render(<AIAgentsHubPage />);
    expect(screen.getByText("Neurex AI Ajanları")).toBeInTheDocument();
  });

  it("renders agent category sections", async () => {
    const { default: AIAgentsHubPage } = await import(
      "@/app/(dashboard)/ai-agents/page"
    );
    render(<AIAgentsHubPage />);
    // At least the 'Test Kalitesi' category should appear
    expect(screen.getByText("Test Kalitesi")).toBeInTheDocument();
  });

  it("renders individual agent cards with data-testid", async () => {
    const { default: AIAgentsHubPage } = await import(
      "@/app/(dashboard)/ai-agents/page"
    );
    render(<AIAgentsHubPage />);
    expect(screen.getByTestId("agent-card-monkey-testing")).toBeInTheDocument();
    expect(screen.getByTestId("agent-card-self-healing")).toBeInTheDocument();
  });

  it("renders the total agent count badge", async () => {
    const { default: AIAgentsHubPage } = await import(
      "@/app/(dashboard)/ai-agents/page"
    );
    render(<AIAgentsHubPage />);
    // Badge text ends with " Ajan"
    const badge = screen.getByText(/\d+ Ajan/);
    expect(badge).toBeInTheDocument();
  });

  it("agent card links point to the correct href", async () => {
    const { default: AIAgentsHubPage } = await import(
      "@/app/(dashboard)/ai-agents/page"
    );
    render(<AIAgentsHubPage />);
    const monkeyCard = screen.getByTestId("agent-card-monkey-testing");
    // Main may render the link wrapper as the card itself or wrap differently;
    // verify there's a link to the monkey-testing agent somewhere in the card.
    const link = monkeyCard.tagName === "A" ? monkeyCard : monkeyCard.closest("a") || monkeyCard.querySelector("a");
    expect(link).toBeTruthy();
    expect(link).toHaveAttribute("href", expect.stringContaining("monkey-testing"));
  });
});

// =============================================================================
// 5. AGENT DETAIL PAGE
// =============================================================================
describe("AgentDetailPage", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the agent name heading when agent is found", async () => {
    mockApiFetch.mockResolvedValue([]);
    const { default: AgentDetailPage } = await import(
      "@/app/(dashboard)/ai-agents/[agentId]/page"
    );
    render(<AgentDetailPage />);
    await waitFor(() => {
      // The agent name appears in the h1 heading
      expect(screen.getByRole("heading", { name: "Monkey Testing" })).toBeInTheDocument();
    });
  });

  it("renders 'Ajan bulunamadı' for an unknown agentId", async () => {
    // Override the mock to return an unknown id for this render
    const navModule = require("next/navigation") as { __useParamsMock: jest.Mock };
    navModule.__useParamsMock.mockImplementation(() => ({ agentId: "nonexistent-xyz" }));

    const { default: AgentDetailPage } = await import(
      "@/app/(dashboard)/ai-agents/[agentId]/page"
    );
    render(<AgentDetailPage />);
    expect(screen.getByText("Ajan bulunamadı")).toBeInTheDocument();

    // Restore default implementation
    navModule.__useParamsMock.mockImplementation(() => ({ agentId: "monkey-testing" }));
  });

  it("renders the project search input for a project-scoped agent", async () => {
    mockApiFetch.mockResolvedValue([
      { id: "p1", name: "Proje Alfa", archived: false },
    ]);
    const { default: AgentDetailPage } = await import(
      "@/app/(dashboard)/ai-agents/[agentId]/page"
    );
    render(<AgentDetailPage />);
    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("Proje ara...")
      ).toBeInTheDocument();
    });
  });

  it("renders the agent features list", async () => {
    mockApiFetch.mockResolvedValue([]);
    const { default: AgentDetailPage } = await import(
      "@/app/(dashboard)/ai-agents/[agentId]/page"
    );
    render(<AgentDetailPage />);
    await waitFor(() => {
      // First feature of monkey-testing agent
      expect(
        screen.getByText("Rastgele tıklama / kaydırma / yazı girişi")
      ).toBeInTheDocument();
    });
  });

  it("filters project list when typing in the search box", async () => {
    mockApiFetch.mockResolvedValue([
      { id: "p1", name: "Proje Alfa", archived: false },
      { id: "p2", name: "Proje Beta", archived: false },
    ]);
    const { default: AgentDetailPage } = await import(
      "@/app/(dashboard)/ai-agents/[agentId]/page"
    );
    render(<AgentDetailPage />);

    // Wait for projects to appear
    await waitFor(() => {
      expect(screen.getByText("Proje Alfa")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Proje ara...");
    fireEvent.change(searchInput, { target: { value: "Alfa" } });

    await waitFor(() => {
      expect(screen.queryByText("Proje Beta")).not.toBeInTheDocument();
      expect(screen.getByText("Proje Alfa")).toBeInTheDocument();
    });
  });
});
