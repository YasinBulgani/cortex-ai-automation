/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

// ── Global mocks ────────────────────────────────────────────────────────────
beforeAll(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  jest.spyOn(console, "warn").mockImplementation(() => {});
});
afterAll(() => {
  (console.error as jest.Mock).mockRestore();
  (console.warn as jest.Mock).mockRestore();
});

jest.mock("next/link", () => function MockLink({ href, children, ...rest }: any) {
  return <a href={href} {...rest}>{children}</a>;
});
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  useParams: () => ({}),
  usePathname: () => "/p/proj-1",
}));
jest.mock("@/lib/use-route-param", () => ({ useRouteParam: jest.fn(() => "proj-1") }));
jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn(),
  engineFetch: jest.fn(),
  ENGINE_BASE: "http://localhost:5001",
}));
jest.mock("@/lib/utils", () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(" "),
}));

jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">{title}{right && <div>{right}</div>}</div>
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
jest.mock("@/components/nexus/StatusBadge", () => ({
  StatusBadge: ({ status }: any) => <span>{status}</span>,
}));
jest.mock("@/components/nexus/StatCard", () => ({
  StatCard: ({ label, value }: any) => (
    <div data-testid={`stat-${label}`}>{String(value)}</div>
  ),
}));
jest.mock("@/components/nexus/MetricRow", () => ({
  MetricRow: ({ children }: any) => <div>{children}</div>,
}));
jest.mock("@/components/ServiceTestingGuide", () => ({
  ServiceTestingGuide: () => <div data-testid="service-testing-guide" />,
}));
jest.mock("@/components/FlowGuideCard", () => ({
  FlowGuideCard: () => <div data-testid="flow-guide-card" />,
}));
jest.mock("@/components/dnd/FileDropZone", () => ({
  FileDropZone: ({ onFiles }: any) => (
    <div data-testid="file-drop-zone">
      <input
        data-testid="file-drop-input"
        type="file"
        onChange={(e) => {
          if (e.target.files) onFiles(Array.from(e.target.files));
        }}
      />
    </div>
  ),
}));
jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, disabled, type, ...rest }: any) => (
    <button onClick={onClick} disabled={disabled} type={type} {...rest}>
      {children}
    </button>
  ),
}));
jest.mock("@/components/ui/input", () => ({
  Input: ({ value, onChange, placeholder, ...rest }: any) => (
    <input value={value} onChange={onChange} placeholder={placeholder} {...rest} />
  ),
}));
jest.mock("@/components/ui/badge", () => ({
  Badge: ({ children, className }: any) => (
    <span className={className}>{children}</span>
  ),
}));

// Mock hooks for flaky page
jest.mock("@/lib/hooks/use-api-testing", () => ({
  useFlakyTests: jest.fn(() => ({ data: [], isLoading: false })),
  useQuarantineList: jest.fn(() => ({ data: [], isLoading: false })),
  useQuarantineTest: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
}));

// ── Imports ──────────────────────────────────────────────────────────────────
import { apiFetch, engineFetch } from "@/lib/api";
import {
  useFlakyTests,
  useQuarantineList,
  useQuarantineTest,
} from "@/lib/hooks/use-api-testing";

const mockApiFetch = apiFetch as jest.Mock;
const mockEngineFetch = engineFetch as jest.Mock;
const mockUseFlakyTests = useFlakyTests as jest.Mock;
const mockUseQuarantineList = useQuarantineList as jest.Mock;
const mockUseQuarantineTest = useQuarantineTest as jest.Mock;

// ────────────────────────────────────────────────────────────────────────────
// 1. FlakyTestsPage
// ────────────────────────────────────────────────────────────────────────────
import FlakyTestsPage from "@/app/(dashboard)/p/[projectId]/flaky/page";

