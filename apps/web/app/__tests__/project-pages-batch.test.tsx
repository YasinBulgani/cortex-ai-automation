/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ── Suppress noise ─────────────────────────────────────────────────────────
const consoleSpies: jest.SpyInstance[] = [];
beforeEach(() => {
  consoleSpies.push(jest.spyOn(console, "error").mockImplementation(() => {}));
  consoleSpies.push(jest.spyOn(console, "warn").mockImplementation(() => {}));
  (global as any).fetch = jest.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
  );
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
  useParams: () => ({}),
  redirect: jest.fn(),
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
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">{title}{right}</div>
  ),
}));
jest.mock("@/components/nexus/SectionCard", () => ({
  SectionCard: ({ title, children, right, icon }: any) => (
    <div data-testid="section-card">
      {icon}{title && <div>{title}</div>}{right}{children}
    </div>
  ),
}));
jest.mock("@/components/nexus/EmptyState", () => ({
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
}));
jest.mock("@/components/nexus/StatusBadge", () => ({
  StatusBadge: ({ status }: any) => <span data-testid={`status-${status}`}>{status}</span>,
}));
jest.mock("@/components/nexus/ProgressBar", () => ({
  ProgressBar: ({ value }: any) => <div data-testid="progress-bar">{value}</div>,
}));
jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">{title}{right}</div>
  ),
  SectionCard: ({ title, children, right, icon }: any) => (
    <div data-testid="section-card">{icon}{title && <div>{title}</div>}{right}{children}</div>
  ),
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
  StatCard: ({ label, value }: any) => <div data-testid={`stat-${label}`}>{String(value ?? "")}</div>,
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
jest.mock("@/components/ui/badge", () => ({
  Badge: ({ children }: any) => <span className="badge">{children}</span>,
}));
jest.mock("@/components/FlowGuideCard", () => ({
  FlowGuideCard: () => <div data-testid="flow-guide-card" />,
}));
jest.mock("@/components/dnd/FileDropZone", () => ({
  FileDropZone: ({ children }: any) => <div data-testid="file-drop-zone">{children}</div>,
}));

// ── AccessibilityPage ──────────────────────────────────────────────────────

describe("AccessibilityPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue({ violations: [] });
  });

  it("renders data-testid='a11y-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/accessibility/page"
    );
    render(<Page />);
    expect(screen.getByTestId("a11y-page")).toBeInTheDocument();
  });

  it("shows 'Erişilebilirlik Testi' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/accessibility/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Erişilebilirlik");
  });

  it("shows URL input field", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/accessibility/page"
    );
    render(<Page />);
    expect(screen.getByPlaceholderText(/https:\/\/|URL/i)).toBeInTheDocument();
  });

  it("shows scan button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/accessibility/page"
    );
    render(<Page />);
    expect(screen.getByTestId("a11y-btn-scan")).toBeInTheDocument();
  });
});

// ── AiChatPage ─────────────────────────────────────────────────────────────

describe("AiChatPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='ai-chat-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/ai-chat/page"
    );
    render(<Page />);
    expect(screen.getByTestId("ai-chat-page")).toBeInTheDocument();
  });

  it("shows 'Yeni Sohbet' button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/ai-chat/page"
    );
    render(<Page />);
    expect(screen.getByTestId("ai-chat-btn-new")).toBeInTheDocument();
  });

  it("shows message input area", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/ai-chat/page"
    );
    render(<Page />);
    expect(screen.getByTestId("ai-chat-input-message")).toBeInTheDocument();
  });

  it("shows send button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/ai-chat/page"
    );
    render(<Page />);
    expect(screen.getByTestId("ai-chat-btn-send")).toBeInTheDocument();
  });

  it("shows starter prompts", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/ai-chat/page"
    );
    render(<Page />);
    expect(screen.getByText("Sonraki adım")).toBeInTheDocument();
  });
});

// ── ManualToAutomationPage ─────────────────────────────────────────────────

describe("ManualToAutomationPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue({});
  });

  it("renders data-testid='manual-to-automation-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/manual-to-automation/page"
    );
    render(<Page />);
    expect(screen.getByTestId("manual-to-automation-page")).toBeInTheDocument();
  });

  it("shows 'Manuel → Otomasyon' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/manual-to-automation/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Manuel");
  });

  it("shows convert button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/manual-to-automation/page"
    );
    render(<Page />);
    expect(screen.getByTestId("convert-btn")).toBeInTheDocument();
  });

  it("shows step action input (first step)", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/manual-to-automation/page"
    );
    render(<Page />);
    expect(screen.getByTestId("step-action-0")).toBeInTheDocument();
  });
});

