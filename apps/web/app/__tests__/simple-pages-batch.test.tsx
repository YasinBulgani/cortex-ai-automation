/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ── Suppress noise ─────────────────────────────────────────────────────────
const consoleSpies: jest.SpyInstance[] = [];
beforeEach(() => {
  consoleSpies.push(jest.spyOn(console, "error").mockImplementation(() => {}));
  consoleSpies.push(jest.spyOn(console, "warn").mockImplementation(() => {}));
  (global as any).fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          status: "ok",
          providers: { openai: true, anthropic: false },
          version: "1.0",
          // AdminSettingsPage on main now expects pm2 + services shapes
          processes: [],
          services: [],
          summary: { total: 0, online: 0 },
        }),
    })
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
  useParams: () => ({}),
  redirect: jest.fn(),
  notFound: jest.fn(),
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

// Nexus components
jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title }: any) => <div data-testid="page-header">{title}</div>,
}));
jest.mock("@/components/nexus/SectionCard", () => ({
  SectionCard: ({ title, children }: any) => (
    <div data-testid="section-card">{title && <div>{title}</div>}{children}</div>
  ),
}));
jest.mock("@/components/nexus/EmptyState", () => ({
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
}));
jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title }: any) => <div data-testid="page-header">{title}</div>,
  SectionCard: ({ title, children }: any) => (
    <div data-testid="section-card">{title && <div>{title}</div>}{children}</div>
  ),
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
  StatCard: ({ label, value }: any) => <div data-testid={`stat-${label}`}>{String(value)}</div>,
  MetricRow: ({ children }: any) => <div>{children}</div>,
  ToolbarActions: ({ children }: any) => <div>{children}</div>,
  StatusBadge: ({ status }: any) => <span>{status}</span>,
  FilterBar: ({ children }: any) => <div>{children}</div>,
  ProgressBar: ({ value }: any) => <div data-testid="progress-bar">{value}</div>,
}));
jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, disabled, ...rest }: any) => (
    <button onClick={onClick} disabled={disabled} {...rest}>{children}</button>
  ),
}));
jest.mock("@/components/ui/input", () => ({
  Input: (props: any) => <input {...props} />,
}));
jest.mock("@/components/BgtestLogo", () => ({
  BgtestLogo: () => <div data-testid="bgtest-logo">Logo</div>,
}));
jest.mock("@neurex/design-system", () => ({
  StatCard: ({ label, value }: any) => <div data-testid={`stat-${label}`}>{String(value ?? "")}</div>,
  Avatar: ({ name }: any) => <div data-testid="avatar">{name}</div>,
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
}));
jest.mock("@/lib/useProject", () => ({
  useProject: jest.fn(() => ({
    project: { id: "proj-1", name: "Test Project" },
    setProject: jest.fn(),
    projectId: "proj-1",
  })),
}));

// ── use-agents hooks (ai-agents page on main calls these) ─────────────────
jest.mock("@/lib/hooks/use-agents", () => ({
  useAgents: jest.fn(() => ({ data: undefined, isLoading: false })),
  useAgent: jest.fn(() => ({ data: undefined, isLoading: false })),
  useRunAgent: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
  useStopAgent: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
  useAgentRecentRuns: jest.fn(() => ({ data: { runs: [] }, isLoading: false })),
  useAgentsCatalog: jest.fn(() => ({ agents: [], isLive: false })),
  useAgentRun: jest.fn(() => ({ mutateAsync: jest.fn(() => Promise.resolve(null)), isPending: false })),
}));

// ── agents-data mock (ai-agents page local import) ─────────────────────────
jest.mock("../(dashboard)/ai-agents/agents-data", () => ({
  AGENT_CATEGORIES: ["test-quality"],
  AGENTS_BY_CATEGORY: [
    {
      key: "test-quality",
      meta: { emoji: "🤖", label: "Test Kalitesi", color: "text-violet-300" },
      agents: [
        {
          id: "scenario-generator",
          name: "Senaryo Üretici",
          tagline: "BDD üretir",
          availability: "active",
          emoji: "📋",
          globalHref: null,
        },
      ],
    },
  ],
}));

// ── Root Dashboard Page ────────────────────────────────────────────────────