describe("FlakyTestsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiFetch.mockResolvedValue([]);
    mockUseFlakyTests.mockReturnValue({ data: [], isLoading: false });
    mockUseQuarantineList.mockReturnValue({ data: [], isLoading: false });
    mockUseQuarantineTest.mockReturnValue({ mutate: jest.fn(), isPending: false });
  });

  it("renders the page container", async () => {
    await act(async () => {
      render(<FlakyTestsPage />);
    });
    expect(screen.getByTestId("flaky-page")).toBeInTheDocument();
  });

  it("displays 'Flaky Testler' title in page header", async () => {
    await act(async () => {
      render(<FlakyTestsPage />);
    });
    expect(screen.getByTestId("page-header")).toHaveTextContent("Flaky Testler");
  });

  it("renders stat cards for Toplam Flaky, Yüksek Risk, AI Anomali", async () => {
    await act(async () => {
      render(<FlakyTestsPage />);
    });
    expect(screen.getByTestId("stat-Toplam Flaky")).toBeInTheDocument();
    expect(screen.getByTestId("stat-Yüksek Risk")).toBeInTheDocument();
    expect(screen.getByTestId("stat-AI Anomali")).toBeInTheDocument();
  });

  it("shows empty state when no flaky tests exist", async () => {
    mockApiFetch.mockResolvedValue([]);
    await act(async () => {
      render(<FlakyTestsPage />);
    });
    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    });
    expect(screen.getByTestId("empty-state")).toHaveTextContent(
      "Flaky test yok — tebrikler!"
    );
  });

  it("renders the four tab buttons", async () => {
    await act(async () => {
      render(<FlakyTestsPage />);
    });
    expect(screen.getByText("Flaky Listesi")).toBeInTheDocument();
    expect(screen.getByText("API Flaky")).toBeInTheDocument();
    expect(screen.getByText("Karantina")).toBeInTheDocument();
    expect(screen.getByText("Anomali")).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 2. AnalysisPage
// ────────────────────────────────────────────────────────────────────────────
import AnalysisPage from "@/app/(dashboard)/p/[projectId]/analysis/page";

describe("AnalysisPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiFetch.mockResolvedValue([]);
  });

  it("renders the page container", async () => {
    await act(async () => {
      render(<AnalysisPage />);
    });
    expect(screen.getByTestId("analysis-page")).toBeInTheDocument();
  });

  it("displays 'Analiz Merkezi' heading", async () => {
    await act(async () => {
      render(<AnalysisPage />);
    });
    expect(screen.getByText("Analiz Merkezi")).toBeInTheDocument();
  });

  it("renders the four navigation tabs", async () => {
    await act(async () => {
      render(<AnalysisPage />);
    });
    expect(screen.getByText("Analiz")).toBeInTheDocument();
    expect(screen.getByText("Manuel Testler")).toBeInTheDocument();
    expect(screen.getByText("BDD Senaryolar")).toBeInTheDocument();
    expect(screen.getByText("Kayitli Senaryolar")).toBeInTheDocument();
  });

  it("shows the Analiz Et button and textarea in analyze tab", async () => {
    await act(async () => {
      render(<AnalysisPage />);
    });
    expect(screen.getByText("Analiz Et")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Gereksinim veya analiz/)).toBeInTheDocument();
  });

  it("shows empty manual tests message when switching to manual tab with no data", async () => {
    await act(async () => {
      render(<AnalysisPage />);
    });
    // Switch to manual tab
    fireEvent.click(screen.getByText("Manuel Testler"));
    await waitFor(() => {
      expect(
        screen.getByText(/Henuz manuel test uretilmedi/)
      ).toBeInTheDocument();
    });
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 3. IntegrationsPage
// ────────────────────────────────────────────────────────────────────────────
import IntegrationsPage from "@/app/(dashboard)/p/[projectId]/integrations/page";

describe("IntegrationsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiFetch.mockResolvedValue([]);
  });

  it("renders the page container", async () => {
    await act(async () => {
      render(<IntegrationsPage />);
    });
    expect(screen.getByTestId("integrations-page")).toBeInTheDocument();
  });

  it("displays 'Entegrasyonlar' title in page header", async () => {
    await act(async () => {
      render(<IntegrationsPage />);
    });
    expect(screen.getByTestId("page-header")).toHaveTextContent("Entegrasyonlar");
  });

  it("shows stat cards for Toplam, Aktif, Pasif", async () => {
    await act(async () => {
      render(<IntegrationsPage />);
    });
    expect(screen.getByTestId("stat-Toplam")).toBeInTheDocument();
    expect(screen.getByTestId("stat-Aktif")).toBeInTheDocument();
    expect(screen.getByTestId("stat-Pasif")).toBeInTheDocument();
  });

  it("shows empty state when no integrations exist", async () => {
    mockApiFetch.mockResolvedValue([]);
    await act(async () => {
      render(<IntegrationsPage />);
    });
    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    });
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Entegrasyon yok");
  });

  it("opens the add integration form when 'Yeni Entegrasyon' button is clicked", async () => {
    await act(async () => {
      render(<IntegrationsPage />);
    });
    const addBtn = screen.getByText("Yeni Entegrasyon");
    fireEvent.click(addBtn);
    await waitFor(() => {
      expect(screen.getByTestId("integrations-form")).toBeInTheDocument();
    });
    expect(screen.getByTestId("integrations-select-provider")).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 4. DeviceManagerPage
// ────────────────────────────────────────────────────────────────────────────
import DeviceManagerPage from "@/app/(dashboard)/p/[projectId]/device-manager/page";

describe("DeviceManagerPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockEngineFetch.mockResolvedValue({ devices: [], summary: null });
  });

  it("renders the page container", async () => {
    await act(async () => {
      render(<DeviceManagerPage />);
    });
    expect(screen.getByTestId("device-manager-page")).toBeInTheDocument();
  });

  it("displays 'Cihaz Yönetim Merkezi' title in page header", async () => {
    await act(async () => {
      render(<DeviceManagerPage />);
    });
    expect(screen.getByTestId("page-header")).toHaveTextContent("Cihaz Yönetim Merkezi");
  });

  it("shows the platform filter buttons (Tümü, Android, iOS)", async () => {
    await act(async () => {
      render(<DeviceManagerPage />);
    });
    expect(screen.getByText("Tümü")).toBeInTheDocument();
    expect(screen.getByText("🤖 Android")).toBeInTheDocument();
    expect(screen.getByText("🍎 iOS")).toBeInTheDocument();
  });

  it("shows empty state when no devices are found after loading", async () => {
    mockEngineFetch.mockResolvedValue({ devices: [], summary: null });
    await act(async () => {
      render(<DeviceManagerPage />);
    });
    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    });
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Bağlı cihaz bulunamadı");
  });

  it("renders device cards when devices are returned from engineFetch", async () => {
    const mockDevice = {
      serial: "emulator-5554",
      state: "online",
      online: true,
      platform: "android",
      device_type: "emulator",
      name: "Pixel 6",
      brand: "Google",
      android_version: "13",
      screen_size: "6.4inch",
      health_score: 95,
      battery: { level: 80 },
      installed_apps_count: 10,
      uptime: "2h 30m",
    };
    mockEngineFetch.mockResolvedValue({
      devices: [mockDevice],
      summary: { total: 1, online: 1, android: 1, ios: 0, physical: 0 },
    });
    await act(async () => {
      render(<DeviceManagerPage />);
    });
    await waitFor(() => {
      expect(screen.getByTestId("device-card-emulator-5554")).toBeInTheDocument();
    });
    expect(screen.getByText("Pixel 6")).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 5. ManualPage
// ────────────────────────────────────────────────────────────────────────────
import ManualPage from "@/app/(dashboard)/p/[projectId]/manual/page";

describe("ManualPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiFetch.mockResolvedValue([]);
  });

  it("renders the page container", async () => {
    await act(async () => {
      render(<ManualPage />);
    });
    expect(screen.getByTestId("manual-tests-page")).toBeInTheDocument();
  });

  it("displays 'Manuel Testler' title in page header", async () => {
    await act(async () => {
      render(<ManualPage />);
    });
    expect(screen.getByTestId("page-header")).toHaveTextContent("Manuel Testler");
  });

  it("shows stat cards for Toplam, Geçti, Başarısız, Engellendi", async () => {
    await act(async () => {
      render(<ManualPage />);
    });
    expect(screen.getByTestId("stat-Toplam")).toBeInTheDocument();
    expect(screen.getByTestId("stat-Geçti")).toBeInTheDocument();
    expect(screen.getByTestId("stat-Başarısız")).toBeInTheDocument();
    expect(screen.getByTestId("stat-Engellendi")).toBeInTheDocument();
  });

  it("shows empty state when no tests exist", async () => {
    mockApiFetch.mockResolvedValue([]);
    await act(async () => {
      render(<ManualPage />);
    });
    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    });
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Henüz manuel test yok");
  });

  it("opens the new test form when 'Yeni Test' button is clicked", async () => {
    await act(async () => {
      render(<ManualPage />);
    });
    const newBtn = screen.getByTestId("manual-tests-btn-new");
    fireEvent.click(newBtn);
    await waitFor(() => {
      expect(screen.getByTestId("manual-tests-create-form")).toBeInTheDocument();
    });
    expect(screen.getByTestId("manual-tests-input-title")).toBeInTheDocument();
    expect(screen.getByTestId("manual-tests-select-priority")).toBeInTheDocument();
  });
});
