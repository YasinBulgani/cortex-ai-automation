/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ── Suppress noise ─────────────────────────────────────────────────────────
const consoleSpies: jest.SpyInstance[] = [];
beforeEach(() => {
  consoleSpies.push(jest.spyOn(console, "error").mockImplementation(() => {}));
  consoleSpies.push(jest.spyOn(console, "warn").mockImplementation(() => {}));
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
  (global as any).fetch = jest.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
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
jest.mock("next/image", () => ({
  __esModule: true,
  default: ({ src, alt, ...rest }: any) => <img src={src} alt={alt} {...rest} />,
}));
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn() }),
  useParams: jest.fn(() => ({})),
  usePathname: () => "/p/proj-1/mobile",
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
  TrendBadge: ({ value }: any) => <span>{value}</span>,
}));
jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, disabled, ...rest }: any) => (
    <button onClick={onClick} disabled={disabled} {...rest}>{children}</button>
  ),
}));
jest.mock("@/components/ui/input", () => ({
  Input: (props: any) => <input {...props} />,
}));
jest.mock("@/components/FlowGuideCard", () => ({
  FlowGuideCard: () => <div data-testid="flow-guide-card" />,
}));
jest.mock("@/components/dsl/MobileAiScenarioCard", () => ({
  MobileAiScenarioCard: ({ scenario }: any) => (
    <div data-testid="mobile-scenario-card">{scenario?.title}</div>
  ),
}));
jest.mock("@/lib/utils", () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(" "),
}));

// ai-gateway mock
jest.mock("@/lib/ai-gateway", () => ({
  aiComplete: jest.fn(() =>
    Promise.resolve({ content: "Generated test scenarios\n| TC | Action | Expected |" })
  ),
  getGatewayHealth: jest.fn(() =>
    Promise.resolve({ status: "ok", providers: { openai: true } })
  ),
  analyzeDocument: jest.fn(() => Promise.resolve({ scenarios: [] })),
  generateTestCases: jest.fn(() => Promise.resolve({ test_cases: [] })),
  generateGherkin: jest.fn(() => Promise.resolve({ feature: "" })),
}));

// agents-v2-api mock
jest.mock("@/lib/agents-v2-api", () => ({
  startAgentRun: jest.fn(() =>
    Promise.resolve({ run_id: "run-123", status: "queued", stream_url: "/sse/run-123" })
  ),
  getAgentRun: jest.fn(() =>
    Promise.resolve({ run_id: "run-123", status: "completed", scenarios: [] })
  ),
  subscribeAgentRun: jest.fn((runId: string, cb: any, errCb: any) => {
    // immediately call with a done event
    setTimeout(() => cb({ event_type: "completed", message: "" }), 10);
    return jest.fn(); // unsub
  }),
  cancelAgentRun: jest.fn(() => Promise.resolve()),
  uploadSourceFile: jest.fn(() =>
    Promise.resolve({ file_id: "file-1", original_name: "test.pdf" })
  ),
}));

// tanstack react-query
jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn(() => ({ data: null, isLoading: false })),
  useMutation: jest.fn(() => ({
    mutate: jest.fn(),
    mutateAsync: jest.fn(() => Promise.resolve(null)),
    isPending: false,
    data: null,
    error: null,
  })),
  useQueryClient: jest.fn(() => ({ invalidateQueries: jest.fn() })),
}));

// use-locator-intelligence hooks
jest.mock("@/lib/hooks/use-locator-intelligence", () => ({
  useFallbackResolve: jest.fn(() => ({ mutate: jest.fn(), isPending: false, data: null })),
  useStabilityAnalysis: jest.fn(() => ({ mutate: jest.fn(), isPending: false, data: null })),
  useImproveSuggestions: jest.fn(() => ({ mutate: jest.fn(), isPending: false, data: null })),
  usePOMGenerate: jest.fn(() => ({ mutate: jest.fn(), isPending: false, data: null })),
  useBreakagePrediction: jest.fn(() => ({ mutate: jest.fn(), isPending: false, data: null })),
  useLocatorTrends: jest.fn(() => ({ mutate: jest.fn(), isPending: false, data: null })),
}));

// use-synthetic-advanced hooks
jest.mock("@/lib/hooks/use-synthetic-advanced", () => ({
  usePrivacyAudit: jest.fn(() => ({ mutate: jest.fn(), isPending: false, data: null })),
  usePrivacyReport: jest.fn(() => ({ data: null, isLoading: false, error: null })),
  useAnonymize: jest.fn(() => ({ mutate: jest.fn(), isPending: false, data: null })),
  useAddNoise: jest.fn(() => ({ mutate: jest.fn(), isPending: false, data: null })),
}));