describe("RootDashboardPage (Aktivite Monitörü)", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue({
      total_projects: 5,
      total_scenarios: 42,
      active_executions: 3,
      overall_pass_rate: 87,
      pending_approvals: 2,
      weekly_trend: [],
      projects: [],
      activities: [],
    });
  });

  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows 'Aktivite Monitörü' heading", async () => {
    const { default: Page } = await import("../(dashboard)/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Aktivite Monitörü")).toBeInTheDocument()
    );
  });

  it("shows 'AI Sağlayıcıları' section", async () => {
    const { default: Page } = await import("../(dashboard)/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("AI Sağlayıcıları")).toBeInTheDocument()
    );
  });

  it("shows 'Aktif Projeler' section", async () => {
    const { default: Page } = await import("../(dashboard)/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Aktif Projeler")).toBeInTheDocument()
    );
  });

  it("shows 'Son Aktiviteler' section", async () => {
    const { default: Page } = await import("../(dashboard)/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Son Aktiviteler")).toBeInTheDocument()
    );
  });
});

// ── LogoutPage ─────────────────────────────────────────────────────────────

describe("LogoutPage", () => {
  it("renders data-testid='logout-page'", async () => {
    const { default: Page } = await import("../(dashboard)/logout/page");
    render(<Page />);
    expect(screen.getByTestId("logout-page")).toBeInTheDocument();
  });

  it("shows 'Çıkış Yapıldı' heading", async () => {
    const { default: Page } = await import("../(dashboard)/logout/page");
    render(<Page />);
    expect(screen.getByText("Çıkış Yapıldı")).toBeInTheDocument();
  });

  it("shows 'Ana sayfaya dön' link", async () => {
    const { default: Page } = await import("../(dashboard)/logout/page");
    render(<Page />);
    expect(screen.getByText("Ana sayfaya dön")).toBeInTheDocument();
  });

  it("shows logout link to homepage", async () => {
    const { default: Page } = await import("../(dashboard)/logout/page");
    render(<Page />);
    const link = screen.getByTestId("logout-link-home");
    expect(link).toHaveAttribute("href", "/");
  });
});

// ── InfoPage ───────────────────────────────────────────────────────────────

describe("InfoPage", () => {
  it("renders data-testid='info-page'", async () => {
    const { default: Page } = await import("../(dashboard)/info/page");
    render(<Page />);
    expect(screen.getByTestId("info-page")).toBeInTheDocument();
  });

  it("shows 'Sistem Bilgileri' in page header", async () => {
    const { default: Page } = await import("../(dashboard)/info/page");
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Sistem Bilgileri");
  });

  it("shows 'Neurex QA Operations' brand text", async () => {
    const { default: Page } = await import("../(dashboard)/info/page");
    render(<Page />);
    expect(screen.getByText("Neurex QA Operations")).toBeInTheDocument();
  });

  it("shows feature list with 'Test Senaryosu Yönetimi'", async () => {
    const { default: Page } = await import("../(dashboard)/info/page");
    render(<Page />);
    expect(screen.getByText("Test Senaryosu Yönetimi")).toBeInTheDocument();
  });

  it("shows version info", async () => {
    const { default: Page } = await import("../(dashboard)/info/page");
    render(<Page />);
    expect(screen.getByText("1.0.0-beta")).toBeInTheDocument();
  });
});

// ── SymbolsPage ────────────────────────────────────────────────────────────

describe("SymbolsPage", () => {
  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/symbols/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows 'Simge Yönetimi' in page header", async () => {
    const { default: Page } = await import("../(dashboard)/symbols/page");
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Simge Yönetimi");
  });

  it("shows 'Başarılı' status icon", async () => {
    const { default: Page } = await import("../(dashboard)/symbols/page");
    render(<Page />);
    expect(screen.getAllByText("Başarılı").length).toBeGreaterThanOrEqual(1);
  });

  it("shows 'Senaryolar' module icon", async () => {
    const { default: Page } = await import("../(dashboard)/symbols/page");
    render(<Page />);
    expect(screen.getByText("Senaryolar")).toBeInTheDocument();
  });
});

// ── AuditLogPage ───────────────────────────────────────────────────────────

describe("AuditLogPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([
      {
        id: "evt-1",
        ts: "2026-01-01T12:00:00Z",
        actor_email: "admin@test.com",
        actor_name: "Admin",
        action: "create",
        resource_type: "scenario",
        resource_id: "s-1",
      },
    ]);
  });

  it("renders data-testid='audit-page'", async () => {
    const { default: Page } = await import("../(dashboard)/admin/audit/page");
    render(<Page />);
    expect(screen.getByTestId("audit-page")).toBeInTheDocument();
  });

  it("shows 'Denetim Günlüğü' in page header", async () => {
    const { default: Page } = await import("../(dashboard)/admin/audit/page");
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Denetim Günlüğü");
  });

  it("shows event actor after load", async () => {
    const { default: Page } = await import("../(dashboard)/admin/audit/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("audit-row-evt-1")).toBeInTheDocument()
    );
  });

  it("shows page navigation buttons", async () => {
    const { default: Page } = await import("../(dashboard)/admin/audit/page");
    render(<Page />);
    expect(screen.getByTestId("audit-btn-prev")).toBeInTheDocument();
    expect(screen.getByTestId("audit-btn-next")).toBeInTheDocument();
  });
});

