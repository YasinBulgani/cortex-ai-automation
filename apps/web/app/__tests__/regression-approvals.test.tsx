/** @jest-environment jsdom */

import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { apiFetch } from "@/lib/api";

/* ── Standard mocks ─────────────────────────────────────────────────────────── */
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
jest.mock("@/lib/api-client", () => ({ apiFetch: jest.fn() }));

/* ── dnd-kit mocks ───────────────────────────────────────────────────────────── */
jest.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: any) => <div>{children}</div>,
  closestCenter: jest.fn(),
  closestCorners: jest.fn(),
  KeyboardSensor: jest.fn(),
  PointerSensor: jest.fn(),
  useSensor: jest.fn(),
  useSensors: jest.fn(() => []),
  DragOverlay: ({ children }: any) => <div>{children}</div>,
  useDroppable: jest.fn(() => ({ isOver: false, setNodeRef: jest.fn() })),
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

/* ── Nexus component mocks ───────────────────────────────────────────────────── */
jest.mock("@/components/nexus", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">
      {title}
      {right && <div data-testid="page-header-right">{right}</div>}
    </div>
  ),
  StatCard: ({ label, value }: any) => (
    <div data-testid={`stat-${label}`}>{String(value)}</div>
  ),
  StatusBadge: ({ status }: any) => (
    <span data-testid={`status-${status}`}>{status}</span>
  ),
  SectionCard: ({ title, children }: any) => (
    <div>
      {title && <div>{title}</div>}
      {children}
    </div>
  ),
  EmptyState: ({ title }: any) => (
    <div data-testid="empty-state">{title}</div>
  ),
  MetricRow: ({ children }: any) => <div>{children}</div>,
  ToolbarActions: ({ children }: any) => <div>{children}</div>,
  ProgressBar: ({ value }: any) => (
    <div data-testid="progress-bar">{value}</div>
  ),
  FilterBar: ({ children }: any) => <div>{children}</div>,
}));

const mockApiFetch = apiFetch as jest.MockedFunction<typeof apiFetch>;

/* ═══════════════════════════════════════════════════════════════════════════
   REGRESSION PAGE TESTS
═══════════════════════════════════════════════════════════════════════════ */
import RegressionSetsPage from "@/app/(dashboard)/p/[projectId]/regression/page";