// ── MobileHistoryPage ──────────────────────────────────────────────────────

describe("MobileHistoryPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='mobile-history-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/mobile/history/page"
    );
    render(<Page />);
    expect(screen.getByTestId("mobile-history-page")).toBeInTheDocument();
  });

  it("shows 'Mobil Koşum Geçmişi' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/mobile/history/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Mobil Koşum Geçmişi");
  });

  it("shows 'Yeni Koşum' link button", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/mobile/history/page"
    );
    render(<Page />);
    expect(screen.getByText("Yeni Koşum")).toBeInTheDocument();
  });

  it("shows empty state when no runs", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/mobile/history/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText(/Henüz mobil koşum yok|Koşum bulunamadı|empty/i)).toBeInTheDocument()
    );
  });
});

// ── PageObjectsPage ────────────────────────────────────────────────────────

describe("PageObjectsPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='page-objects-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/page-objects/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-objects-page")).toBeInTheDocument();
  });

  it("shows 'Page Objects' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/page-objects/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Page Objects");
  });

  it("shows 'Yeni Locator Ekle' section", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/page-objects/page"
    );
    render(<Page />);
    expect(screen.getByText("Yeni Locator Ekle")).toBeInTheDocument();
  });

  it("shows 'Locator Listesi' section", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/page-objects/page"
    );
    render(<Page />);
    expect(screen.getByText("Locator Listesi")).toBeInTheDocument();
  });
});

// ── VisualRegressionPage ───────────────────────────────────────────────────

describe("VisualRegressionPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='visual-regression-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/visual/page"
    );
    render(<Page />);
    expect(screen.getByTestId("visual-regression-page")).toBeInTheDocument();
  });

  it("shows 'Visual Regression' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/visual/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Visual Regression");
  });

  it("shows baselines section", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/visual/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Baseline'lar")).toBeInTheDocument()
    );
  });

  it("shows empty baselines state", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/visual/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Henüz baseline yok")).toBeInTheDocument()
    );
  });
});

// ── SyntheticPage ──────────────────────────────────────────────────────────

describe("SyntheticPage", () => {
  beforeEach(() => {
    // fetch returns empty datasets
    (global as any).fetch = jest.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
    );
  });

  it("renders data-testid='synthetic-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/synthetic/page"
    );
    render(<Page />);
    expect(screen.getByTestId("synthetic-page")).toBeInTheDocument();
  });

  it("shows 'Sentetik Veri' in page header", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/synthetic/page"
    );
    render(<Page />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Sentetik Veri");
  });

  it("shows 'Veri Seti Kataloğu' section", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/synthetic/page"
    );
    render(<Page />);
    expect(screen.getByText("Veri Seti Kataloğu")).toBeInTheDocument();
  });

  it("shows empty state when catalog empty", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/synthetic/page"
    );
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("empty-state")).toBeInTheDocument()
    );
  });
});

// ── WizardPage ─────────────────────────────────────────────────────────────

describe("WizardPage", () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([]);
  });

  it("renders data-testid='wizard-page'", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/wizard/page"
    );
    render(<Page />);
    expect(screen.getByTestId("wizard-page")).toBeInTheDocument();
  });

  it("shows step indicators", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/wizard/page"
    );
    render(<Page />);
    expect(screen.getByTestId("wizard-step-1")).toBeInTheDocument();
  });

  it("shows URL input on step 1", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/wizard/page"
    );
    render(<Page />);
    expect(screen.getByTestId("wizard-input-url")).toBeInTheDocument();
  });

  it("shows step 1 content (URL input)", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/wizard/page"
    );
    render(<Page />);
    expect(screen.getByTestId("wizard-input-url")).toBeInTheDocument();
  });

  it("shows 'Proje Bilgileri' in step indicator", async () => {
    const { default: Page } = await import(
      "../(dashboard)/p/[projectId]/wizard/page"
    );
    render(<Page />);
    // Step 1: "Proje Bilgileri" appears multiple times (step 1 in indicator + step content)
    expect(screen.getAllByText("Proje Bilgileri").length).toBeGreaterThanOrEqual(1);
  });
});
