/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

// ─── Standard mocks ─────────────────────────────────────────────────────────

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

jest.mock("@/lib/api-client", () => ({
  apiFetch: jest.fn(),
  ENGINE_BASE: "http://localhost:5001",
}));

// nexus barrel
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
  StatusBadge: ({ status }: any) => (
    <span data-testid={`status-${status}`}>{status}</span>
  ),
  FilterBar: ({ children }: any) => <div>{children}</div>,
}));

// nexus individual component mocks
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

// dnd-kit mocks (needed by ApiTestsPage)
jest.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: any) => <div>{children}</div>,
  closestCenter: jest.fn(),
  KeyboardSensor: jest.fn(),
  PointerSensor: jest.fn(),
  useSensor: jest.fn(),
  useSensors: jest.fn(() => []),
  DragOverlay: ({ children }: any) => <div>{children}</div>,
}));

jest.mock("@dnd-kit/sortable", () => ({
  SortableContext: ({ children }: any) => <div>{children}</div>,
  sortableKeyboardCoordinates: jest.fn(),
  verticalListSortingStrategy: "vertical",
  arrayMove: jest.fn((arr: any[]) => arr),
  useSortable: jest.fn(() => ({
    attributes: {},
    listeners: {},
    setNodeRef: jest.fn(),
    transform: null,
    transition: undefined,
    isDragging: false,
  })),
}));

jest.mock("@dnd-kit/utilities", () => ({
  CSS: { Transform: { toString: jest.fn(() => "") } },
}));

// @tanstack/react-query mock
jest.mock("@tanstack/react-query", () => ({
  useMutation: jest.fn(() => ({
    mutateAsync: jest.fn(),
    isPending: false,
    isError: false,
  })),
}));

// ─── Imports ─────────────────────────────────────────────────────────────────

import QAOrchestratorPage from "@/app/(dashboard)/p/[projectId]/qa-orchestrator/page";
import ApiTestsPage from "@/app/(dashboard)/p/[projectId]/api-tests/page";
import { apiFetch as apiFetchFromApi } from "@/lib/api";

const apiFetch = apiFetchFromApi as jest.Mock;

// ─── QAOrchestratorPage ──────────────────────────────────────────────────────

