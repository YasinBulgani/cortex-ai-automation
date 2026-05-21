/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor, act } from "@testing-library/react";

// ─── next/link ────────────────────────────────────────────────────────────────
jest.mock("next/link", () => {
  function MockLink({ href, children, ...rest }: { href: string; children: React.ReactNode; [key: string]: unknown }) {
    return <a href={href} {...rest}>{children}</a>;
  }
  MockLink.displayName = "MockLink";
  return MockLink;
});

// ─── @/lib/use-route-param ────────────────────────────────────────────────────
jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn((key: string) => (key === "projectId" ? "proj-1" : "scen-42")),
}));

// ─── @/lib/api ────────────────────────────────────────────────────────────────
jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn(),
}));

// ─── @/components/ui/button ──────────────────────────────────────────────────
jest.mock("@/components/ui/button", () => ({
  Button: ({ children, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: string }) => (
    <button {...rest}>{children}</button>
  ),
}));

// ─── Subject under test ───────────────────────────────────────────────────────
import ScenarioDetailPage from "../(dashboard)/p/[projectId]/scenarios/[id]/page";

// ─── Fixtures ─────────────────────────────────────────────────────────────────
const SCENARIO_FIXTURE = {
  id: "scen-42",
  title: "Login Akışı",
  description: "Kullanıcı giriş senaryosu",
  status: "active",
  current_version: 3,
  steps: [
    { action: "navigate", url: "https://example.com/login" },
    { action: "click", selector: "#submit" },
  ],
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
function getApiFetch() {
  const { apiFetch } = jest.requireMock("@/lib/api");
  return apiFetch as jest.Mock;
}

async function renderLoaded(fixture = SCENARIO_FIXTURE) {
  getApiFetch().mockResolvedValue(fixture);
  let result!: ReturnType<typeof render>;
  await act(async () => {
    result = render(<ScenarioDetailPage />);
    await Promise.resolve();
  });
  return result;
}

// ─── Tests ────────────────────────────────────────────────────────────────────
describe("ScenarioDetailPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, "error").mockImplementation(() => {});
    jest.spyOn(console, "warn").mockImplementation(() => {});
  });

  afterEach(() => {
    (console.error as jest.Mock).mockRestore();
    (console.warn as jest.Mock).mockRestore();
  });

  // 1. Shows loading state before data resolves
  it("shows loading state 'Yükleniyor…' before data resolves", () => {
    getApiFetch().mockReturnValue(new Promise(() => {})); // never resolves

    render(<ScenarioDetailPage />);

    expect(screen.getByText(/Yükleniyor/)).toBeInTheDocument();
  });

  // 2. apiFetch called with correct URL on mount
  it("calls apiFetch with the correct URL on mount", async () => {
    await renderLoaded();

    expect(getApiFetch()).toHaveBeenCalledWith(
      "/api/v1/tspm/projects/proj-1/scenarios/scen-42"
    );
  });

  // 3. Renders scenario-detail-page container after load
  it("renders the scenario-detail-page container after data loads", async () => {
    await renderLoaded();

    expect(screen.getByTestId("scenario-detail-page")).toBeInTheDocument();
  });

  // 4. Renders scenario title in heading
  it("renders the scenario title in the heading", async () => {
    await renderLoaded();

    const heading = screen.getByTestId("scenario-detail-heading");
    expect(heading).toBeInTheDocument();
    expect(heading).toHaveTextContent("Login Akışı");
  });

  // 5. Renders scenario description
  it("renders the scenario description when present", async () => {
    await renderLoaded();

    expect(screen.getByText("Kullanıcı giriş senaryosu")).toBeInTheDocument();
  });

  // 6. Shows "—" when description is empty
  it("shows '—' when description is empty string", async () => {
    await renderLoaded({ ...SCENARIO_FIXTURE, description: "" });

    expect(screen.getByText("—")).toBeInTheDocument();
  });

  // 7. Shows status and version metadata
  it("shows status and version metadata", async () => {
    await renderLoaded();

    expect(screen.getByText(/Durum:.*active.*Sürüm:.*3/)).toBeInTheDocument();
  });

  // 8. Renders "Adımlar" section heading
  it("renders the 'Adımlar' section heading", async () => {
    await renderLoaded();

    expect(screen.getByText("Adımlar")).toBeInTheDocument();
  });

  // 9. Shows "Adım yok" when steps array is empty
  it("shows 'Adım yok' when the steps array is empty", async () => {
    await renderLoaded({ ...SCENARIO_FIXTURE, steps: [] });

    expect(screen.getByText("Adım yok")).toBeInTheDocument();
  });

  // 10. Renders step content when steps exist
  it("renders JSON-stringified step content when steps exist", async () => {
    await renderLoaded();

    // Each step is JSON.stringify-ed and rendered in a <pre> block.
    // Use exact:false so whitespace normalization doesn't interfere with newlines.
    expect(
      screen.getByText((content) => content.includes('"action"') && content.includes('"navigate"'))
    ).toBeInTheDocument();
  });

  // 11. Edit button is present
  it("renders the edit button with correct testid and href", async () => {
    await renderLoaded();

    const editBtn = screen.getByTestId("scenario-detail-btn-edit");
    expect(editBtn).toBeInTheDocument();

    // The surrounding <a> (from MockLink) should point to the edit URL
    const link = editBtn.closest("a");
    expect(link).toHaveAttribute("href", "/p/proj-1/scenarios/edit/scen-42");
  });

  // 12. Back button is present
  it("renders the back button with correct testid and href pointing to scenario list", async () => {
    await renderLoaded();

    const backBtn = screen.getByTestId("scenario-detail-btn-back");
    expect(backBtn).toBeInTheDocument();

    const link = backBtn.closest("a");
    expect(link).toHaveAttribute("href", "/p/proj-1/scenarios");
  });
});
