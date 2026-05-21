/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

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
  useRouteParam: jest.fn((key: string) =>
    key === "projectId" ? "proj-1" : "scen-1"
  ),
}));

const mockApiFetch = jest.fn();
jest.mock("@/lib/api", () => ({ apiFetch: (...args: any[]) => mockApiFetch(...args) }));

jest.mock("@/components/ui/button", () => ({
  Button: ({ children, ...rest }: any) => <button {...rest}>{children}</button>,
}));

jest.mock("@/components/ui/input", () => ({
  Input: (props: any) => <input {...props} />,
}));

jest.mock("@/components/ui/badge", () => ({
  Badge: ({ children }: any) => <span data-testid="badge">{children}</span>,
}));

// ─── Suppress noisy console output ───────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks();
  // Default: apiFetch resolves with empty arrays / objects
  mockApiFetch.mockResolvedValue([]);
  jest.spyOn(console, "error").mockImplementation(() => {});
  jest.spyOn(console, "warn").mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

// ─── Lazy imports after mocks are in place ────────────────────────────────────

const getVersionsPage = () =>
  require("@/app/(dashboard)/p/[projectId]/scenarios/[id]/versions/page").default;

const getEditPage = () =>
  require("@/app/(dashboard)/p/[projectId]/scenarios/edit/[id]/page").default;

// ═════════════════════════════════════════════════════════════════════════════
// ScenarioVersionsPage
// ═════════════════════════════════════════════════════════════════════════════

