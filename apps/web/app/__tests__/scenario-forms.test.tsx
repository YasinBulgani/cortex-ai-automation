/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor, act, fireEvent } from "@testing-library/react";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------
jest.mock("next/link", () =>
  function MockLink({ href, children, ...rest }: any) {
    return <a href={href} {...rest}>{children}</a>;
  },
);

const mockRouterPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockRouterPush }),
  useParams: () => ({}),
  usePathname: () => "/p/proj-1",
}));

jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

const mockApiFetch = jest.fn();
jest.mock("@/lib/api", () => ({
  apiFetch: (...args: any[]) => mockApiFetch(...args),
}));

jest.mock("@/components/ui/button", () => ({
  Button: ({ children, ...rest }: any) => <button {...rest}>{children}</button>,
}));

jest.mock("@/components/ui/input", () => ({
  Input: (props: any) => <input {...props} />,
}));

// ---------------------------------------------------------------------------
// Suppress expected console errors from React / jsdom
// ---------------------------------------------------------------------------
beforeAll(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
});

afterAll(() => {
  (console.error as jest.Mock).mockRestore();
});

// ---------------------------------------------------------------------------
// Import real components AFTER mocks are registered
// ---------------------------------------------------------------------------
import NewScenarioPage from "../(dashboard)/p/[projectId]/scenarios/new/page";
import GenerateBddPage from "../(dashboard)/p/[projectId]/scenarios/generate/page";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
beforeEach(() => {
  jest.clearAllMocks();
});

// ===========================================================================
// NewScenarioPage — 10 tests
// ===========================================================================
describe("NewScenarioPage", () => {
  // 1
  it("renders data-testid='new-scenario-page'", () => {
    render(<NewScenarioPage />);
    expect(screen.getByTestId("new-scenario-page")).toBeInTheDocument();
  });

  // 2
  it("renders heading 'Yeni senaryo'", () => {
    render(<NewScenarioPage />);
    expect(screen.getByTestId("new-scenario-heading")).toHaveTextContent("Yeni senaryo");
  });

  // 3
  it("renders the form with data-testid='scenario-form'", () => {
    render(<NewScenarioPage />);
    expect(screen.getByTestId("scenario-form")).toBeInTheDocument();
  });

  // 4
  it("renders title input with data-testid='scenario-title'", () => {
    render(<NewScenarioPage />);
    expect(screen.getByTestId("scenario-title")).toBeInTheDocument();
  });

  // 5
  it("renders save button with text 'Kaydet'", () => {
    render(<NewScenarioPage />);
    const btn = screen.getByTestId("scenario-save-btn");
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent("Kaydet");
  });

  // 6
  it("shows 'Başlık' placeholder in preview when title is empty", () => {
    render(<NewScenarioPage />);
    // The preview <p> renders {title || "Başlık"} — match by the paragraph role
    const previewParagraphs = screen.getAllByText("Başlık");
    // At least one element (the preview <p>) should contain the placeholder
    expect(previewParagraphs.length).toBeGreaterThanOrEqual(1);
    // The preview paragraph has class "mt-2 text-lg font-medium"
    const previewP = previewParagraphs.find(
      (el) => el.tagName === "P" && el.classList.contains("mt-2"),
    );
    expect(previewP).toBeInTheDocument();
  });

  // 7
  it("preview updates to show typed title", () => {
    render(<NewScenarioPage />);
    const input = screen.getByTestId("scenario-title");
    fireEvent.change(input, { target: { value: "Login akışı" } });
    expect(screen.getByText("Login akışı")).toBeInTheDocument();
  });

  // 8
  it("form submit calls apiFetch with correct URL", async () => {
    mockApiFetch.mockResolvedValue({ id: "sc-99" });
    render(<NewScenarioPage />);

    const input = screen.getByTestId("scenario-title");
    fireEvent.change(input, { target: { value: "Test başlık" } });

    await act(async () => {
      fireEvent.submit(screen.getByTestId("scenario-form"));
    });

    expect(mockApiFetch).toHaveBeenCalledWith(
      "/api/v1/tspm/projects/proj-1/scenarios",
      expect.objectContaining({ method: "POST" }),
    );
  });

  // 9
  it("calls router.push with correct path after successful submit", async () => {
    mockApiFetch.mockResolvedValue({ id: "sc-99" });
    render(<NewScenarioPage />);

    const input = screen.getByTestId("scenario-title");
    fireEvent.change(input, { target: { value: "Test başlık" } });

    await act(async () => {
      fireEvent.submit(screen.getByTestId("scenario-form"));
    });

    await waitFor(() => {
      expect(mockRouterPush).toHaveBeenCalledWith("/p/proj-1/scenarios/sc-99");
    });
  });

  // 10
  it("shows API error in data-testid='validation-error'", async () => {
    mockApiFetch.mockRejectedValue(new Error("Sunucu hatası"));
    render(<NewScenarioPage />);

    await act(async () => {
      fireEvent.submit(screen.getByTestId("scenario-form"));
    });

    await waitFor(() => {
      const errEl = screen.getByTestId("validation-error");
      expect(errEl).toBeInTheDocument();
      expect(errEl).toHaveTextContent("Sunucu hatası");
    });
  });
});

