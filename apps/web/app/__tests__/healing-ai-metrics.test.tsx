/**
 * Tests for HealingPage and AiMetricsPage
 */
import React from "react";
import { render, screen } from "@testing-library/react";

// ── Standard mocks ──────────────────────────────────────────────────────────
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

jest.mock("@/lib/api", () => ({ apiFetch: jest.fn() }));

jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">
      {title}
      {right && <div data-testid="page-header-right">{right}</div>}
    </div>
  ),
}));

jest.mock("@/components/nexus/SectionCard", () => ({
  SectionCard: ({ title, children }: any) => (
    <div data-testid={`section-${title}`}>{children}</div>
  ),
}));

jest.mock("@/components/nexus/EmptyState", () => ({
  EmptyState: ({ title, description }: any) => (
    <div data-testid="empty-state">
      {title}
      {description && <p>{description}</p>}
    </div>
  ),
}));

// ── HealingPage-specific mock ────────────────────────────────────────────────
jest.mock("@/lib/hooks/use-api-testing", () => ({
  useHealingStats: jest.fn(),
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

// ── AiMetricsPage-specific mock ──────────────────────────────────────────────
jest.mock("@/lib/hooks/use-ai-metrics", () => ({
  useQualityMetrics: jest.fn(),
  useLlmTraceStats: jest.fn(),
}));

// ── Helpers ──────────────────────────────────────────────────────────────────
import { useHealingStats } from "@/lib/hooks/use-api-testing";
import { useQualityMetrics, useLlmTraceStats } from "@/lib/hooks/use-ai-metrics";

const mockUseHealingStats = useHealingStats as jest.MockedFunction<typeof useHealingStats>;
const mockUseQualityMetrics = useQualityMetrics as jest.MockedFunction<typeof useQualityMetrics>;
const mockUseLlmTraceStats = useLlmTraceStats as jest.MockedFunction<typeof useLlmTraceStats>;

// Full healing stats fixture
const fullHealingStats = {
  total_healing_attempts: 120,
  success_rate: 0.85,
  avg_retries_needed: 2.3,
  avg_healing_time_ms: 1500,
  saved_ci_time_ms: 45000,
  by_category: {
    timeout: { healed: 30, attempts: 35, rate: 0.857 },
    server_error: { healed: 20, attempts: 25, rate: 0.8 },
  },
  top_healed_tests: [
    { test_case_id: "tc-1", title: "Login test", heal_count: 15 },
    { test_case_id: "tc-2", title: "Checkout test", heal_count: 10 },
  ],
};

// Full metrics fixture
const fullMetrics = {
  overview: {
    total_calls: 500,
    success_rate: 92.5,
    json_parse_rate: 98.1,
    avg_latency_ms: 320,
  },
  by_agent: [
    { agent: "NL Generator", calls: 200, success_rate: 94.0, avg_latency_ms: 280 },
  ],
  recommendations: ["Basari orani normal seviyelerde", "JSON parse hatasi tespit edildi"],
};

// ════════════════════════════════════════════════════════════════════════════
// HealingPage tests
// ════════════════════════════════════════════════════════════════════════════
import HealingPage from "@/app/(dashboard)/p/[projectId]/healing/page";

describe("HealingPage", () => {
  beforeEach(() => jest.clearAllMocks());

  test("1. shows loading spinner/text while isLoading=true", () => {
    mockUseHealingStats.mockReturnValue({ data: undefined, isLoading: true } as any);
    render(<HealingPage />);
    expect(screen.getByText("Yükleniyor…")).toBeInTheDocument();
  });

  test("2. shows page container data-testid='healing-page' when data loaded", () => {
    mockUseHealingStats.mockReturnValue({ data: fullHealingStats, isLoading: false } as any);
    render(<HealingPage />);
    expect(screen.getByTestId("healing-page")).toBeInTheDocument();
  });

  test("3. shows 'Otomatik Onarım (Self-Healing)' title in PageHeader", () => {
    mockUseHealingStats.mockReturnValue({ data: fullHealingStats, isLoading: false } as any);
    render(<HealingPage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Otomatik Onarım (Self-Healing)");
  });

  test("4. shows success rate percentage when stats provided", () => {
    // success_rate = 0.85 → 85%
    mockUseHealingStats.mockReturnValue({ data: fullHealingStats, isLoading: false } as any);
    render(<HealingPage />);
    // The page renders it twice (stat tile + gauge bar label)
    const rates = screen.getAllByText("85%");
    expect(rates.length).toBeGreaterThanOrEqual(1);
  });

  test("5. shows empty state when stats is null and not loading", () => {
    mockUseHealingStats.mockReturnValue({ data: null, isLoading: false } as any);
    render(<HealingPage />);
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByText("Henüz healing verisi yok")).toBeInTheDocument();
  });

  test("6. shows healing category stats cards (SectionCard rendered)", () => {
    mockUseHealingStats.mockReturnValue({ data: fullHealingStats, isLoading: false } as any);
    render(<HealingPage />);
    // SectionCard mock uses data-testid="section-<title>"
    expect(screen.getByTestId("section-Kategori Bazlı İstatistik")).toBeInTheDocument();
    // Category labels should appear (multiple times allowed — one in stats card, one in history list)
    expect(screen.getAllByText("Zaman Aşımı").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Sunucu Hatası").length).toBeGreaterThanOrEqual(1);
  });

  test("7. shows total_healing_attempts count when data provided", () => {
    mockUseHealingStats.mockReturnValue({ data: fullHealingStats, isLoading: false } as any);
    render(<HealingPage />);
    // total_healing_attempts = 120, shown in "Toplam Deneme" card
    expect(screen.getByText("120")).toBeInTheDocument();
  });

  test("8. shows avg_healing_time_ms formatted correctly", () => {
    mockUseHealingStats.mockReturnValue({ data: fullHealingStats, isLoading: false } as any);
    render(<HealingPage />);
    // 1500ms → "1.5s"
    expect(screen.getByText("1.5s")).toBeInTheDocument();
  });
});

// ════════════════════════════════════════════════════════════════════════════
// AiMetricsPage tests
// ════════════════════════════════════════════════════════════════════════════
import AiMetricsPage from "@/app/(dashboard)/p/[projectId]/ai-metrics/page";

describe("AiMetricsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // traceStats returns null by default unless overridden
    mockUseLlmTraceStats.mockReturnValue({ data: null, isLoading: false } as any);
  });

  test("1. shows data-testid='ai-metrics-loading' while isLoading=true", () => {
    mockUseQualityMetrics.mockReturnValue({ data: undefined, isLoading: true } as any);
    render(<AiMetricsPage />);
    expect(screen.getByTestId("ai-metrics-loading")).toBeInTheDocument();
  });

  test("2. shows 'LLM Kalite Metrikleri' page title", () => {
    mockUseQualityMetrics.mockReturnValue({ data: undefined, isLoading: true } as any);
    render(<AiMetricsPage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("LLM Kalite Metrikleri");
  });

  test("3. shows data-testid='ai-metrics-empty' when total_calls=0", () => {
    mockUseQualityMetrics.mockReturnValue({
      data: { overview: { total_calls: 0, success_rate: 0, json_parse_rate: 0, avg_latency_ms: 0 }, by_agent: [], recommendations: [] },
      isLoading: false,
    } as any);
    render(<AiMetricsPage />);
    expect(screen.getByTestId("ai-metrics-empty")).toBeInTheDocument();
    expect(screen.getByText("Henuz veri yok")).toBeInTheDocument();
  });

  test("4. shows data-testid='ai-metrics-page' when data has calls", () => {
    mockUseQualityMetrics.mockReturnValue({ data: fullMetrics, isLoading: false } as any);
    render(<AiMetricsPage />);
    expect(screen.getByTestId("ai-metrics-page")).toBeInTheDocument();
  });

  test("5. shows total_calls count when data is present", () => {
    mockUseQualityMetrics.mockReturnValue({ data: fullMetrics, isLoading: false } as any);
    render(<AiMetricsPage />);
    // 500 formatted via toLocaleString → "500" (no separator at this scale)
    expect(screen.getByText("500")).toBeInTheDocument();
  });

  test("6. shows success_rate percentage", () => {
    mockUseQualityMetrics.mockReturnValue({ data: fullMetrics, isLoading: false } as any);
    render(<AiMetricsPage />);
    // overview.success_rate = 92.5 → "92.5%"
    expect(screen.getByText("92.5%")).toBeInTheDocument();
  });

  test("7. shows day selector with multiple options", () => {
    mockUseQualityMetrics.mockReturnValue({ data: fullMetrics, isLoading: false } as any);
    render(<AiMetricsPage />);
    // The select has options for 7, 14, 30, 60, 90 days
    expect(screen.getByRole("combobox", { name: /zaman araligi sec/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "7 gun" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "30 gun" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "90 gun" })).toBeInTheDocument();
  });

  test("8. shows recommendations section when data has recommendations", () => {
    mockUseQualityMetrics.mockReturnValue({ data: fullMetrics, isLoading: false } as any);
    render(<AiMetricsPage />);
    // SectionCard mock renders data-testid="section-AI Onerileri"
    expect(screen.getByTestId("section-AI Onerileri")).toBeInTheDocument();
    expect(screen.getByText("Basari orani normal seviyelerde")).toBeInTheDocument();
    expect(screen.getByText("JSON parse hatasi tespit edildi")).toBeInTheDocument();
  });
});
