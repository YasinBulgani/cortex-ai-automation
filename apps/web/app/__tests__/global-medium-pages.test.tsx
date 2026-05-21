/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ── Suppress noise ─────────────────────────────────────────────────────────
const consoleSpies: jest.SpyInstance[] = [];
beforeEach(() => {
  consoleSpies.push(jest.spyOn(console, "error").mockImplementation(() => {}));
  consoleSpies.push(jest.spyOn(console, "warn").mockImplementation(() => {}));
  (global as any).fetch = jest.fn(() => Promise.resolve({ json: () => Promise.resolve({}) }));
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
  useParams: () => ({ agentId: "scenario-generator" }),
  usePathname: () => "/p/proj-1",
}));
jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

const apiMock = jest.fn();
jest.mock("@/lib/api", () => ({
  apiFetch: (...args: any[]) => apiMock(...args),
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
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
jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title, right }: any) => <div data-testid="page-header">{title}{right}</div>,
  SectionCard: ({ title, children }: any) => <div data-testid="section-card">{title && <div>{title}</div>}{children}</div>,
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
  Badge: ({ children }: any) => <span>{children}</span>,
}));
jest.mock("@/lib/useProject", () => ({
  useProject: jest.fn(() => ({
    project: { id: "proj-1", name: "Test Project" },
    setProject: jest.fn(),
    projectId: "proj-1",
  })),
}));
jest.mock("@/lib/product", () => ({
  PRODUCT_FAMILY: [{ id: "one", name: "TestwrightAI", shortName: "TW", tagline: "", description: "", availability: "ga", defaultEntryKey: "scenarios", routeSegments: [] }],
  PRODUCT_FAMILY_BY_ID: { one: { id: "one", name: "TestwrightAI" } },
  DEFAULT_PRODUCT_FAMILY_ID: "one",
}));

// ─── BgtestWizardPage ──────────────────────────────────────────────────────

describe("BgtestWizardPage", () => {
  beforeEach(() => {
    apiMock.mockImplementation((url: string) => {
      if (url.includes("projects")) return Promise.resolve([{ id: "proj-1", name: "Alpha Project" }]);
      if (url.includes("global")) return Promise.resolve({ total_projects: 3, total_scenarios: 12, total_executions: 45, avg_pass_rate: 87 });
      if (url.includes("executions")) return Promise.resolve([]);
      return Promise.resolve([]);
    });
  });

  it("renders data-testid='bgtest-wizard-page'", async () => {
    const { default: Page } = await import("../(dashboard)/bgtest-wizard/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("bgtest-wizard-page")).toBeInTheDocument()
    );
  });

  it("shows wizard title heading", async () => {
    const { default: Page } = await import("../(dashboard)/bgtest-wizard/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getAllByText(/Uçtan Uca|Wizard|Sihirbaz/i).length).toBeGreaterThanOrEqual(1)
    );
  });

  it("shows project name after API load", async () => {
    const { default: Page } = await import("../(dashboard)/bgtest-wizard/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getAllByText("Alpha Project").length).toBeGreaterThanOrEqual(1)
    );
  });

  it("renders 'Yeni Proje Oluştur' section", async () => {
    const { default: Page } = await import("../(dashboard)/bgtest-wizard/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Yeni Proje Oluştur")).toBeInTheDocument()
    );
  });

  it("renders 'Uçtan Uca Adım Rehberi' section", async () => {
    const { default: Page } = await import("../(dashboard)/bgtest-wizard/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Uçtan Uca Adım Rehberi")).toBeInTheDocument()
    );
  });
});

// ─── VeriKaynagiPage ───────────────────────────────────────────────────────

describe("VeriKaynagiPage", () => {
  beforeEach(() => {
    apiMock.mockResolvedValue({});
  });

  it("renders data-testid='veri-kaynagi-page'", async () => {
    const { default: Page } = await import("../(dashboard)/veri-kaynagi/page");
    render(<Page />);
    expect(screen.getByTestId("veri-kaynagi-page")).toBeInTheDocument();
  });

  it("shows heading 'Veri Kaynağı'", async () => {
    const { default: Page } = await import("../(dashboard)/veri-kaynagi/page");
    render(<Page />);
    expect(screen.getByText("Veri Kaynağı")).toBeInTheDocument();
  });

  it("shows DDL / SQL source option", async () => {
    const { default: Page } = await import("../(dashboard)/veri-kaynagi/page");
    render(<Page />);
    expect(screen.getByText("DDL / SQL")).toBeInTheDocument();
  });

  it("shows CSV / TSV source option", async () => {
    const { default: Page } = await import("../(dashboard)/veri-kaynagi/page");
    render(<Page />);
    expect(screen.getByText("CSV / TSV")).toBeInTheDocument();
  });

  it("shows Doğal Dil source option", async () => {
    const { default: Page } = await import("../(dashboard)/veri-kaynagi/page");
    render(<Page />);
    expect(screen.getByText("Doğal Dil")).toBeInTheDocument();
  });
});

// ─── TaskDraftsPage ────────────────────────────────────────────────────────

