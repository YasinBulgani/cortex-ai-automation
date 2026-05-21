/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// ─── Suppress noisy console errors ───────────────────────────────────────────
let consoleErrorSpy: jest.SpyInstance;
let consoleWarnSpy: jest.SpyInstance;

beforeAll(() => {
  consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
  consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});
});
afterAll(() => {
  consoleErrorSpy.mockRestore();
  consoleWarnSpy.mockRestore();
});

// ─── Standard mocks ───────────────────────────────────────────────────────────
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

jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn(),
  ENGINE_BASE: "http://localhost:5001",
}));

jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">
      {title}
      {right && <div>{right}</div>}
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
  EmptyState: ({ title }: any) => (
    <div data-testid="empty-state">{title}</div>
  ),
}));

jest.mock("@/components/nexus/StatCard", () => ({
  StatCard: ({ label, value }: any) => (
    <div data-testid={`stat-${label}`}>{String(value)}</div>
  ),
}));

jest.mock("@/components/nexus/MetricRow", () => ({
  MetricRow: ({ children }: any) => <div>{children}</div>,
}));

jest.mock("@/components/nexus/ToolbarActions", () => ({
  ToolbarActions: ({ children }: any) => <div>{children}</div>,
}));

jest.mock("@/components/nexus/StatusBadge", () => ({
  StatusBadge: ({ status }: any) => <span>{status}</span>,
}));

jest.mock("@/components/nexus/FilterBar", () => ({
  FilterBar: ({ children }: any) => <div>{children}</div>,
}));

jest.mock("@/components/nexus/ProgressBar", () => ({
  ProgressBar: ({ value }: any) => (
    <div data-testid="progress-bar">{value}</div>
  ),
}));

jest.mock("@/components/nexus/CodeBlock", () => ({
  CodeBlock: ({ code }: any) => <pre data-testid="code-block">{code}</pre>,
}));

// ─── UI component mocks for AutomationPage ───────────────────────────────────
jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, disabled, "data-testid": testId, type, variant }: any) => (
    <button
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      type={type || "button"}
    >
      {children}
    </button>
  ),
}));

jest.mock("@/components/ui/input", () => ({
  Input: React.forwardRef(({ placeholder, value, onChange, required, "data-testid": testId }: any, ref: any) => (
    <input
      ref={ref}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      required={required}
      data-testid={testId}
    />
  )),
}));

jest.mock("@/components/ui/confirm-dialog", () => ({
  useConfirm: () => ({ confirm: jest.fn(async () => false) }),
}));

jest.mock("@/components/ui/toast", () => ({
  useToast: () => ({ toast: jest.fn() }),
}));

// ─── Privacy hooks mock ───────────────────────────────────────────────────────
jest.mock("@/lib/hooks/use-synthetic-advanced", () => ({
  usePrivacyReport: jest.fn(),
  usePrivacyAudit: jest.fn(),
  useAnonymize: jest.fn(),
  useAddNoise: jest.fn(),
}));

import {
  usePrivacyReport,
  usePrivacyAudit,
  useAnonymize,
  useAddNoise,
} from "@/lib/hooks/use-synthetic-advanced";

const mockUsePrivacyReport = usePrivacyReport as jest.MockedFunction<typeof usePrivacyReport>;
const mockUsePrivacyAudit = usePrivacyAudit as jest.MockedFunction<typeof usePrivacyAudit>;
const mockUseAnonymize = useAnonymize as jest.MockedFunction<typeof useAnonymize>;
const mockUseAddNoise = useAddNoise as jest.MockedFunction<typeof useAddNoise>;

// ─── Privacy page fixtures ─────────────────────────────────────────────────
const auditResult = {
  re_identification_risk: 0.85,
  total_records: 200,
  pii_columns_detected: ["name", "tc_no"],
  compliance: {
    kvkk: { compliant: false, issues: ["PII eksik"] },
    gdpr: { compliant: true, issues: [] },
    pci_dss: { compliant: true, issues: [] },
  },
  recommendations: ["PII kolonlarını maskelayın", "Şifreleme kullanın"],
  quasi_identifier_risk: { name: 0.9 },
};

function setupPrivacyMocks(opts: {
  reportLoading?: boolean;
  reportData?: any;
  reportFailed?: boolean;
  auditPending?: boolean;
  auditData?: any;
} = {}) {
  const { reportLoading = false, reportData = null, reportFailed = false, auditPending = false, auditData = null } = opts;
  mockUsePrivacyReport.mockReturnValue({
    data: reportData,
    isLoading: reportLoading,
    isError: reportFailed,
    error: reportFailed ? new Error("Gizlilik verileri yüklenemedi.") : undefined,
  } as any);
  mockUsePrivacyAudit.mockReturnValue({
    data: auditData,
    isPending: auditPending,
    mutateAsync: jest.fn(),
  } as any);
  mockUseAnonymize.mockReturnValue({
    data: null,
    isPending: false,
    mutateAsync: jest.fn(),
  } as any);
  mockUseAddNoise.mockReturnValue({
    data: null,
    isPending: false,
    mutateAsync: jest.fn(),
  } as any);
}

// ═══════════════════════════════════════════════════════════════════════════════
// PrivacyPage Tests
// ═══════════════════════════════════════════════════════════════════════════════
import PrivacyPage from "@/app/(dashboard)/p/[projectId]/privacy/page";