// ── AdminSettingsPage ──────────────────────────────────────────────────────

describe("AdminSettingsPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue({
      providers: [
        { id: "openai", name: "OpenAI", configured: true },
        { id: "anthropic", name: "Anthropic", configured: false },
      ],
      active: "openai",
    });
  });

  it("renders data-testid='admin-settings-page'", async () => {
    const { default: Page } = await import("../(dashboard)/admin/settings/page");
    render(<Page />);
    expect(screen.getByTestId("admin-settings-page")).toBeInTheDocument();
  });

  it("shows 'AI Ayarları' in page header", async () => {
    const { default: Page } = await import("../(dashboard)/admin/settings/page");
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("AI Ayarları");
  });

  it("shows provider names after load", async () => {
    const { default: Page } = await import("../(dashboard)/admin/settings/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("OpenAI")).toBeInTheDocument()
    );
    expect(screen.getByText("Anthropic")).toBeInTheDocument();
  });

  it("shows save button", async () => {
    const { default: Page } = await import("../(dashboard)/admin/settings/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText(/Kaydet|Aktif/i)).toBeInTheDocument()
    );
  });
});

// ── OnboardingPage ─────────────────────────────────────────────────────────

describe("OnboardingPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue({ id: "new-proj", name: "New Project" });
  });

  it("renders data-testid='onboarding-page'", async () => {
    const { default: Page } = await import("../(dashboard)/onboarding/page");
    render(<Page />);
    expect(screen.getByTestId("onboarding-page")).toBeInTheDocument();
  });

  // OnboardingPage was refactored into a 5-step wizard on main.
  // The old form (input-name / btn-create / btn-skip) was replaced.
  it("shows the initial 'Rolünüz nedir?' step heading", async () => {
    const { default: Page } = await import("../(dashboard)/onboarding/page");
    render(<Page />);
    expect(screen.getByText("Rolünüz nedir?")).toBeInTheDocument();
  });

  it("renders the page heading area (h1)", async () => {
    const { default: Page } = await import("../(dashboard)/onboarding/page");
    const { container } = render(<Page />);
    expect(container.querySelector("h1")).toBeInTheDocument();
  });

  it("renders inside the onboarding-page container", async () => {
    const { default: Page } = await import("../(dashboard)/onboarding/page");
    render(<Page />);
    // Sanity check — page mounts and the wizard layout is present
    expect(screen.getByTestId("onboarding-page")).toBeInTheDocument();
  });
});

// ── AIAgentsHubPage ────────────────────────────────────────────────────────

describe("AIAgentsHubPage", () => {
  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/ai-agents/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows 'Neurex AI Ajanları' heading", async () => {
    const { default: Page } = await import("../(dashboard)/ai-agents/page");
    render(<Page />);
    expect(screen.getByText("Neurex AI Ajanları")).toBeInTheDocument();
  });

  it("renders agent cards", async () => {
    const { default: Page } = await import("../(dashboard)/ai-agents/page");
    render(<Page />);
    expect(screen.getByTestId("agent-card-scenario-generator")).toBeInTheDocument();
  });

  it("shows agent name in card", async () => {
    const { default: Page } = await import("../(dashboard)/ai-agents/page");
    render(<Page />);
    expect(screen.getByText("Senaryo Üretici")).toBeInTheDocument();
  });

  it("shows portfolio link", async () => {
    const { default: Page } = await import("../(dashboard)/ai-agents/page");
    render(<Page />);
    expect(screen.getByText("📊 Portföy")).toBeInTheDocument();
  });
});

// ── FlowDesignerPage ───────────────────────────────────────────────────────

describe("FlowDesignerPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([
      { id: "proj-1", name: "Test Project" },
    ]);
  });

  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/flow-designer/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows 'Akış Tasarımcısı' heading", async () => {
    const { default: Page } = await import("../(dashboard)/flow-designer/page");
    render(<Page />);
    expect(screen.getByText("Akış Tasarımcısı")).toBeInTheDocument();
  });

  it("shows category filter buttons", async () => {
    const { default: Page } = await import("../(dashboard)/flow-designer/page");
    render(<Page />);
    expect(screen.getByText("Tüm Kategoriler")).toBeInTheDocument();
  });

  it("shows built-in template names", async () => {
    const { default: Page } = await import("../(dashboard)/flow-designer/page");
    render(<Page />);
    expect(screen.getByText("Senaryo Üreticisi")).toBeInTheDocument();
  });
});