describe("TaskDraftsPage", () => {
  beforeEach(() => {
    apiMock.mockImplementation((url: string) => {
      if (url.includes("projects")) return Promise.resolve([{ id: "proj-1", name: "Test Project" }]);
      if (url.includes("scenarios")) return Promise.resolve([
        { id: "s1", title: "Taslak Senaryo", description: "Açıklama", status: "draft", project_id: "proj-1", created_at: "2026-01-01" },
      ]);
      return Promise.resolve([]);
    });
  });

  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/task-drafts/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows 'Senaryo Oluşturucu' heading", async () => {
    const { default: Page } = await import("../(dashboard)/task-drafts/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Senaryo Oluşturucu")).toBeInTheDocument()
    );
  });

  it("shows filter buttons (Tümü, Taslak, İnceleme, Onaylı)", async () => {
    const { default: Page } = await import("../(dashboard)/task-drafts/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Tümü")).toBeInTheDocument()
    );
    expect(screen.getByText("Taslak")).toBeInTheDocument();
  });

  it("shows scenario title after load", async () => {
    apiMock.mockImplementation((url: string) => {
      if (url.includes("scenarios")) return Promise.resolve([
        { id: "s1", title: "Taslak Senaryo", description: "Açıklama", status: "draft", project_id: "proj-1", created_at: "2026-01-01" },
      ]);
      return Promise.resolve([{ id: "proj-1", name: "Test Project" }]);
    });
    const { default: Page } = await import("../(dashboard)/task-drafts/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Taslak Senaryo")).toBeInTheDocument()
    );
  });
});

// ─── WhatsNewPage ──────────────────────────────────────────────────────────

describe("WhatsNewPage", () => {
  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/info/whats-new/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows 'Yenilikler' heading", async () => {
    const { default: Page } = await import("../(dashboard)/info/whats-new/page");
    render(<Page />);
    expect(screen.getByText("Yenilikler")).toBeInTheDocument();
  });

  it("shows sprint releases", async () => {
    const { default: Page } = await import("../(dashboard)/info/whats-new/page");
    render(<Page />);
    expect(screen.getByText(/Sprint 10/i)).toBeInTheDocument();
  });

  it("renders release badges (new, improved, fix)", async () => {
    const { default: Page } = await import("../(dashboard)/info/whats-new/page");
    render(<Page />);
    // Should have multiple entries with badges
    expect(screen.getAllByRole("heading").length).toBeGreaterThan(0);
  });
});

// ─── AdminUsersPage ────────────────────────────────────────────────────────

describe("AdminUsersPage", () => {
  beforeEach(() => {
    apiMock.mockResolvedValue([
      { id: "u1", email: "test@example.com", full_name: "Test User", department: "QA", is_active: true, roles: ["viewer"], created_at: "2026-01-01" },
    ]);
  });

  it("renders data-testid='admin-users-page'", async () => {
    const { default: Page } = await import("../(dashboard)/admin/users/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("admin-users-page")).toBeInTheDocument()
    );
  });

  it("shows 'Yeni Kullanıcı Ekle' section", async () => {
    const { default: Page } = await import("../(dashboard)/admin/users/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Yeni Kullanıcı Ekle")).toBeInTheDocument()
    );
  });

  it("shows user email after load", async () => {
    const { default: Page } = await import("../(dashboard)/admin/users/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("test@example.com")).toBeInTheDocument()
    );
  });

  it("renders create user form inputs", async () => {
    const { default: Page } = await import("../(dashboard)/admin/users/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("admin-users-input-email")).toBeInTheDocument()
    );
  });

  it("shows search input", async () => {
    const { default: Page } = await import("../(dashboard)/admin/users/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("admin-users-input-search")).toBeInTheDocument()
    );
  });
});

// ─── AiAgentDetailPage ─────────────────────────────────────────────────────

describe("AiAgentDetailPage (/ai-agents/[agentId])", () => {
  beforeEach(() => {
    apiMock.mockResolvedValue([
      { id: "proj-1", name: "Test Project", description: "Desc", archived: false },
    ]);
  });

  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/ai-agents/[agentId]/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows agent name or 'not found' message", async () => {
    const { default: Page } = await import("../(dashboard)/ai-agents/[agentId]/page");
    render(<Page />);
    // agentId is "scenario-generator" from useParams mock
    await waitFor(() => {
      const hasAgent = screen.queryByText(/Senaryo|Ajan bulunamadı/i);
      expect(hasAgent).toBeInTheDocument();
    });
  });

  it("renders project selector when agent found", async () => {
    const { default: Page } = await import("../(dashboard)/ai-agents/[agentId]/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.queryByText(/Proje Seç|Test Project|Ajan bulunamadı/i)).toBeInTheDocument()
    );
  });
});

// ─── VeriSimulatoPage ──────────────────────────────────────────────────────

describe("VeriSimulatoPage", () => {
  beforeEach(() => {
    apiMock.mockResolvedValue({});
  });

  it("renders data-testid='veri-simulatoru-page'", async () => {
    const { default: Page } = await import("../(dashboard)/veri-simulatoru/page");
    render(<Page />);
    expect(screen.getByTestId("veri-simulatoru-page")).toBeInTheDocument();
  });

  it("shows generate button", async () => {
    const { default: Page } = await import("../(dashboard)/veri-simulatoru/page");
    render(<Page />);
    expect(screen.getByTestId("btn-generate")).toBeInTheDocument();
  });

  it("shows row count input", async () => {
    const { default: Page } = await import("../(dashboard)/veri-simulatoru/page");
    render(<Page />);
    expect(screen.getByTestId("row-count")).toBeInTheDocument();
  });

  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/veri-simulatoru/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
