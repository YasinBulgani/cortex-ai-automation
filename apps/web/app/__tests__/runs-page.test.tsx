/** @jest-environment jsdom */

import React from "react";
import { render, screen, waitFor, act, fireEvent } from "@testing-library/react";

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
  ENGINE_BASE: "http://localhost:5001",
  apiFetch: jest.fn(),
}));

jest.mock("@/lib/provenance", () => ({
  normalizeProvenance: jest.fn(() => "manual"),
  provenanceBadgeClass: jest.fn(() => "text-slate-400"),
  provenanceLabel: jest.fn(() => "Manual"),
}));

jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title }: any) => <div data-testid="page-header">{title}</div>,
  StatCard: ({ label, value }: any) => <div data-testid={`stat-${label}`}>{value}</div>,
  StatusBadge: ({ status }: any) => <span data-testid={`status-badge-${status}`}>{status}</span>,
  SectionCard: ({ title, children }: any) => <div data-testid={`section-${title}`}>{children}</div>,
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
  MetricRow: ({ children }: any) => <div>{children}</div>,
  ToolbarActions: ({ children }: any) => <div>{children}</div>,
}));

jest.mock("@/components/ui/tabs", () => ({
  Tabs: ({ children }: any) => <div>{children}</div>,
  TabsList: ({ children }: any) => <div>{children}</div>,
  TabsTrigger: ({ children, value }: any) => (
    <button data-testid={`tab-${value}`}>{children}</button>
  ),
}));

import RunsPage from "../(dashboard)/p/[projectId]/runs/page";

const SAMPLE_RUN = {
  id: 1,
  test_title: "Login Test",
  status: "passed",
  started_at: "2024-01-01T10:00:00Z",
  ended_at: "2024-01-01T10:01:00Z",
  allure_path: "",
  feature_path: "features/login.feature",
};

function mockFetchEmpty() {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ runs: [] }),
  } as any);
}

function mockFetchWithRuns(runs = [SAMPLE_RUN]) {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ runs }),
  } as any);
}

function mockFetchError() {
  global.fetch = jest.fn().mockResolvedValue({
    ok: false,
    status: 500,
  } as any);
}

class MockEventSource {
  static instances: MockEventSource[] = [];
  onmessage: ((ev: any) => void) | null = null;
  onerror: (() => void) | null = null;
  close = jest.fn();

  constructor(public url: string) {
    MockEventSource.instances.push(this);
  }
}

beforeEach(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  MockEventSource.instances = [];
  global.EventSource = MockEventSource as any;
});

afterEach(() => {
  jest.restoreAllMocks();
});

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("RunsPage", () => {
  test("1. renders the page container with data-testid=runs-page", async () => {
    mockFetchEmpty();
    await act(async () => {
      render(<RunsPage />);
    });
    expect(screen.getByTestId("runs-page")).toBeInTheDocument();
  });

  test("2. renders PageHeader with title 'Test Koşuları (Engine)'", async () => {
    mockFetchEmpty();
    await act(async () => {
      render(<RunsPage />);
    });
    expect(screen.getByTestId("page-header")).toHaveTextContent(
      "Test Koşuları (Engine)"
    );
  });

  test("3. shows loading state while fetch is pending", async () => {
    // Never resolve so loading stays true
    global.fetch = jest.fn().mockReturnValue(new Promise(() => {}));
    render(<RunsPage />);
    expect(screen.getByText("Yükleniyor...")).toBeInTheDocument();
  });

  test("4. shows empty state when runs array is empty", async () => {
    mockFetchEmpty();
    await act(async () => {
      render(<RunsPage />);
    });
    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    });
  });

  test("5. shows error EmptyState when fetch fails", async () => {
    mockFetchError();
    await act(async () => {
      render(<RunsPage />);
    });
    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    });
    expect(screen.getByTestId("empty-state")).toHaveTextContent(
      "Engine bağlantısı kurulamadı"
    );
  });

  test("6. renders run rows when data loads with runs", async () => {
    mockFetchWithRuns();
    await act(async () => {
      render(<RunsPage />);
    });
    await waitFor(() => {
      expect(screen.getByText("Login Test")).toBeInTheDocument();
    });
    expect(screen.getByText("features/login.feature")).toBeInTheDocument();
  });

  test("7. shows run status badge", async () => {
    mockFetchWithRuns();
    await act(async () => {
      render(<RunsPage />);
    });
    await waitFor(() => {
      expect(screen.getByTestId("status-badge-passed")).toBeInTheDocument();
    });
  });

  test("8. Toplam Koşu stat shows correct count", async () => {
    mockFetchWithRuns([SAMPLE_RUN, { ...SAMPLE_RUN, id: 2, test_title: "Signup Test" }]);
    await act(async () => {
      render(<RunsPage />);
    });
    await waitFor(() => {
      const stat = screen.getByTestId("stat-Toplam Koşu");
      expect(stat).toHaveTextContent("2");
    });
  });

  test("9. shows 'Henüz koşu yok' empty state title", async () => {
    mockFetchEmpty();
    await act(async () => {
      render(<RunsPage />);
    });
    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toHaveTextContent("Henüz koşu yok");
    });
  });

  test("10. Koşu Başlat button is disabled when feature path is empty", async () => {
    mockFetchEmpty();
    await act(async () => {
      render(<RunsPage />);
    });
    const startBtn = screen.getByRole("button", { name: /Koşu Başlat/i });
    expect(startBtn).toBeDisabled();
  });

  test("11. Koşu Başlat button enables when feature path is entered", async () => {
    mockFetchEmpty();
    await act(async () => {
      render(<RunsPage />);
    });
    const input = screen.getByPlaceholderText(
      "features/login.feature veya klasör yolu"
    );
    await act(async () => {
      fireEvent.change(input, { target: { value: "features/login.feature" } });
    });
    const startBtn = screen.getByRole("button", { name: /Koşu Başlat/i });
    expect(startBtn).not.toBeDisabled();
  });

  test("12. browser tabs (chromium, firefox, webkit) are rendered", async () => {
    mockFetchEmpty();
    await act(async () => {
      render(<RunsPage />);
    });
    expect(screen.getByTestId("tab-chromium")).toBeInTheDocument();
    expect(screen.getByTestId("tab-firefox")).toBeInTheDocument();
    expect(screen.getByTestId("tab-webkit")).toBeInTheDocument();
  });
});