describe("RegressionSetsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, "error").mockImplementation(() => {});
    jest.spyOn(console, "warn").mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  /* 1. Page container renders */
  it("renders the page container", async () => {
    mockApiFetch.mockResolvedValue([]);
    await act(async () => {
      render(<RegressionSetsPage />);
    });
    expect(screen.getByTestId("regression-page")).toBeInTheDocument();
  });

  /* 2. PageHeader with correct title */
  it("renders PageHeader with title 'Regresyon Setleri'", async () => {
    mockApiFetch.mockResolvedValue([]);
    await act(async () => {
      render(<RegressionSetsPage />);
    });
    expect(screen.getByTestId("page-header")).toHaveTextContent("Regresyon Setleri");
  });

  /* 3. Loading state — fetch returns pending promise, table headers still visible */
  it("shows table headers while loading", async () => {
    mockApiFetch.mockReturnValue(new Promise(() => {}));
    render(<RegressionSetsPage />);
    expect(screen.getByText("Set Adı")).toBeInTheDocument();
    expect(screen.getByText("Senaryo")).toBeInTheDocument();
    expect(screen.getByText("Kapsam")).toBeInTheDocument();
  });

  /* 4. Empty state — no rows rendered when API returns empty array */
  it("renders no rows when API returns empty array", async () => {
    mockApiFetch.mockResolvedValue([]);
    await act(async () => {
      render(<RegressionSetsPage />);
    });
    // Zero-value stat cards for empty data
    expect(screen.getByTestId("stat-Toplam Set")).toHaveTextContent("0");
    expect(screen.getByTestId("stat-Kapsanan Senaryo")).toHaveTextContent("0");
  });

  /* 5. Data rows render when API returns items */
  it("renders regression set rows when API returns data", async () => {
    const mockRows = [
      {
        id: "set-001",
        name: "Smoke Suite",
        description: "Core smoke tests",
        scenario_count: 5,
        item_count: 5,
        created_at: "2024-01-15T00:00:00Z",
        coverage_pct: 80,
      },
      {
        id: "set-002",
        name: "Full Regression",
        description: "Complete regression",
        scenario_count: 20,
        item_count: 20,
        created_at: null,
        coverage_pct: 60,
      },
    ];
    mockApiFetch.mockResolvedValue(mockRows);
    await act(async () => {
      render(<RegressionSetsPage />);
    });
    expect(screen.getByText("Smoke Suite")).toBeInTheDocument();
    expect(screen.getByText("Full Regression")).toBeInTheDocument();
    expect(screen.getByText("5 senaryo")).toBeInTheDocument();
    expect(screen.getByText("20 senaryo")).toBeInTheDocument();
  });

  /* 6. Stat cards show correct counts from loaded data */
  it("shows stat card values from loaded data", async () => {
    const mockRows = [
      {
        id: "set-1",
        name: "Set A",
        description: "",
        scenario_count: 10,
        item_count: 10,
        created_at: null,
        coverage_pct: 50,
      },
    ];
    mockApiFetch.mockResolvedValue(mockRows);
    await act(async () => {
      render(<RegressionSetsPage />);
    });
    expect(screen.getByTestId("stat-Toplam Set")).toHaveTextContent("1");
    expect(screen.getByTestId("stat-Kapsanan Senaryo")).toHaveTextContent("10");
  });

  /* 7. Create form — input and submit button are present, input is interactive */
  it("renders create form and allows typing a name", async () => {
    mockApiFetch.mockResolvedValue([]);
    await act(async () => {
      render(<RegressionSetsPage />);
    });
    const input = screen.getByTestId("regression-input-name");
    const submitBtn = screen.getByTestId("regression-btn-create");
    expect(input).toBeInTheDocument();
    expect(submitBtn).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "My New Set" } });
    expect(input).toHaveValue("My New Set");
  });
});

/* ═══════════════════════════════════════════════════════════════════════════
   APPROVALS PAGE TESTS
═══════════════════════════════════════════════════════════════════════════ */
import ApprovalsPage from "@/app/(dashboard)/p/[projectId]/approvals/page";