describe("ScenarioVersionsPage", () => {
  it("renders the page heading and back-link", async () => {
    const ScenarioVersionsPage = getVersionsPage();
    await act(async () => {
      render(<ScenarioVersionsPage />);
    });

    expect(screen.getByTestId("versions-heading")).toHaveTextContent("Sürüm Geçmişi");
    expect(screen.getByTestId("versions-btn-back")).toBeInTheDocument();
  });

  it("back link points to the correct scenario URL", async () => {
    const ScenarioVersionsPage = getVersionsPage();
    await act(async () => {
      render(<ScenarioVersionsPage />);
    });

    const backLink = screen.getByTestId("versions-btn-back").closest("a");
    expect(backLink).toHaveAttribute("href", "/p/proj-1/scenarios/scen-1");
  });

  it("shows 'Sürüm bulunamadı' when versions list is empty", async () => {
    mockApiFetch.mockResolvedValue([]);
    const ScenarioVersionsPage = getVersionsPage();

    await act(async () => {
      render(<ScenarioVersionsPage />);
    });

    expect(screen.getByText("Sürüm bulunamadı.")).toBeInTheDocument();
  });

  it("renders version cards when API returns versions", async () => {
    const versions = [
      { id: "v-1", version_number: 1, title: "İlk versiyon", status: "active", created_at: "2026-01-01T10:00:00Z" },
      { id: "v-2", version_number: 2, title: "İkinci versiyon", status: "draft", created_at: "2026-02-01T10:00:00Z" },
    ];
    mockApiFetch.mockResolvedValue(versions);
    const ScenarioVersionsPage = getVersionsPage();

    await act(async () => {
      render(<ScenarioVersionsPage />);
    });

    expect(screen.getByText("v1")).toBeInTheDocument();
    expect(screen.getByText("v2")).toBeInTheDocument();
    expect(screen.getByText("İlk versiyon")).toBeInTheDocument();
    expect(screen.getByText("İkinci versiyon")).toBeInTheDocument();
  });

  it("compare button is disabled when fewer than two versions are selected", async () => {
    mockApiFetch.mockResolvedValue([]);
    const ScenarioVersionsPage = getVersionsPage();

    await act(async () => {
      render(<ScenarioVersionsPage />);
    });

    expect(screen.getByTestId("versions-btn-compare")).toBeDisabled();
  });

  it("selecting two versions enables the compare button", async () => {
    const versions = [
      { id: "v-1", version_number: 1, title: "V1", status: "active", created_at: null },
      { id: "v-2", version_number: 2, title: "V2", status: "draft", created_at: null },
    ];
    // First call: load versions list; subsequent calls: diff
    mockApiFetch.mockResolvedValue(versions);
    const ScenarioVersionsPage = getVersionsPage();

    await act(async () => {
      render(<ScenarioVersionsPage />);
    });

    const versionButtons = screen.getAllByRole("button", { name: /v[12]/i });
    await act(async () => { fireEvent.click(versionButtons[0]); });
    await act(async () => { fireEvent.click(versionButtons[1]); });

    expect(screen.getByTestId("versions-btn-compare")).not.toBeDisabled();
  });

  it("clicking compare calls apiFetch with diff endpoint", async () => {
    const versions = [
      { id: "v-1", version_number: 1, title: "V1", status: "active", created_at: null },
      { id: "v-2", version_number: 2, title: "V2", status: "draft", created_at: null },
    ];
    mockApiFetch
      .mockResolvedValueOnce(versions)   // initial load
      .mockResolvedValueOnce([]);        // diff result (empty diff)

    const ScenarioVersionsPage = getVersionsPage();

    await act(async () => {
      render(<ScenarioVersionsPage />);
    });

    const versionButtons = screen.getAllByRole("button", { name: /v[12]/i });
    await act(async () => { fireEvent.click(versionButtons[0]); });
    await act(async () => { fireEvent.click(versionButtons[1]); });

    await act(async () => {
      fireEvent.click(screen.getByTestId("versions-btn-compare"));
    });

    expect(mockApiFetch).toHaveBeenCalledWith(
      expect.stringContaining("/versions/")
    );
    expect(mockApiFetch).toHaveBeenCalledWith(
      expect.stringContaining("/diff/")
    );
  });

  it("shows 'fark bulunamadı' message when diff is empty", async () => {
    const versions = [
      { id: "v-1", version_number: 1, title: "V1", status: "active", created_at: null },
      { id: "v-2", version_number: 2, title: "V2", status: "draft", created_at: null },
    ];
    mockApiFetch
      .mockResolvedValueOnce(versions)
      .mockResolvedValueOnce([]);

    const ScenarioVersionsPage = getVersionsPage();

    await act(async () => {
      render(<ScenarioVersionsPage />);
    });

    const versionButtons = screen.getAllByRole("button", { name: /v[12]/i });
    await act(async () => { fireEvent.click(versionButtons[0]); });
    await act(async () => { fireEvent.click(versionButtons[1]); });

    await act(async () => {
      fireEvent.click(screen.getByTestId("versions-btn-compare"));
    });

    expect(screen.getByText(/İki sürüm arasında fark bulunamadı/)).toBeInTheDocument();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// EditScenarioPage
// ═════════════════════════════════════════════════════════════════════════════

describe("EditScenarioPage", () => {
  const mockDetail = {
    id: "scen-1",
    title: "Mevcut Senaryo",
    description: "Açıklama metni",
    status: "draft",
    steps: [{ id: 0, keyword: "Given", text: "kullanıcı giriş yapar" }],
    data_bindings: [],
  };

  it("renders the edit page heading and form", async () => {
    mockApiFetch.mockResolvedValue(mockDetail);
    const EditScenarioPage = getEditPage();

    await act(async () => {
      render(<EditScenarioPage />);
    });

    expect(screen.getByTestId("scenario-edit-heading")).toHaveTextContent("Senaryo düzenle");
    expect(screen.getByTestId("scenario-edit-form")).toBeInTheDocument();
  });

  it("loads and pre-fills title field from API", async () => {
    mockApiFetch.mockResolvedValue(mockDetail);
    const EditScenarioPage = getEditPage();

    await act(async () => {
      render(<EditScenarioPage />);
    });

    await waitFor(() => {
      expect((screen.getByTestId("scenario-edit-input-title") as HTMLInputElement).value).toBe(
        "Mevcut Senaryo"
      );
    });
  });

  it("loads and pre-fills status select from API", async () => {
    mockApiFetch.mockResolvedValue({ ...mockDetail, status: "active" });
    const EditScenarioPage = getEditPage();

    await act(async () => {
      render(<EditScenarioPage />);
    });

    await waitFor(() => {
      expect((screen.getByTestId("scenario-edit-select-status") as HTMLSelectElement).value).toBe("active");
    });
  });

  it("renders all STATUS_OPTIONS in the select dropdown", async () => {
    mockApiFetch.mockResolvedValue(mockDetail);
    const EditScenarioPage = getEditPage();

    await act(async () => {
      render(<EditScenarioPage />);
    });

    const select = screen.getByTestId("scenario-edit-select-status") as HTMLSelectElement;
    const options = Array.from(select.options).map((o) => o.value);
    expect(options).toEqual(expect.arrayContaining(["draft", "active", "deprecated", "review"]));
  });

  it("save button is present and submittable", async () => {
    mockApiFetch.mockResolvedValue(mockDetail);
    const EditScenarioPage = getEditPage();

    await act(async () => {
      render(<EditScenarioPage />);
    });

    expect(screen.getByTestId("scenario-edit-btn-save")).toBeInTheDocument();
  });

  it("shows validation error when submitting with no steps", async () => {
    // Return scenario with empty steps
    mockApiFetch.mockResolvedValue({ ...mockDetail, steps: [] });
    const EditScenarioPage = getEditPage();

    await act(async () => {
      render(<EditScenarioPage />);
    });

    await act(async () => {
      fireEvent.submit(screen.getByTestId("scenario-edit-form"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("scenario-edit-error")).toHaveTextContent(
        "En az bir adım gerekli"
      );
    });
  });
});
