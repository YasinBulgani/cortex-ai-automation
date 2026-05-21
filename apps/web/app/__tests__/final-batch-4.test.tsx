/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ── Suppress noise ─────────────────────────────────────────────────────────
const consoleSpies: jest.SpyInstance[] = [];
beforeEach(() => {
  consoleSpies.push(jest.spyOn(console, "error").mockImplementation(() => {}));
  consoleSpies.push(jest.spyOn(console, "warn").mockImplementation(() => {}));
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
  // Default: fetch returns empty runs list (ok)
  (global as any).fetch = jest.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve({ runs: [] }) })
  );
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
  redirect: jest.fn(),
  usePathname: () => "/p/proj-1",
}));

// next/dynamic — return the loading placeholder in jsdom
jest.mock("next/dynamic", () => ({
  __esModule: true,
  default: (_fn: any, opts?: any) => {
    if (opts?.loading) return opts.loading;
    return () => <div data-testid="dynamic-placeholder" />;
  },
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
jest.mock("@/components/ui/tabs", () => ({
  Tabs: ({ children }: any) => <div data-testid="tabs">{children}</div>,
  TabsList: ({ children }: any) => <div data-testid="tabs-list">{children}</div>,
  TabsTrigger: ({ children, value }: any) => (
    <button data-testid={`tab-${value}`}>{children}</button>
  ),
}));

jest.mock("@/lib/provenance", () => ({
  isRealProvenance: jest.fn(() => false),
  normalizeProvenance: jest.fn(() => "stub"),
  provenanceBadgeClass: jest.fn(() => "badge-stub"),
  provenanceLabel: jest.fn(() => "Stub"),
}));

// ── FlowDetailPage ─────────────────────────────────────────────────────────

describe("FlowDetailPage", () => {
  it("renders without crashing", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/flows/[flowId]/page"
    );
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows flow-editor-loading placeholder (next/dynamic ssr:false)", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/flows/[flowId]/page"
    );
    render(<Page />);
    expect(screen.getByTestId("flow-editor-loading")).toBeInTheDocument();
  });

  it("shows 'Akış düzenleyici yükleniyor...' text", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/flows/[flowId]/page"
    );
    render(<Page />);
    expect(screen.getByText("Akış düzenleyici yükleniyor...")).toBeInTheDocument();
  });
});

// ── RunsPage ───────────────────────────────────────────────────────────────

describe("RunsPage", () => {
  it("renders data-testid='runs-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/runs/page"
    );
    render(<Page />);
    expect(screen.getByTestId("runs-page")).toBeInTheDocument();
  });

  it("shows 'Test Koşuları' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/runs/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Test Koşuları/i);
  });

  it("shows 'Yeni Koşu Başlat' section", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/runs/page"
    );
    render(<Page />);
    expect(screen.getByText("Yeni Koşu Başlat")).toBeInTheDocument();
  });

  it("shows 'Koşu Başlat' button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/runs/page"
    );
    render(<Page />);
    expect(screen.getByText("Koşu Başlat")).toBeInTheDocument();
  });

  it("shows empty state after load with no runs", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/runs/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("empty-state")).toBeInTheDocument()
    );
    expect(screen.getByTestId("empty-state")).toHaveTextContent(/Henüz koşu yok|koşu bulunamadı/i);
  });

  it("shows engine connection error when fetch fails", async () => {
    (global as any).fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        status: 503,
        json: () => Promise.resolve({}),
      })
    );
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/runs/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("empty-state")).toBeInTheDocument()
    );
    expect(screen.getByTestId("empty-state")).toHaveTextContent(/Engine|bağlantı/i);
  });

  it("shows stat cards (Toplam Koşu)", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/runs/page"
    );
    render(<Page />);
    expect(screen.getByTestId("stat-Toplam Koşu")).toBeInTheDocument();
  });

  it("shows 'Execution Koşusu' link", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/runs/page"
    );
    render(<Page />);
    expect(screen.getByText(/Execution Koşusu/i)).toBeInTheDocument();
  });
});

// ── ScenarioDetailPage ─────────────────────────────────────────────────────

