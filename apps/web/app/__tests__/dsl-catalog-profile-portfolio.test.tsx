/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// ── Suppress noise ────────────────────────────────────────────────────────────
const consoleSpies: jest.SpyInstance[] = [];
beforeEach(() => {
  consoleSpies.push(jest.spyOn(console, "error").mockImplementation(() => {}));
  consoleSpies.push(jest.spyOn(console, "warn").mockImplementation(() => {}));
});
afterEach(() => {
  consoleSpies.forEach((s) => s.mockRestore());
  consoleSpies.length = 0;
  jest.clearAllMocks();
});

// ── Mocks ─────────────────────────────────────────────────────────────────────
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

// api mock — two separate mocks needed (some pages use @/lib/api, some @/lib/api-client)
const apiMock = jest.fn();
jest.mock("@/lib/api", () => ({ apiFetch: (...args: any[]) => apiMock(...args) }));
const apiClientMock = jest.fn();
jest.mock("@/lib/api-client", () => ({
  apiFetch: (...args: any[]) => apiClientMock(...args),
  engineFetch: jest.fn(),
}));

jest.mock("@/lib/dsl-api", () => ({
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
  dslApi: {
    stats: jest.fn(),
    categories: jest.fn(),
    listActions: jest.fn(),
    search: jest.fn(),
    reload: jest.fn(),
  },
}));

jest.mock("@/lib/product", () => ({
  PRODUCT_FAMILY: [{ id: "one", name: "TestwrightAI", shortName: "TW", tagline: "", description: "", availability: "ga", defaultEntryKey: "scenarios", routeSegments: [] }],
  PRODUCT_FAMILY_BY_ID: { one: { id: "one", name: "TestwrightAI" } },
  DEFAULT_PRODUCT_FAMILY_ID: "one",
}));

jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, right }: any) => <div data-testid="page-header">{title}{right}</div>,
}));
jest.mock("@/components/nexus/SectionCard", () => ({
  SectionCard: ({ title, children }: any) => (
    <div data-testid="section-card">{title && <div>{title}</div>}{children}</div>
  ),
}));
jest.mock("@/components/nexus/StatCard", () => ({
  StatCard: ({ label, value }: any) => <div data-testid={`stat-${label}`}>{String(value)}</div>,
}));
jest.mock("@/components/nexus/MetricRow", () => ({
  MetricRow: ({ children }: any) => <div>{children}</div>,
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
  Badge: ({ children }: any) => <span className="badge">{children}</span>,
}));
jest.mock("@/components/ui/virtual-list", () => ({
  VirtualList: ({ items, renderItem }: any) => (
    <div data-testid="virtual-list">
      {(items || []).map((item: any, i: number) => <div key={i}>{renderItem(item, i)}</div>)}
    </div>
  ),
}));

// ─── DslCatalogPage ───────────────────────────────────────────────────────────

describe("DslCatalogPage (p/[projectId]/dsl-catalog)", () => {
  beforeEach(() => {
    const { dslApi } = require("@/lib/dsl-api");
    dslApi.stats.mockResolvedValue({
      total: 42,
      aliases: { tr: 20, en: 15, both: 7 },
      by_implementation: { python: 30 },
      loaded_at: "2026-01-01T00:00:00Z",
    });
    dslApi.categories.mockResolvedValue([
      { id: "web", label: "Web Eylemleri", count: 25, children: [] },
      { id: "mobile", label: "Mobil", count: 10, children: [] },
    ]);
    dslApi.listActions.mockResolvedValue({
      items: [
        {
          id: "click-element",
          description: "Elemana tıkla",
          category: "web",
          aliases: { tr: ["tıkla"], en: ["click"] },
          tags: ["click"],
          implementations: {},
        },
      ],
      total: 1,
    });
  });

  it("renders the page heading 'DSL Katalogu'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/dsl-catalog/page"
    );
    render(<Page />);
    await waitFor(() => expect(screen.getByText("DSL Katalogu")).toBeInTheDocument());
  });

  it("shows total stat (42) after loading", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/dsl-catalog/page"
    );
    render(<Page />);
    await waitFor(() => expect(screen.getByText("42")).toBeInTheDocument());
  });

  it("renders category tree items after load", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/dsl-catalog/page"
    );
    render(<Page />);
    await waitFor(() => expect(screen.getByText("Web Eylemleri")).toBeInTheDocument());
    expect(screen.getByText("Mobil")).toBeInTheDocument();
  });

  it("renders an action row with its ID", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/dsl-catalog/page"
    );
    render(<Page />);
    await waitFor(() => expect(screen.getByText("click-element")).toBeInTheDocument());
  });

  it("renders 'Tümü' category row", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/dsl-catalog/page"
    );
    render(<Page />);
    await waitFor(() => expect(screen.getByText("Tümü")).toBeInTheDocument());
  });

  it("renders search input with placeholder text", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/dsl-catalog/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByPlaceholderText(/cümlecik ara/i)).toBeInTheDocument()
    );
  });

  it("shows action detail placeholder when nothing selected", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/dsl-catalog/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText(/Bir cümlecik seçin/i)).toBeInTheDocument()
    );
  });

  it("renders 'Yeniden Yükle' button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/dsl-catalog/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Yeniden Yükle")).toBeInTheDocument()
    );
  });
});

// ─── ProfilePage ──────────────────────────────────────────────────────────────

