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
  (global as any).fetch = jest.fn(() =>
    Promise.resolve({ json: () => Promise.resolve({}) })
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
  useParams: () => ({}),
  usePathname: () => "/p/proj-1",
}));
jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

const apiFetchMock = jest.fn();
jest.mock("@/lib/api", () => ({
  apiFetch: (...args: any[]) => apiFetchMock(...args),
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

// Nexus components
jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, badge }: any) => (
    <div data-testid="page-header">{title}{badge}</div>
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
jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title, badge }: any) => (
    <div data-testid="page-header">{title}{badge}</div>
  ),
  SectionCard: ({ title, children, right }: any) => (
    <div data-testid="section-card">
      {title && <div>{title}</div>}
      {right && <div>{right}</div>}
      {children}
    </div>
  ),
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
  Badge: ({ children }: any) => <span className="badge">{children}</span>,
}));
jest.mock("@/components/ui/toast", () => ({
  useToast: jest.fn(() => ({ toast: jest.fn() })),
  ToastProvider: ({ children }: any) => <div>{children}</div>,
}));

// @tanstack/react-query mock — PlaywrightConsolePage and similar now use it
jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn(() => ({ data: null, isLoading: false, error: null })),
  useMutation: jest.fn(() => ({
    mutate: jest.fn(),
    mutateAsync: jest.fn(() => Promise.resolve(null)),
    isPending: false,
    data: null,
    error: null,
  })),
  useQueryClient: jest.fn(() => ({
    invalidateQueries: jest.fn(),
    setQueryData: jest.fn(),
    getQueryData: jest.fn(),
  })),
  QueryClient: jest.fn().mockImplementation(() => ({})),
  QueryClientProvider: ({ children }: any) => <>{children}</>,
}));

// ── PlaywrightMcp hook mock ────────────────────────────────────────────────
jest.mock("@/lib/hooks/use-playwright-mcp", () => ({
  usePlaywrightHealth: jest.fn(),
  useCreateSession: jest.fn(),
  useCloseSession: jest.fn(),
  useNavigate: jest.fn(),
  useScreenshot: jest.fn(),
  useValidateSelectors: jest.fn(),
  useDOMSnapshot: jest.fn(),
  useVerifyHeal: jest.fn(),
  useRunHealPipeline: jest.fn(),
  useHealHistory: jest.fn(),
  useHealStats: jest.fn(),
  usePlaywrightSessions: jest.fn(),
  useSuggestSelectors: jest.fn(),
  useBrowserAction: jest.fn(),
}));

// ── DocumentUploader mock ─────────────────────────────────────────────────
jest.mock("@/components/DocumentUploader", () => ({
  DocumentUploader: ({ onDocumentParsed }: any) => (
    <div data-testid="document-uploader">
      <button onClick={() => onDocumentParsed?.({ name: "test.pdf", content: "content" })}>
        Upload
      </button>
    </div>
  ),
}));

// ── New-project local component mocks ─────────────────────────────────────
jest.mock("../(dashboard)/new-project/MaviyakaFeatureViewer", () => ({
  MaviyakaFeatureViewer: ({ features }: any) => (
    <div data-testid="maviyaka-feature-viewer">{(features || []).length} features</div>
  ),
}));
jest.mock("../(dashboard)/new-project/IdeWorkbench", () => ({
  IdeWorkbench: () => <div data-testid="ide-workbench">IDE Workbench</div>,
}));

// ── Product mock (must have availability: "active" for new-project page) ──
jest.mock("@/lib/product", () => ({
  PRODUCT_FAMILY: [
    {
      id: "one",
      name: "TestwrightAI",
      shortName: "TW",
      tagline: "Test otomasyon platformu",
      description: "AI destekli test platformu",
      availability: "active",
      defaultEntryKey: "scenarios",
      routeSegments: ["scenarios"],
    },
  ],
  PRODUCT_FAMILY_BY_ID: { one: { id: "one", name: "TestwrightAI" } },
  DEFAULT_PRODUCT_FAMILY_ID: "one",
  PRODUCT_FAMILY_STORAGE_KEY: "bgts_product_family_focus",
  getProductFamilyMember: jest.fn(() => ({
    id: "one",
    name: "TestwrightAI",
    shortName: "TW",
    tagline: "Test otomasyon platformu",
    description: "AI destekli test platformu",
    availability: "active",
    defaultEntryKey: "scenarios",
    routeSegments: ["scenarios"],
  })),
}));

// ─── PlaywrightConsolePage ─────────────────────────────────────────────────

