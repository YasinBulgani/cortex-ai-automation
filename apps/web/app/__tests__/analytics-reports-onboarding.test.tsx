/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ── Suppress console errors/warnings in tests ──────────────────────────────
beforeAll(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  jest.spyOn(console, "warn").mockImplementation(() => {});
});
afterAll(() => {
  (console.error as jest.Mock).mockRestore();
  (console.warn as jest.Mock).mockRestore();
});

// ── Standard mocks ─────────────────────────────────────────────────────────
jest.mock("next/link", () =>
  function MockLink({ href, children, ...rest }: any) {
    return <a href={href} {...rest}>{children}</a>;
  }
);

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useParams: () => ({}),
  usePathname: () => "/p/proj-1",
}));

jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn(),
  engineFetch: jest.fn(),
  getToken: jest.fn(() => "tok"),
  ENGINE_BASE: "http://localhost:5001",
}));

jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">
      {title}
      {right && <div>{right}</div>}
    </div>
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
  FilterBar: ({ children }: any) => <div>{children}</div>,
  ProgressBar: ({ value }: any) => <div data-testid="progress-bar">{value}</div>,
  TrendBadge: ({ label }: any) => <span data-testid="trend-badge">{label}</span>,
}));

jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">
      {title}
      {right}
    </div>
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

// ── Reports-specific mocks ──────────────────────────────────────────────────
jest.mock("@/components/FlowGuideCard", () => ({
  FlowGuideCard: () => <div data-testid="flow-guide-card" />,
}));

jest.mock("@/lib/useFetch", () => ({
  useFetch: jest.fn(() => ({ data: null, loading: false })),
}));

jest.mock("@/lib/provenance", () => ({
  isRealProvenance: jest.fn(() => true),
  normalizeProvenance: jest.fn((r: any) => r.provenance ?? "real"),
  provenanceBadgeClass: jest.fn(() => ""),
  provenanceLabel: jest.fn(() => "Gerçek"),
}));

// ── Analytics-specific mocks ───────────────────────────────────────────────
jest.mock("@/lib/useRealtimeExecution", () => ({
  useRealtimeExecution: jest.fn(),
}));

// ── FlowDesigner-specific mocks ────────────────────────────────────────────
jest.mock("@/lib/useProject", () => ({
  useProject: jest.fn(() => ({ projectId: "proj-1" })),
}));

// ── Tabs UI component mock ─────────────────────────────────────────────────
jest.mock("@/components/ui/tabs", () => ({
  Tabs: ({ children }: any) => <div>{children}</div>,
  TabsList: ({ children }: any) => <div>{children}</div>,
  TabsTrigger: ({ children, value, onClick }: any) => (
    <button data-value={value} onClick={onClick}>{children}</button>
  ),
}));

// ── Import pages ───────────────────────────────────────────────────────────
import AnalyticsPage from "@/app/(dashboard)/p/[projectId]/analytics/page";
import ReportsPage from "@/app/(dashboard)/p/[projectId]/reports/page";
import OnboardingPage from "@/app/(dashboard)/onboarding/page";
import FlowDesignerPage from "@/app/(dashboard)/flow-designer/page";

const { apiFetch, engineFetch } = require("@/lib/api");
const { useFetch } = require("@/lib/useFetch");

// ══════════════════════════════════════════════════════════════════════════
// ANALYTICS PAGE  (5 tests)
// ══════════════════════════════════════════════════════════════════════════
describe("AnalyticsPage", () => {
  beforeEach(() => {
    apiFetch.mockResolvedValue([]);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the analytics page container", () => {
    render(<AnalyticsPage />);
    expect(screen.getByTestId("analytics-page")).toBeInTheDocument();
  });

  it("renders the page header with title 'Analitik'", () => {
    render(<AnalyticsPage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Analitik");
  });

  it("renders stat cards for total runs, pass rate, scenarios, and flaky tests", () => {
    render(<AnalyticsPage />);
    expect(screen.getByTestId("stat-Toplam Koşu")).toBeInTheDocument();
    expect(screen.getByTestId("stat-Ort. Başarı Oranı")).toBeInTheDocument();
    expect(screen.getByTestId("stat-Toplam Senaryo")).toBeInTheDocument();
    expect(screen.getByTestId("stat-Flaky Test")).toBeInTheDocument();
  });

  it("shows 'Trend verisi yok' when trends are empty", async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText("Trend verisi yok")).toBeInTheDocument();
    });
  });

  it("renders the 'Anomali Tara' button and triggers anomaly detection", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url.includes("anomaly-detect")) {
        return Promise.resolve({
          anomalies: [],
          total_analyzed: 10,
          anomaly_count: 0,
          avg_duration: 5,
        });
      }
      return Promise.resolve([]);
    });

    render(<AnalyticsPage />);
    const btn = screen.getByText("Anomali Tara");
    expect(btn).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(btn);
    });

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        expect.stringContaining("anomaly-detect"),
        expect.objectContaining({ method: "POST" }),
      );
    });
  });
});

