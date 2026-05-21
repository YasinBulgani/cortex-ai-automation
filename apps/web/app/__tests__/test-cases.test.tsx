/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: () => "proj-1",
}));

jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn(),
}));

jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, description, right }: any) => (
    <div data-testid="page-header">
      <h1 data-testid="page-title">{title}</h1>
      <p data-testid="page-description">{description}</p>
      {right && <div data-testid="page-header-right">{right}</div>}
    </div>
  ),
}));

import { apiFetch } from "@/lib/api";

const mockApiFetch = apiFetch as jest.Mock;

const SAMPLE_TEST_CASES = [
  {
    id: "tc-1",
    title: "Login başarılı",
    description: "Geçerli kimlik bilgileriyle giriş",
    module_name: "Auth",
    test_type: "functional",
    priority: "high",
    risk_level: "medium",
    steps: [
      { order: 1, action: "Email gir", expected: "Alan dolu" },
      { order: 2, action: "Submit", expected: "Dashboard açılır" },
    ],
    expected_result: "Kullanıcı sisteme giriş yapar",
    tags: ["login", "auth"],
    review_status: "approved",
  },
  {
    id: "tc-2",
    title: "Login başarısız",
    description: null,
    module_name: null,
    test_type: "negative",
    priority: "critical",
    risk_level: "high",
    steps: [],
    expected_result: null,
    tags: [],
    review_status: "pending",
  },
];

import TestCasesPage from "@/app/(dashboard)/p/[projectId]/test-cases/page";

describe("TestCasesPage", () => {
  beforeEach(() => {
    mockApiFetch.mockReset();
  });

  it("renders the page container", async () => {
    mockApiFetch.mockResolvedValue([]);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByTestId("test-cases-page")).toBeInTheDocument(),
    );
  });

  it("renders page title", async () => {
    mockApiFetch.mockResolvedValue([]);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByTestId("page-title")).toHaveTextContent(
        "AI Test Case Tasarimi",
      ),
    );
  });

  it("renders generate section with textarea and button", async () => {
    mockApiFetch.mockResolvedValue([]);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByTestId("generate-section")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("analysis-input")).toBeInTheDocument();
    expect(screen.getByTestId("generate-button")).toBeInTheDocument();
  });

  it("generate button is disabled when analysis textarea is empty", async () => {
    mockApiFetch.mockResolvedValue([]);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByTestId("generate-button")).toBeDisabled(),
    );
  });

  it("generate button becomes enabled when textarea has content", async () => {
    mockApiFetch.mockResolvedValue([]);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByTestId("generate-button")).toBeInTheDocument(),
    );
    await userEvent.type(screen.getByTestId("analysis-input"), "sistem analizi");
    expect(screen.getByTestId("generate-button")).not.toBeDisabled();
  });

  it("shows empty state when no test cases", async () => {
    mockApiFetch.mockResolvedValue([]);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByText(/henüz test case yok/i)).toBeInTheDocument(),
    );
  });

  it("shows loading then renders test cases", async () => {
    mockApiFetch.mockResolvedValue(SAMPLE_TEST_CASES);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByTestId("test-cases-list")).toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(screen.getByTestId("test-case-tc-1")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("test-case-tc-2")).toBeInTheDocument();
  });

  it("renders test case title and badges", async () => {
    mockApiFetch.mockResolvedValue(SAMPLE_TEST_CASES);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByText("Login başarılı")).toBeInTheDocument(),
    );
    expect(screen.getByText("Login başarısız")).toBeInTheDocument();
  });

  it("shows count and approved stats in header right when cases exist", async () => {
    mockApiFetch.mockResolvedValue(SAMPLE_TEST_CASES);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByText(/2 test case/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/1 onaylı/i)).toBeInTheDocument();
  });

  it("expands test case on click to show steps", async () => {
    mockApiFetch.mockResolvedValue(SAMPLE_TEST_CASES);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByTestId("test-case-tc-1")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("test-case-tc-1"));
    await waitFor(() =>
      expect(screen.getByText("Email gir")).toBeInTheDocument(),
    );
    expect(screen.getByText("Submit")).toBeInTheDocument();
    expect(screen.getByText(/Kullanıcı sisteme giriş yapar/)).toBeInTheDocument();
  });

  it("collapses test case on second click", async () => {
    mockApiFetch.mockResolvedValue(SAMPLE_TEST_CASES);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByTestId("test-case-tc-1")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("test-case-tc-1"));
    await waitFor(() =>
      expect(screen.getByText("Email gir")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("test-case-tc-1"));
    await waitFor(() =>
      expect(screen.queryByText("Email gir")).not.toBeInTheDocument(),
    );
  });

  it("shows tags when test case has tags", async () => {
    mockApiFetch.mockResolvedValue(SAMPLE_TEST_CASES);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByTestId("test-case-tc-1")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("test-case-tc-1"));
    await waitFor(() =>
      expect(screen.getByText("#login")).toBeInTheDocument(),
    );
    expect(screen.getByText("#auth")).toBeInTheDocument();
  });

  it("calls generate API when generate button clicked", async () => {
    mockApiFetch
      .mockResolvedValueOnce([]) // initial load
      .mockResolvedValueOnce({
        batch_id: "batch-1",
        total_generated: 1,
        test_cases: [SAMPLE_TEST_CASES[0]],
        message: "1 test case üretildi",
      });

    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByTestId("generate-button")).toBeInTheDocument(),
    );
    await userEvent.type(
      screen.getByTestId("analysis-input"),
      "kullanıcı login sistemi",
    );
    fireEvent.click(screen.getByTestId("generate-button"));

    await waitFor(() =>
      expect(screen.getByText(/1 test case üretildi/i)).toBeInTheDocument(),
    );
  });

  it("shows priority badges for each priority level", async () => {
    const cases = [
      { ...SAMPLE_TEST_CASES[0], id: "tc-crit", priority: "critical", title: "Kritik test" },
      { ...SAMPLE_TEST_CASES[0], id: "tc-low", priority: "low", title: "Düşük test" },
    ];
    mockApiFetch.mockResolvedValue(cases);
    render(<TestCasesPage />);
    await waitFor(() =>
      expect(screen.getByText("Kritik test")).toBeInTheDocument(),
    );
    // Both priority badges should appear
    expect(screen.getAllByText(/critical/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/low/i).length).toBeGreaterThan(0);
  });
});
