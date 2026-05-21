/** @jest-environment jsdom */

import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => "/p/proj-1",
}));

jest.mock("next/link", () => {
  return function MockLink({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) {
    return (
      <a href={href} {...rest}>
        {children}
      </a>
    );
  };
});

jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

const mockApiFetch = jest.fn();
jest.mock("@/lib/api", () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
}));

jest.mock("@/components/ui/button", () => ({
  Button: ({
    children,
    ...rest
  }: {
    children: React.ReactNode;
    [key: string]: unknown;
  }) => <button {...rest}>{children}</button>,
}));

jest.mock("@/components/ui/input", () => ({
  Input: ({ ...rest }: Record<string, unknown>) => <input {...rest} />,
}));

// ── Component import (after mocks) ────────────────────────────────────────────

import NewExecutionPage from "@/app/(dashboard)/p/[projectId]/executions/new/page";

// ── Helpers ───────────────────────────────────────────────────────────────────

const SCENARIOS = [
  { id: "sc-1", title: "Login flow", status: "active" },
  { id: "sc-2", title: "Checkout flow", status: "draft" },
];

function renderPage() {
  return render(<NewExecutionPage />);
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks();
  // Default: resolve with an empty scenario list
  mockApiFetch.mockResolvedValue([]);
  jest.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
  (console.error as jest.Mock).mockRestore();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("NewExecutionPage", () => {
  // 1. Root container renders
  it("renders the page container", async () => {
    await act(async () => {
      renderPage();
    });
    expect(screen.getByTestId("new-execution-page")).toBeInTheDocument();
  });

  // 2. Heading text
  it('renders the heading "Yeni execution"', async () => {
    await act(async () => {
      renderPage();
    });
    expect(screen.getByTestId("new-execution-heading")).toHaveTextContent(
      "Yeni execution"
    );
  });

  // 3. Form renders
  it("renders the form", async () => {
    await act(async () => {
      renderPage();
    });
    expect(screen.getByTestId("new-execution-form")).toBeInTheDocument();
  });

  // 4. Name input renders
  it("renders the name input", async () => {
    await act(async () => {
      renderPage();
    });
    expect(screen.getByTestId("execution-input-name")).toBeInTheDocument();
  });

  // 5. Empty state when no scenarios
  it('shows empty state "Önce senaryo oluşturun." when no scenarios are loaded', async () => {
    mockApiFetch.mockResolvedValue([]);
    await act(async () => {
      renderPage();
    });
    await waitFor(() => {
      expect(screen.getByTestId("execution-empty-scenarios")).toBeInTheDocument();
    });
    expect(screen.getByTestId("execution-empty-scenarios")).toHaveTextContent(
      "Önce senaryo oluşturun."
    );
  });

  // 6. Loaded scenarios render checkboxes
  it("shows loaded scenario checkboxes after apiFetch resolves", async () => {
    mockApiFetch.mockResolvedValue(SCENARIOS);
    await act(async () => {
      renderPage();
    });
    await waitFor(() => {
      expect(
        screen.getByTestId("execution-check-scenario-sc-1")
      ).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("execution-check-scenario-sc-2")
    ).toBeInTheDocument();
  });

  // 7. Checkbox toggles selection state
  it("toggles checkbox selection when clicked", async () => {
    mockApiFetch.mockResolvedValue(SCENARIOS);
    await act(async () => {
      renderPage();
    });
    await waitFor(() => {
      expect(
        screen.getByTestId("execution-check-scenario-sc-1")
      ).toBeInTheDocument();
    });

    const checkbox = screen.getByTestId(
      "execution-check-scenario-sc-1"
    ) as HTMLInputElement;
    expect(checkbox.checked).toBe(false);

    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(true);

    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(false);
  });

  // 8. Submit without selecting scenarios shows error
  it('shows error "En az bir senaryo seçin." when submitting without selecting a scenario', async () => {
    mockApiFetch.mockResolvedValue([]);
    await act(async () => {
      renderPage();
    });

    const form = screen.getByTestId("new-execution-form");
    await act(async () => {
      fireEvent.submit(form);
    });

    expect(screen.getByTestId("execution-alert-error")).toHaveTextContent(
      "En az bir senaryo seçin."
    );
  });

  // 9. Submit button default text
  it('submit button shows "Koşuyu oluştur"', async () => {
    await act(async () => {
      renderPage();
    });
    expect(screen.getByTestId("execution-btn-start")).toHaveTextContent(
      "Koşuyu oluştur"
    );
  });

  // 10. apiFetch called on mount to load scenarios
  it("calls apiFetch on mount to load scenarios", async () => {
    await act(async () => {
      renderPage();
    });
    expect(mockApiFetch).toHaveBeenCalledWith(
      "/api/v1/tspm/projects/proj-1/scenarios"
    );
  });

  // 11. Scenario title and status are rendered
  it("renders scenario title and status", async () => {
    mockApiFetch.mockResolvedValue(SCENARIOS);
    await act(async () => {
      renderPage();
    });
    await waitFor(() => {
      expect(screen.getByText("Login flow")).toBeInTheDocument();
    });
    expect(screen.getByText("active")).toBeInTheDocument();
    expect(screen.getByText("Checkout flow")).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
  });

  // 12. Name input is editable
  it("allows typing in the name input", async () => {
    await act(async () => {
      renderPage();
    });
    const input = screen.getByTestId("execution-input-name") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Sprint 12 regresyon" } });
    expect(input.value).toBe("Sprint 12 regresyon");
  });

  // 13. Successful submit calls router.push with correct path
  it("calls router.push with the correct path on successful submit", async () => {
    mockApiFetch
      .mockResolvedValueOnce(SCENARIOS) // load scenarios
      .mockResolvedValueOnce({ id: "exec-99" }); // create execution

    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      expect(
        screen.getByTestId("execution-check-scenario-sc-1")
      ).toBeInTheDocument();
    });

    // Select a scenario
    fireEvent.click(screen.getByTestId("execution-check-scenario-sc-1"));

    // Submit the form
    await act(async () => {
      fireEvent.submit(screen.getByTestId("new-execution-form"));
    });

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/p/proj-1/executions/exec-99");
    });
  });

  // 14. API error shown in error element
  it("displays API error message when the create call fails", async () => {
    mockApiFetch
      .mockResolvedValueOnce(SCENARIOS) // load scenarios
      .mockRejectedValueOnce(new Error("Sunucu hatası")); // create fails

    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      expect(
        screen.getByTestId("execution-check-scenario-sc-1")
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("execution-check-scenario-sc-1"));

    await act(async () => {
      fireEvent.submit(screen.getByTestId("new-execution-form"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("execution-alert-error")).toHaveTextContent(
        "Sunucu hatası"
      );
    });
  });

  // 15. Submit button is disabled while saving
  it("disables the submit button while saving", async () => {
    // Never resolves so we can assert the in-progress state
    let resolveCreate!: (value: { id: string }) => void;
    const pendingCreate = new Promise<{ id: string }>((res) => {
      resolveCreate = res;
    });

    mockApiFetch
      .mockResolvedValueOnce(SCENARIOS) // load scenarios
      .mockReturnValueOnce(pendingCreate); // create hangs

    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      expect(
        screen.getByTestId("execution-check-scenario-sc-1")
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("execution-check-scenario-sc-1"));

    act(() => {
      fireEvent.submit(screen.getByTestId("new-execution-form"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("execution-btn-start")).toBeDisabled();
    });

    // Cleanup: resolve the pending promise so React state settles
    await act(async () => {
      resolveCreate({ id: "exec-1" });
    });
  });
});