// ══════════════════════════════════════════════════════════════════════════
// REPORTS PAGE  (5 tests)
// ══════════════════════════════════════════════════════════════════════════
describe("ReportsPage", () => {
  beforeEach(() => {
    useFetch.mockReturnValue({ data: null, loading: false });
    engineFetch.mockResolvedValue({ runs: [] });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the reports page container", () => {
    render(<ReportsPage />);
    expect(screen.getByTestId("reports-page")).toBeInTheDocument();
  });

  it("renders the page header with title 'Raporlar'", () => {
    render(<ReportsPage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Raporlar");
  });

  it("renders the CSV and HTML report buttons", () => {
    render(<ReportsPage />);
    expect(screen.getByTestId("reports-btn-csv")).toBeInTheDocument();
    expect(screen.getByTestId("reports-btn-html")).toBeInTheDocument();
  });

  it("shows 'Henüz koşu yok' empty state when there are no executions", async () => {
    useFetch.mockReturnValue({ data: [], loading: false });
    render(<ReportsPage />);
    await waitFor(() => {
      expect(screen.getByText("Henüz koşu yok")).toBeInTheDocument();
    });
  });

  it("renders execution rows when executions data is available", async () => {
    useFetch.mockReturnValue({
      data: [
        { id: "exec-1", name: "Test Koşusu 1", status: "completed", created_at: "2024-01-15T10:00:00Z" },
        { id: "exec-2", name: "Test Koşusu 2", status: "failed", created_at: "2024-01-14T09:00:00Z" },
      ],
      loading: false,
    });
    render(<ReportsPage />);
    await waitFor(() => {
      expect(screen.getByText("Test Koşusu 1")).toBeInTheDocument();
      expect(screen.getByText("Test Koşusu 2")).toBeInTheDocument();
    });
  });
});

// ══════════════════════════════════════════════════════════════════════════
// ONBOARDING PAGE  (5 tests)
// ══════════════════════════════════════════════════════════════════════════
describe("OnboardingPage", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the onboarding page container", () => {
    render(<OnboardingPage />);
    expect(screen.getByTestId("onboarding-page")).toBeInTheDocument();
  });

  // OnboardingPage was refactored from a single create-project form into a 5-step wizard
  // that renders one step at a time. The new UI's main testid is `onboarding-page`;
  // step-specific testids no longer exist.
  it("renders the wizard's first step heading 'Rolünüz nedir?'", () => {
    render(<OnboardingPage />);
    expect(screen.getByText("Rolünüz nedir?")).toBeInTheDocument();
  });

  it("renders the onboarding-page container", () => {
    render(<OnboardingPage />);
    expect(screen.getByTestId("onboarding-page")).toBeInTheDocument();
  });

  it("renders the page heading area (h1)", () => {
    const { container } = render(<OnboardingPage />);
    expect(container.querySelector("h1")).toBeInTheDocument();
  });

  it("does not render legacy form testids (input-name / btn-create / btn-skip)", () => {
    render(<OnboardingPage />);
    expect(screen.queryByTestId("onboarding-input-name")).not.toBeInTheDocument();
    expect(screen.queryByTestId("onboarding-btn-create")).not.toBeInTheDocument();
    expect(screen.queryByTestId("onboarding-btn-skip")).not.toBeInTheDocument();
  });
});

// ══════════════════════════════════════════════════════════════════════════
// FLOW DESIGNER PAGE  (5 tests)
// ══════════════════════════════════════════════════════════════════════════
describe("FlowDesignerPage", () => {
  beforeEach(() => {
    apiFetch.mockResolvedValue([{ id: "p1", name: "Proje 1" }]);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the flow designer page with title 'Akış Tasarımcısı'", () => {
    render(<FlowDesignerPage />);
    expect(screen.getByText("Akış Tasarımcısı")).toBeInTheDocument();
  });

  it("renders template cards in the default 'all' category view", async () => {
    render(<FlowDesignerPage />);
    await waitFor(() => {
      // At least one template should be visible
      expect(screen.getByText("Senaryo Üreticisi")).toBeInTheDocument();
    });
  });

  it("renders category filter buttons", () => {
    render(<FlowDesignerPage />);
    expect(screen.getByText("Tüm Kategoriler")).toBeInTheDocument();
    // "Otomasyon" may appear both as a filter button and as a group heading; use getAllByText
    expect(screen.getAllByText("Otomasyon").length).toBeGreaterThanOrEqual(1);
    // "Test" also appears as group heading; verify the filter button is present
    expect(screen.getAllByText("Test").length).toBeGreaterThanOrEqual(1);
  });

  it("filters templates when a category button is clicked", async () => {
    render(<FlowDesignerPage />);
    // "Test" can appear as both a filter button (role=button) and as a group heading (h2)
    // Click the filter button specifically
    const testButtons = screen.getAllByText("Test");
    const testFilterBtn = testButtons.find(
      (el) => el.tagName.toLowerCase() === "button",
    )!;
    fireEvent.click(testFilterBtn);
    await waitFor(() => {
      // API Sözleşme Doğrulama is in 'test' category
      expect(screen.getByText("API Sözleşme Doğrulama")).toBeInTheDocument();
      // Senaryo Üreticisi is in 'automation' - should not show
      expect(screen.queryByText("Senaryo Üreticisi")).not.toBeInTheDocument();
    });
  });

  it("opens the UseTemplateModal when 'Şablonu Kullan' is clicked", async () => {
    render(<FlowDesignerPage />);
    await waitFor(() => {
      expect(screen.getByText("Senaryo Üreticisi")).toBeInTheDocument();
    });
    // There are multiple "Şablonu Kullan" buttons; click the first one
    const useButtons = screen.getAllByText("Şablonu Kullan");
    fireEvent.click(useButtons[0]);
    // After clicking, the modal should appear with the "Akışı Oluştur" submit button
    await waitFor(() => {
      expect(screen.getByText("Akışı Oluştur")).toBeInTheDocument();
    });
  });
});