// ===========================================================================
// GenerateBddPage — 5 tests
// ===========================================================================
describe("GenerateBddPage", () => {
  // 11
  it("shows validation error when analysis text is shorter than 10 chars", async () => {
    render(<GenerateBddPage />);
    const textarea = screen.getByTestId("analysis-text");
    fireEvent.change(textarea, { target: { value: "kısa" } }); // 4 chars

    await act(async () => {
      fireEvent.click(screen.getByTestId("generate-btn-submit"));
    });

    await waitFor(() => {
      expect(
        screen.getByText("Analiz dokümanı en az 10 karakter olmalı."),
      ).toBeInTheDocument();
    });
    expect(mockApiFetch).not.toHaveBeenCalled();
  });

  // 12
  it("does NOT show short-text error when analysis text is at least 10 chars", async () => {
    mockApiFetch.mockResolvedValue({ scenarios: [] });
    render(<GenerateBddPage />);
    const textarea = screen.getByTestId("analysis-text");
    fireEvent.change(textarea, { target: { value: "Bu en az on karakterlik metin." } });

    await act(async () => {
      fireEvent.click(screen.getByTestId("generate-btn-submit"));
    });

    await waitFor(() => {
      expect(
        screen.queryByText("Analiz dokümanı en az 10 karakter olmalı."),
      ).not.toBeInTheDocument();
    });
  });

  // 13
  it("calls apiFetch when sufficient text is provided", async () => {
    const fakeScenario = {
      title: "Kullanıcı giriş yapabilmeli",
      description: "Açıklama",
      feature: "Auth",
      gherkin: "Given ...",
      tags: ["smoke"],
      steps: [{ keyword: "Given", text: "kullanıcı giriş sayfasındadır" }],
    };
    mockApiFetch.mockResolvedValue({ scenarios: [fakeScenario] });
    render(<GenerateBddPage />);

    const textarea = screen.getByTestId("analysis-text");
    fireEvent.change(textarea, { target: { value: "Yeterince uzun bir analiz dokümanı." } });

    await act(async () => {
      fireEvent.click(screen.getByTestId("generate-btn-submit"));
    });

    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith(
        "/api/v1/tspm/projects/proj-1/scenarios/generate-bdd",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  // 14 — verifies that the save button is disabled (and shows "(0)") when no scenario
  //      is selected, which is the UI-level enforcement of "En az bir senaryo seçmelisiniz."
  it("disables save button and shows 0 count when all scenarios are deselected", async () => {
    const fakeScenario = {
      title: "Login senaryosu",
      description: "Desc",
      feature: "Auth",
      gherkin: "Given ...",
      tags: [],
      steps: [],
    };
    mockApiFetch.mockResolvedValue({ scenarios: [fakeScenario] });
    render(<GenerateBddPage />);

    // Generate scenarios
    const textarea = screen.getByTestId("analysis-text");
    fireEvent.change(textarea, { target: { value: "Yeterince uzun bir analiz dokümanı metni." } });

    await act(async () => {
      fireEvent.click(screen.getByTestId("generate-btn-submit"));
    });

    await waitFor(() => {
      expect(screen.getByText("Login senaryosu")).toBeInTheDocument();
    });

    // The scenario starts selected (selectedCount=1), save button enabled
    expect(screen.getByRole("button", { name: /Seçilenleri kaydet \(1\)/i })).not.toBeDisabled();

    // Deselect the only scenario
    const checkbox = screen.getByRole("checkbox", {
      name: /Senaryo seç: Login senaryosu/i,
    });
    fireEvent.click(checkbox);

    // Save button should now show (0) and be disabled — the component enforces
    // "En az bir senaryo seçmelisiniz." by disabling the button when selectedCount === 0
    await waitFor(() => {
      const saveBtn = screen.getByRole("button", { name: /Seçilenleri kaydet \(0\)/i });
      expect(saveBtn).toBeInTheDocument();
      expect(saveBtn).toBeDisabled();
    });
  });

  // 15
  it("shows success message after successful save", async () => {
    const fakeScenario = {
      title: "Başarılı senaryo",
      description: "Desc",
      feature: "Feature",
      gherkin: "Given ...",
      tags: [],
      steps: [],
    };
    // First call = generate, second call = save
    mockApiFetch
      .mockResolvedValueOnce({ scenarios: [fakeScenario] })
      .mockResolvedValueOnce({});

    render(<GenerateBddPage />);

    const textarea = screen.getByTestId("analysis-text");
    fireEvent.change(textarea, { target: { value: "Yeterince uzun bir analiz dokümanı metni." } });

    await act(async () => {
      fireEvent.click(screen.getByTestId("generate-btn-submit"));
    });

    await waitFor(() => {
      expect(screen.getByText("Başarılı senaryo")).toBeInTheDocument();
    });

    // Scenario is selected by default (selected: true) — click save
    const saveBtn = screen.getByRole("button", { name: /Seçilenleri kaydet/i });
    await act(async () => {
      fireEvent.click(saveBtn);
    });

    await waitFor(() => {
      expect(screen.getByText(/senaryo başarıyla kaydedildi/i)).toBeInTheDocument();
    });
  });
});