describe("ScenarioDetailPage (/scenarios/[id])", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue({
      id: "s-1",
      title: "Login Senaryosu",
      description: "Kullanıcı giriş akışı",
      status: "active",
      current_version: 3,
      steps: [{ order: 0, text: "URL aç" }],
    });
  });

  it("shows loading state initially", async () => {
    // Block resolution so we can see loading
    apiFetchMock.mockReturnValue(new Promise(() => {}));
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/[id]/page"
    );
    render(<Page />);
    expect(screen.getByText(/Yükleniyor/i)).toBeInTheDocument();
  });

  it("renders data-testid='scenario-detail-page' after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/[id]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("scenario-detail-page")).toBeInTheDocument()
    );
  });

  it("shows scenario title after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/[id]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("scenario-detail-heading")).toHaveTextContent("Login Senaryosu")
    );
  });

  it("shows 'Düzenle' button after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/[id]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("scenario-detail-btn-edit")).toBeInTheDocument()
    );
  });

  it("shows 'Listeye dön' button after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/[id]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("scenario-detail-btn-back")).toBeInTheDocument()
    );
  });

  it("shows step content after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/[id]/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText(/URL aç/i)).toBeInTheDocument()
    );
  });
});

// ── ScenarioGeneratePage ───────────────────────────────────────────────────

describe("ScenarioGeneratePage (/scenarios/generate)", () => {
  it("renders data-testid='scenario-generate-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/generate/page"
    );
    render(<Page />);
    expect(screen.getByTestId("scenario-generate-page")).toBeInTheDocument();
  });

  it("shows 'BDD Senaryosu Üret' heading", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/generate/page"
    );
    render(<Page />);
    expect(screen.getByText("BDD Senaryosu Üret")).toBeInTheDocument();
  });

  it("shows analysis textarea", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/generate/page"
    );
    render(<Page />);
    expect(screen.getByTestId("analysis-text")).toBeInTheDocument();
  });

  it("shows 'Senaryoları Üret' submit button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/generate/page"
    );
    render(<Page />);
    expect(screen.getByTestId("generate-btn-submit")).toBeInTheDocument();
  });

  it("shows 'Geri dön' button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/generate/page"
    );
    render(<Page />);
    expect(screen.getByTestId("generate-btn-back")).toBeInTheDocument();
  });

  it("shows 'Analiz Dokümanı' label", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/generate/page"
    );
    render(<Page />);
    expect(screen.getByText("Analiz Dokümanı *")).toBeInTheDocument();
  });
});

// ── NewScenarioPage ────────────────────────────────────────────────────────

describe("NewScenarioPage (/scenarios/new)", () => {
  it("renders data-testid='new-scenario-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/new/page"
    );
    render(<Page />);
    expect(screen.getByTestId("new-scenario-page")).toBeInTheDocument();
  });

  it("shows 'Yeni senaryo' heading", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/new/page"
    );
    render(<Page />);
    expect(screen.getByTestId("new-scenario-heading")).toHaveTextContent("Yeni senaryo");
  });

  it("renders the scenario form", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/new/page"
    );
    render(<Page />);
    expect(screen.getByTestId("scenario-form")).toBeInTheDocument();
  });

  it("shows title input field", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/new/page"
    );
    render(<Page />);
    expect(screen.getByTestId("scenario-title")).toBeInTheDocument();
  });

  it("shows 'Kaydet' save button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/new/page"
    );
    render(<Page />);
    expect(screen.getByTestId("scenario-save-btn")).toBeInTheDocument();
  });

  it("shows 'Başlık' label", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/new/page"
    );
    render(<Page />);
    // "Başlık" appears both in the form label and the preview placeholder
    expect(screen.getAllByText("Başlık").length).toBeGreaterThanOrEqual(1);
  });

  it("shows preview panel", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/scenarios/new/page"
    );
    render(<Page />);
    expect(screen.getByText("Önizleme")).toBeInTheDocument();
  });
});

// ── ProjectRootPage (welcome dashboard) ────────────────────────────────────

describe("ProjectRootPage (/p/[projectId])", () => {
  it("renders welcome dashboard with quick starts", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/page"
    );
    render(<Page />);
    expect(screen.getByTestId("project-welcome-page")).toBeInTheDocument();
    expect(screen.getByTestId("welcome-quick-starts")).toBeInTheDocument();
  });

  it("renders learning checklist", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/page"
    );
    render(<Page />);
    expect(screen.getByTestId("learning-checklist-card")).toBeInTheDocument();
  });

  it("renders KB + workflows gallery links", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/page"
    );
    render(<Page />);
    expect(screen.getByTestId("welcome-kb")).toBeInTheDocument();
    expect(screen.getByTestId("welcome-workflows-gallery")).toBeInTheDocument();
  });
});