describe("ProfilePage", () => {
  const profileData = {
    email: "yasin@testwright.ai",
    full_name: "Yasin Bulgan",
    phone: "",
    department: "",
    roles: ["admin"],
  };
  const notifData = {
    notify_on_complete: true,
    notify_on_failure: false,
    slack_webhook_url: null,
  };

  beforeEach(() => {
    apiMock.mockImplementation((url: string) => {
      if (url.includes("profile")) return Promise.resolve(profileData);
      if (url.includes("prefs")) return Promise.resolve(notifData);
      return Promise.resolve({});
    });
  });

  it("renders data-testid='profile-page'", async () => {
    const { default: Page } = await import("../(dashboard)/profile/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("profile-page")).toBeInTheDocument()
    );
  });

  it("renders user email in disabled input", async () => {
    const { default: Page } = await import("../(dashboard)/profile/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("profile-input-email")).toBeInTheDocument()
    );
    expect(screen.getByTestId("profile-input-email")).toHaveValue("yasin@testwright.ai");
  });

  it("renders user full name in heading", async () => {
    const { default: Page } = await import("../(dashboard)/profile/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Yasin Bulgan")).toBeInTheDocument()
    );
  });

  it("renders 'Şifre Değiştir' button", async () => {
    const { default: Page } = await import("../(dashboard)/profile/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("profile-btn-password")).toBeInTheDocument()
    );
  });

  it("renders profile name input", async () => {
    const { default: Page } = await import("../(dashboard)/profile/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("profile-input-name")).toBeInTheDocument()
    );
  });
});

// ─── PortfolioPage ────────────────────────────────────────────────────────────

describe("PortfolioPage", () => {
  const projects = [
    { id: "proj-1", name: "Alpha Project", description: "Test project", archived: false, pass_rate: 85 },
    { id: "proj-2", name: "Beta Suite", description: "Another project", archived: false, pass_rate: 60 },
  ];

  beforeEach(() => {
    apiMock.mockResolvedValue(projects);
  });

  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/portfolio/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows project cards after API resolves", async () => {
    const { default: Page } = await import("../(dashboard)/portfolio/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("project-card-proj-1")).toBeInTheDocument()
    );
  });

  it("shows project names in cards", async () => {
    const { default: Page } = await import("../(dashboard)/portfolio/page");
    render(<Page />);
    await waitFor(() => {
      expect(screen.getByText("Alpha Project")).toBeInTheDocument();
      expect(screen.getByText("Beta Suite")).toBeInTheDocument();
    });
  });

  it("project card links to /p/{id}/scenarios", async () => {
    const { default: Page } = await import("../(dashboard)/portfolio/page");
    render(<Page />);
    await waitFor(() => {
      const card = screen.getByTestId("project-card-proj-1");
      expect(card.closest("a")).toHaveAttribute("href", "/p/proj-1/scenarios");
    });
  });

  it("shows empty text when no projects", async () => {
    apiMock.mockResolvedValueOnce([]);
    const { default: Page } = await import("../(dashboard)/portfolio/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText(/Henüz proje yok\./i)).toBeInTheDocument()
    );
  });
});

// ─── AiQualityPage ────────────────────────────────────────────────────────────

describe("AiQualityPage", () => {
  const mockPayload = {
    period_days: 7,
    overview: {
      total_calls: 1200,
      success_rate: 0.94,
      json_parse_rate: 0.97,
      avg_latency_ms: 320,
      total_cost_usd: 5.42,
    },
    by_model: [
      {
        model: "claude-3-haiku",
        calls: 800,
        success_rate: 0.95,
        json_parse_rate: 0.98,
        avg_latency_ms: 250,
        p95_latency_ms: 800,
        total_cost_usd: 2.1,
      },
    ],
    regression_alerts: [],
    recommendations: ["Increase cache TTL for frequent queries"],
    judge: { total: 50, avg_overall: 4.2, avg_correctness: 4.1, avg_completeness: 4.0, avg_domain_fit: 3.9, avg_format_validity: 4.3 },
    routing: { routing_mode: "smart", tiers: {}, provider_availability: {} },
    ingestion: { total: 100, sources: [] },
    eval_latest: { suite: null, total: 0, pass_count: 0, pass_rate: 0, results: [] },
  };

  beforeEach(() => {
    apiClientMock.mockResolvedValue(mockPayload);
  });

  it("renders without crashing", async () => {
    const { default: Page } = await import("../(dashboard)/ai-quality/page");
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders PageHeader with AI quality title", async () => {
    const { default: Page } = await import("../(dashboard)/ai-quality/page");
    render(<Page />);
    await waitFor(() => {
      const header = screen.getByTestId("page-header");
      expect(header.textContent).toMatch(/AI|Kalite|LLM/i);
    });
  });

  it("shows total calls value after data loads", async () => {
    const { default: Page } = await import("../(dashboard)/ai-quality/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("1200")).toBeInTheDocument()
    );
  });

  it("shows model table with model name", async () => {
    const { default: Page } = await import("../(dashboard)/ai-quality/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("claude-3-haiku")).toBeInTheDocument()
    );
  });

  it("shows recommendation text", async () => {
    const { default: Page } = await import("../(dashboard)/ai-quality/page");
    render(<Page />);
    await waitFor(() =>
      expect(
        screen.getByText(/Increase cache TTL/i)
      ).toBeInTheDocument()
    );
  });
});