describe("QAOrchestratorPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the page root element", () => {
    render(<QAOrchestratorPage />);
    expect(screen.getByTestId("qa-orchestrator-page")).toBeInTheDocument();
  });

  it("renders PageHeader with correct title", () => {
    render(<QAOrchestratorPage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("QA Orkestratör");
  });

  it("renders the goal input area with placeholder text", () => {
    render(<QAOrchestratorPage />);
    const input = screen.getByPlaceholderText(/Ödeme API'leri/i);
    expect(input).toBeInTheDocument();
  });

  it("renders all four preset goal buttons", () => {
    render(<QAOrchestratorPage />);
    expect(screen.getByText("Kapsam Artır")).toBeInTheDocument();
    expect(screen.getByText("Güvenlik Tarama")).toBeInTheDocument();
    expect(screen.getByText("Flaky Temizle")).toBeInTheDocument();
    expect(screen.getByText("Tam Döngü")).toBeInTheDocument();
  });

  it("shows empty state when no cycle has run", () => {
    render(<QAOrchestratorPage />);
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Otonom QA Döngüsü");
  });

  it("run button is disabled when goal input is empty", () => {
    render(<QAOrchestratorPage />);
    const runButton = screen.getByRole("button", { name: /Çalıştır/i });
    expect(runButton).toBeDisabled();
  });

  it("run button becomes enabled after typing a goal", () => {
    render(<QAOrchestratorPage />);
    const input = screen.getByPlaceholderText(/Ödeme API'leri/i);
    fireEvent.change(input, { target: { value: "Tüm endpoint testlerini çalıştır" } });
    const runButton = screen.getByRole("button", { name: /Çalıştır/i });
    expect(runButton).not.toBeDisabled();
  });
});

// ─── ApiTestsPage ────────────────────────────────────────────────────────────

describe("ApiTestsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default: return empty arrays for collections and runs
    apiFetch.mockResolvedValue([]);
  });

  it("renders the page root element", async () => {
    await act(async () => {
      render(<ApiTestsPage />);
    });
    expect(screen.getByTestId("api-tests-page")).toBeInTheDocument();
  });

  it("renders PageHeader with correct title", async () => {
    await act(async () => {
      render(<ApiTestsPage />);
    });
    expect(screen.getByTestId("page-header")).toHaveTextContent("API Testleri");
  });

  it("shows empty state when no collections exist", async () => {
    apiFetch.mockResolvedValue([]);
    await act(async () => {
      render(<ApiTestsPage />);
    });
    await waitFor(() => {
      const emptyStates = screen.getAllByTestId("empty-state");
      const collectionEmpty = emptyStates.find((el) =>
        el.textContent?.includes("Koleksiyon yok")
      );
      expect(collectionEmpty).toBeInTheDocument();
    });
  });

  it("renders collection list when collections are loaded", async () => {
    const mockCollections = [
      { id: "c1", name: "Auth Endpoints", base_url: "http://localhost:3000" },
      { id: "c2", name: "Payment Flow", base_url: "http://localhost:4000" },
    ];
    apiFetch.mockImplementation((url: string) => {
      if (url.includes("/collections") && !url.includes("/requests") && !url.includes("/run")) {
        return Promise.resolve(mockCollections);
      }
      return Promise.resolve([]);
    });

    await act(async () => {
      render(<ApiTestsPage />);
    });

    await waitFor(() => {
      expect(screen.getByText("Auth Endpoints")).toBeInTheDocument();
    });
    expect(screen.getByText("Payment Flow")).toBeInTheDocument();
  });

  it("renders ServiceTestingGuide and FlowGuideCard", async () => {
    await act(async () => {
      render(<ApiTestsPage />);
    });
    expect(screen.getByTestId("service-testing-guide")).toBeInTheDocument();
    expect(screen.getByTestId("flow-guide-card")).toBeInTheDocument();
  });

  it("shows create collection form when + Yeni button is clicked", async () => {
    await act(async () => {
      render(<ApiTestsPage />);
    });
    const newButton = screen.getByText("+ Yeni");
    fireEvent.click(newButton);
    await waitFor(() => {
      expect(screen.getByPlaceholderText("İsim")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Base URL")).toBeInTheDocument();
    });
  });

  it("renders run results table when collection has been run", async () => {
    const mockCollections = [
      { id: "c1", name: "Auth Endpoints", base_url: "http://localhost:3000" },
    ];
    const mockRequests = [
      { id: "r1", name: "GET /users", method: "GET", path: "/users" },
    ];
    const mockRunResults = {
      results: [
        { name: "GET /users", status_code: 200, passed: true, duration_ms: 120 },
        { name: "POST /login", status_code: 401, passed: false, duration_ms: 88 },
      ],
    };

    apiFetch.mockImplementation((url: string) => {
      if (url.includes("/requests") && !url.includes("method")) {
        return Promise.resolve(mockRequests);
      }
      if (url.endsWith("/collections")) return Promise.resolve(mockCollections);
      if (url.includes("/run")) return Promise.resolve(mockRunResults);
      return Promise.resolve([]);
    });

    await act(async () => {
      render(<ApiTestsPage />);
    });

    // Wait for collections to load, then select one
    await waitFor(() => screen.getByText("Auth Endpoints"));
    await act(async () => {
      fireEvent.click(screen.getByText("Auth Endpoints"));
    });

    // Wait for requests to load (so run button is enabled)
    await waitFor(() => {
      const runBtn = screen.getByTestId("api-tests-btn-run");
      expect(runBtn).not.toBeDisabled();
    });

    // Run the collection
    await act(async () => {
      fireEvent.click(screen.getByTestId("api-tests-btn-run"));
    });

    await waitFor(() => {
      // "GET /users" appears in both the requests table and run results table
      expect(screen.getAllByText("GET /users").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("POST /login")).toBeInTheDocument();
    });
  });
});