describe("PrivacyPage", () => {
  beforeEach(() => jest.clearAllMocks());

  test("1. page renders with data-testid='privacy-page'", () => {
    setupPrivacyMocks();
    render(<PrivacyPage />);
    expect(screen.getByTestId("privacy-page")).toBeInTheDocument();
  });

  test("2. PageHeader shows privacy-related title", () => {
    setupPrivacyMocks();
    render(<PrivacyPage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Gizlilik ve Uyumluluk");
  });

  test("3. loading state — report is loading, audit has no data", () => {
    setupPrivacyMocks({ reportLoading: true });
    render(<PrivacyPage />);
    // Page still mounts; the quick-audit button should be present
    expect(screen.getByTestId("privacy-page")).toBeInTheDocument();
    // The audit button shows default text (not "Taranıyor...")
    expect(screen.getByText("Denetim Başlat")).toBeInTheDocument();
  });

  test("4. empty state — no audit data and not loading", () => {
    setupPrivacyMocks({ reportLoading: false, reportData: null });
    render(<PrivacyPage />);
    // Without auditData the empty-state block is NOT rendered
    // (it only shows inside auditData branch). The textarea and button are visible.
    expect(screen.getByPlaceholderText("JSON dizisi yapıştırın...")).toBeInTheDocument();
  });

  test("5. quick-audit textarea and button are present", () => {
    setupPrivacyMocks();
    render(<PrivacyPage />);
    // Quick audit block is always rendered
    expect(screen.getByPlaceholderText("JSON dizisi yapıştırın...")).toBeInTheDocument();
    expect(screen.getByText("Denetim Başlat")).toBeInTheDocument();
  });

  test("6. audit button shows 'Taranıyor...' while isPending=true", () => {
    setupPrivacyMocks({ auditPending: true });
    render(<PrivacyPage />);
    expect(screen.getAllByText("Taranıyor...").length).toBeGreaterThanOrEqual(1);
  });

  test("7. compliance results render when auditData is provided via report", () => {
    setupPrivacyMocks({ reportData: auditResult });
    render(<PrivacyPage />);
    // auditData = auditMut.data || report → uses report
    // Shows re-identification risk in the result grid
    expect(screen.getByText("85.0%")).toBeInTheDocument();
    // Total records
    expect(screen.getByText("200")).toBeInTheDocument();
    // PII column count
    expect(screen.getByText("2")).toBeInTheDocument();
    // Compliance labels
    expect(screen.getByText("KVKK")).toBeInTheDocument();
    expect(screen.getByText("GDPR")).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// AutomationPage Tests
// ═══════════════════════════════════════════════════════════════════════════════
import { apiFetch } from "@/lib/api";
const mockApiFetch = apiFetch as jest.MockedFunction<typeof apiFetch>;

import AutomationPage from "@/app/(dashboard)/p/[projectId]/automation/page";

const MOCK_FEATURES = [
  { type: "file" as const, name: "login.feature", path: "login.feature", modified: "2026-01-10" },
  { type: "file" as const, name: "checkout.feature", path: "checkout.feature", modified: "2026-01-12" },
];

describe("AutomationPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("1. page renders with data-testid='automation-page'", async () => {
    // apiFetch resolves with an empty array → empty state
    mockApiFetch.mockResolvedValueOnce([]);
    render(<AutomationPage />);
    // Loading state first, then resolves
    await waitFor(() =>
      expect(screen.getByTestId("automation-page")).toBeInTheDocument()
    );
  });

  test("2. heading 'Otomasyon' renders via data-testid", async () => {
    mockApiFetch.mockResolvedValueOnce([]);
    render(<AutomationPage />);
    await waitFor(() =>
      expect(screen.getByTestId("automation-heading")).toHaveTextContent("Otomasyon")
    );
  });

  test("3. loading state shows 'Yükleniyor…' initially", () => {
    // Make apiFetch hang so loading state persists
    mockApiFetch.mockReturnValueOnce(new Promise(() => {}));
    render(<AutomationPage />);
    expect(screen.getByTestId("automation-loading")).toBeInTheDocument();
    // "Yükleniyor…" may appear in multiple places (loading region + disabled button label)
    expect(screen.getAllByText("Yükleniyor…").length).toBeGreaterThanOrEqual(1);
  });

  test("4. empty state renders when no feature files", async () => {
    mockApiFetch.mockResolvedValueOnce([]);
    render(<AutomationPage />);
    await waitFor(() =>
      expect(screen.getByTestId("automation-empty")).toBeInTheDocument()
    );
    expect(screen.getByText("Henüz feature dosyası yok")).toBeInTheDocument();
  });

  test("5. 'Yeni Feature' create button exists in header", async () => {
    mockApiFetch.mockResolvedValueOnce([]);
    render(<AutomationPage />);
    await waitFor(() =>
      expect(screen.getByTestId("automation-btn-new")).toBeInTheDocument()
    );
    expect(screen.getByTestId("automation-btn-new")).toHaveTextContent("+ Yeni Feature");
  });

  test("6. file list renders when features are loaded", async () => {
    // First call: list returns two feature files
    mockApiFetch
      .mockResolvedValueOnce(MOCK_FEATURES)          // load()
      .mockResolvedValueOnce({ name: "login.feature", content: "Feature: Login\n" }); // loadDetail()
    render(<AutomationPage />);
    await waitFor(() =>
      expect(screen.getByTestId("automation-file-list")).toBeInTheDocument()
    );
    expect(screen.getAllByText("login.feature").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("checkout.feature").length).toBeGreaterThanOrEqual(1);
  });

  test("7. create modal opens when '+ Yeni Feature' button is clicked", async () => {
    mockApiFetch.mockResolvedValueOnce([]);
    render(<AutomationPage />);
    await waitFor(() =>
      expect(screen.getByTestId("automation-btn-empty-new")).toBeInTheDocument()
    );
    fireEvent.click(screen.getByTestId("automation-btn-empty-new"));
    expect(screen.getByTestId("automation-create-modal")).toBeInTheDocument();
    expect(screen.getByTestId("automation-create-form")).toBeInTheDocument();
  });
});