describe("ApprovalsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, "error").mockImplementation(() => {});
    jest.spyOn(console, "warn").mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  /* 8. Page container renders */
  it("renders the approvals page container", async () => {
    mockApiFetch.mockResolvedValue([]);
    await act(async () => {
      render(<ApprovalsPage />);
    });
    expect(screen.getByTestId("approvals-page")).toBeInTheDocument();
  });

  /* 9. PageHeader with correct title */
  it("renders PageHeader with title 'Onay Kuyruğu'", async () => {
    mockApiFetch.mockResolvedValue([]);
    await act(async () => {
      render(<ApprovalsPage />);
    });
    expect(screen.getByTestId("page-header")).toHaveTextContent("Onay Kuyruğu");
  });

  /* 10. Loading state — page renders without crashing while fetch is pending */
  it("renders without crashing while data is loading", () => {
    mockApiFetch.mockReturnValue(new Promise(() => {}));
    render(<ApprovalsPage />);
    expect(screen.getByTestId("approvals-page")).toBeInTheDocument();
  });

  /* 11. Empty state — kanban columns render even with no items */
  it("renders kanban columns with empty drop zones when no approvals", async () => {
    mockApiFetch.mockResolvedValue([]);
    await act(async () => {
      render(<ApprovalsPage />);
    });
    expect(screen.getByTestId("kanban-column-pending")).toBeInTheDocument();
    expect(screen.getByTestId("kanban-column-approved")).toBeInTheDocument();
    expect(screen.getByTestId("kanban-column-rejected")).toBeInTheDocument();
    // All empty drop zones show placeholder text
    const placeholders = screen.getAllByText("Buraya sürükleyin");
    expect(placeholders.length).toBe(3);
  });

  /* 12. Data rows render — approval cards appear in the right columns */
  it("renders approval cards when API returns data", async () => {
    const mockApprovals = [
      {
        id: "appr-0001-0000",
        title: "Test Approval",
        source_text: "This is a test source text",
        draft_payload: null,
        status: "pending",
        scenario_id: null,
        source_batch_id: null,
        source_test_case_id: null,
        decision_note: null,
        decision_trace: {},
      },
      {
        id: "appr-0002-0000",
        title: "Approved Item",
        source_text: "Already approved item",
        draft_payload: null,
        status: "approved",
        scenario_id: null,
        source_batch_id: null,
        source_test_case_id: null,
        decision_note: null,
        decision_trace: {},
      },
    ];
    mockApiFetch.mockResolvedValue(mockApprovals);
    await act(async () => {
      render(<ApprovalsPage />);
    });
    expect(screen.getByTestId("approvals-card-appr-0001-0000")).toBeInTheDocument();
    expect(screen.getByTestId("approvals-card-appr-0002-0000")).toBeInTheDocument();
    expect(screen.getByText("Test Approval")).toBeInTheDocument();
    expect(screen.getByText("Approved Item")).toBeInTheDocument();
  });

  /* 13. Stat cards show correct pending/approved/rejected counts */
  it("shows correct stat card values for pending and approved items", async () => {
    const mockApprovals = [
      {
        id: "appr-p1",
        title: "Pending 1",
        source_text: "text",
        draft_payload: null,
        status: "pending",
        scenario_id: null,
        source_batch_id: null,
        source_test_case_id: null,
        decision_note: null,
        decision_trace: {},
      },
      {
        id: "appr-p2",
        title: "Pending 2",
        source_text: "text2",
        draft_payload: null,
        status: "pending",
        scenario_id: null,
        source_batch_id: null,
        source_test_case_id: null,
        decision_note: null,
        decision_trace: {},
      },
      {
        id: "appr-a1",
        title: "Approved",
        source_text: "approved text",
        draft_payload: null,
        status: "approved",
        scenario_id: null,
        source_batch_id: null,
        source_test_case_id: null,
        decision_note: null,
        decision_trace: {},
      },
    ];
    mockApiFetch.mockResolvedValue(mockApprovals);
    await act(async () => {
      render(<ApprovalsPage />);
    });
    expect(screen.getByTestId("stat-Bekleyen")).toHaveTextContent("2");
    expect(screen.getByTestId("stat-Onaylanan")).toHaveTextContent("1");
    expect(screen.getByTestId("stat-Reddedilen")).toHaveTextContent("0");
  });

  /* 14. Batch approve button appears when there are pending items and is clickable */
  it("shows batch approve button when pending items exist and handles click", async () => {
    const pendingApproval = {
      id: "appr-batch-01",
      title: "Batch Pending",
      source_text: "batch pending text",
      draft_payload: null,
      status: "pending",
      scenario_id: null,
      source_batch_id: null,
      source_test_case_id: null,
      decision_note: null,
      decision_trace: {},
    };
    // First call: load initial data; decide call; reload call returns empty array
    mockApiFetch
      .mockResolvedValueOnce([pendingApproval])  // initial load
      .mockResolvedValueOnce(undefined)           // decide POST
      .mockResolvedValueOnce([]);                 // reload after batch approve

    await act(async () => {
      render(<ApprovalsPage />);
    });

    const batchBtn = screen.getByTestId("approvals-btn-batch");
    expect(batchBtn).toBeInTheDocument();
    expect(batchBtn).toHaveTextContent("Tümünü Onayla (1)");

    await act(async () => {
      fireEvent.click(batchBtn);
    });
    // apiFetch should have been called for the decide endpoint
    expect(mockApiFetch).toHaveBeenCalledWith(
      expect.stringContaining("appr-batch-01/decide"),
      expect.objectContaining({ method: "POST" })
    );
  });
});