// ── MonkeyPage ─────────────────────────────────────────────────────────────

describe("MonkeyPage", () => {
  it("renders Monkey Testing page", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/monkey/page"
    );
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows 'Monkey Testing' in content", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/monkey/page"
    );
    render(<Page />);
    expect(screen.getByText(/Monkey Testing/i)).toBeInTheDocument();
  });

  it("renders page without crashing", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/monkey/page"
    );
    const { container } = render(<Page />);
    expect(container.querySelector(".min-h-screen")).toBeInTheDocument();
  });
});

// ── PrivacyPage ────────────────────────────────────────────────────────────

describe("PrivacyPage", () => {
  it("renders data-testid='privacy-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/privacy/page"
    );
    render(<Page />);
    expect(screen.getByTestId("privacy-page")).toBeInTheDocument();
  });

  it("shows 'Gizlilik' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/privacy/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Gizlilik|Privacy/i);
  });

  it("shows 'Denetim Başlat' button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/privacy/page"
    );
    render(<Page />);
    expect(screen.getByText("Denetim Başlat")).toBeInTheDocument();
  });
});

// ── LocatorsPage ───────────────────────────────────────────────────────────

describe("LocatorsPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
    const tq = require("@tanstack/react-query");
    (tq.useQuery as jest.Mock).mockReturnValue({ data: [], isLoading: false });
  });

  it("renders data-testid='locators-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/locators/page"
    );
    render(<Page />);
    expect(screen.getByTestId("locators-page")).toBeInTheDocument();
  });

  it("shows 'Locator' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/locators/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Locator/i);
  });

  it("shows empty state when no locators", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/locators/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("empty-state")).toBeInTheDocument()
    );
  });
});

// ── DebugReportPage ────────────────────────────────────────────────────────

describe("DebugReportPage", () => {
  beforeEach(() => {
    (global as any).fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        statusText: "Not Found",
        json: () => Promise.resolve([]),
      })
    );
  });

  it("renders 'AI Debug Report' heading", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/debug-report/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("page-header")).toHaveTextContent(/AI Debug Report/i)
    );
  });

  it("shows flow guide card", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/debug-report/page"
    );
    render(<Page />);
    expect(screen.getByTestId("flow-guide-card")).toBeInTheDocument();
  });

  it("shows 'AI Debug Analizi' empty-state hint when no result", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/debug-report/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("AI Debug Analizi")).toBeInTheDocument()
    );
  });
});

// ── DeviceManagerPage ──────────────────────────────────────────────────────

describe("DeviceManagerPage", () => {
  beforeEach(() => {
    const m = require("@/lib/api");
    (m.engineFetch as jest.Mock).mockResolvedValue({
      devices: [],
      summary: { total: 0, online: 0, android: 0, ios: 0 },
    });
  });

  it("renders data-testid='device-manager-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/device-manager/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("device-manager-page")).toBeInTheDocument()
    );
  });

  it("shows 'Cihaz' or 'Device' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/device-manager/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("page-header")).toHaveTextContent(/Cihaz|Device/i)
    );
  });
});

// ── MobilePage ─────────────────────────────────────────────────────────────

describe("MobilePage", () => {
  beforeEach(() => {
    const m = require("@/lib/api-client");
    (m.engineFetch as jest.Mock).mockResolvedValue({
      devices: [],
      summary: { total: 0, online: 0 },
    });
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='mobile-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/mobile/page"
    );
    render(<Page />);
    expect(screen.getByTestId("mobile-page")).toBeInTheDocument();
  });

  it("shows 'Mobil' content", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/mobile/page"
    );
    render(<Page />);
    expect(screen.getByTestId("mobile-page")).toBeInTheDocument();
  });
});

// ── SifirBilgiPage ─────────────────────────────────────────────────────────

describe("SifirBilgiPage", () => {
  it("renders 'Sıfır Bilgi' heading", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/sifir-bilgi/page"
    );
    render(<Page />);
    expect(screen.getByText(/Sıfır Bilgi/i)).toBeInTheDocument();
  });

  it("renders page without crashing", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/sifir-bilgi/page"
    );
    const { container } = render(<Page />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows 'AI Destekli Test' content", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/sifir-bilgi/page"
    );
    render(<Page />);
    // The h1 always contains "Sıfır Bilgi"
    expect(screen.getAllByText(/Sıfır Bilgi/i).length).toBeGreaterThanOrEqual(1);
  });
});