describe("PlaywrightConsolePage", () => {
  beforeEach(() => {
    const m = require("@/lib/hooks/use-playwright-mcp");
    (m.usePlaywrightHealth as jest.Mock).mockReturnValue({
      data: { status: "ok" },
      isLoading: false,
    });
    (m.useCreateSession as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false });
    (m.useCloseSession as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false });
    (m.useNavigate as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false });
    (m.useScreenshot as jest.Mock).mockReturnValue({
      data: null,
      isLoading: false,
      refetch: jest.fn(),
    });
    (m.useValidateSelectors as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false, data: null });
    (m.useDOMSnapshot as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false, data: null });
    (m.useVerifyHeal as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false, data: null });
    (m.useRunHealPipeline as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false });
    (m.useHealHistory as jest.Mock).mockReturnValue({ data: [] });
    (m.useHealStats as jest.Mock).mockReturnValue({ data: null });
    (m.usePlaywrightSessions as jest.Mock).mockReturnValue({ data: [] });
    (m.useSuggestSelectors as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false, data: null });
    (m.useBrowserAction as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false });
  });

  it("renders data-testid='playwright-console-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/playwright-console/page"
    );
    render(<Page />);
    expect(screen.getByTestId("playwright-console-page")).toBeInTheDocument();
  });

  it("shows 'Playwright Konsol' title", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/playwright-console/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Playwright Konsol");
  });

  it("page mounts and exposes data-testid='playwright-console-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/playwright-console/page"
    );
    render(<Page />);
    expect(screen.getByTestId("playwright-console-page")).toBeInTheDocument();
  });

  it("does not render legacy copy-output-btn (refactored)", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/playwright-console/page"
    );
    render(<Page />);
    expect(screen.queryByTestId("copy-output-btn")).not.toBeInTheDocument();
  });

  it("shows AKTIF badge when playwright is available", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/playwright-console/page"
    );
    render(<Page />);
    expect(screen.getByText("AKTIF")).toBeInTheDocument();
  });
});

// ─── MobilOtomasyonPage ────────────────────────────────────────────────────

describe("MobilOtomasyonPage", () => {
  beforeEach(() => {
    // API fails → page falls back to mock mode, which is fine for render tests
    apiFetchMock.mockRejectedValue(new Error("Network error"));
  });

  it("renders data-testid='mobil-otomasyon-page'", async () => {
    const { default: Page } = await import("../(dashboard)/mobil-otomasyon/page");
    render(<Page />);
    expect(screen.getByTestId("mobil-otomasyon-page")).toBeInTheDocument();
  });

  it("shows 'Mobil Otomasyon' heading", async () => {
    const { default: Page } = await import("../(dashboard)/mobil-otomasyon/page");
    render(<Page />);
    expect(screen.getByText(/Mobil Otomasyon/i)).toBeInTheDocument();
  });

  it("shows DEV / DEMO Modu warning", async () => {
    const { default: Page } = await import("../(dashboard)/mobil-otomasyon/page");
    render(<Page />);
    expect(screen.getByText("DEV / DEMO Modu")).toBeInTheDocument();
  });

  it("renders 'Araştırma Raporu' button", async () => {
    const { default: Page } = await import("../(dashboard)/mobil-otomasyon/page");
    render(<Page />);
    expect(screen.getByText("📄 Araştırma Raporu")).toBeInTheDocument();
  });

  it("renders 'Fiziksel Cihaz Kaydet' button", async () => {
    const { default: Page } = await import("../(dashboard)/mobil-otomasyon/page");
    render(<Page />);
    expect(screen.getByText("➕ Fiziksel Cihaz Kaydet")).toBeInTheDocument();
  });
});

// ─── ScenarioIdePage ───────────────────────────────────────────────────────

describe("ScenarioIdePage (ide)", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='scenario-ide-page'", async () => {
    const { default: Page } = await import("../(dashboard)/ide/page");
    render(<Page />);
    expect(screen.getByTestId("scenario-ide-page")).toBeInTheDocument();
  });

  it("shows 'Neurex IDE' title bar", async () => {
    const { default: Page } = await import("../(dashboard)/ide/page");
    render(<Page />);
    expect(screen.getByText("Neurex IDE")).toBeInTheDocument();
  });

  it("shows scenario-ide-explorer sidebar", async () => {
    const { default: Page } = await import("../(dashboard)/ide/page");
    render(<Page />);
    expect(screen.getByTestId("scenario-ide-explorer")).toBeInTheDocument();
  });

  it("shows search input", async () => {
    const { default: Page } = await import("../(dashboard)/ide/page");
    render(<Page />);
    expect(screen.getByTestId("scenario-ide-search")).toBeInTheDocument();
  });

  it("shows 'Senaryo Çalışma Alanı' placeholder when no tab open", async () => {
    const { default: Page } = await import("../(dashboard)/ide/page");
    render(<Page />);
    expect(screen.getByText("Senaryo Çalışma Alanı")).toBeInTheDocument();
  });
});

// ─── NewProjectPage ────────────────────────────────────────────────────────

describe("NewProjectPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/new-project/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows 'new-project-back' button", async () => {
    const { default: Page } = await import("../(dashboard)/new-project/page");
    render(<Page />);
    expect(screen.getByTestId("new-project-back")).toBeInTheDocument();
  });

  it("shows 'Yeni Proje' breadcrumb text", async () => {
    const { default: Page } = await import("../(dashboard)/new-project/page");
    render(<Page />);
    expect(screen.getByText("Yeni Proje")).toBeInTheDocument();
  });

  it("shows 'Ana Sayfa' back link text", async () => {
    const { default: Page } = await import("../(dashboard)/new-project/page");
    render(<Page />);
    expect(screen.getByText("Ana Sayfa")).toBeInTheDocument();
  });

  it("shows step progress indicator", async () => {
    const { default: Page } = await import("../(dashboard)/new-project/page");
    render(<Page />);
    expect(screen.getAllByText(/Adım/).length).toBeGreaterThanOrEqual(1);
  });

  it("shows TestwrightAI product name", async () => {
    const { default: Page } = await import("../(dashboard)/new-project/page");
    render(<Page />);
    expect(screen.getAllByText("TestwrightAI").length).toBeGreaterThanOrEqual(1);
  });
});
