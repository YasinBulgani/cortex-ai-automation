/**
 * Tests for SıfırBilgiPage — Zero-Knowledge AI Test Generation
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ── Mocks ────────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  useParams: () => ({ projectId: "proj-123" }),
  usePathname: () => "/p/proj-1",
}));

jest.mock("@/lib/agents-v2-api", () => ({
  startAgentRun: jest.fn(),
  getAgentRun: jest.fn(),
  subscribeAgentRun: jest.fn(),
  cancelAgentRun: jest.fn(),
  uploadSourceFile: jest.fn(),
  createAIWorkflow: jest.fn(() =>
    Promise.resolve({ workflow_id: "wf-1", status: "queued", stream_url: "/sse/wf-1" })
  ),
  getAIWorkflow: jest.fn(() =>
    Promise.resolve({ workflow_id: "wf-1", status: "completed", scenarios: [] })
  ),
  cancelAIWorkflow: jest.fn(() => Promise.resolve()),
  subscribeAIWorkflow: jest.fn((_id: string, cb: any) => {
    setTimeout(() => cb({ event_type: "completed", message: "" }), 10);
    return jest.fn();
  }),
  getAIWorkflowArtifacts: jest.fn(() =>
    Promise.resolve({ artifacts: [] })
  ),
}));

// ── Imports after mocks ───────────────────────────────────────────────────────

import SıfırBilgiPage from "@/app/(dashboard)/p/[projectId]/sifir-bilgi/page";
import {
  startAgentRun,
  getAgentRun,
  subscribeAgentRun,
  cancelAgentRun,
  uploadSourceFile,
  createAIWorkflow,
  getAIWorkflow,
  getAIWorkflowArtifacts,
} from "@/lib/agents-v2-api";

const mockStartAgentRun = startAgentRun as jest.MockedFunction<typeof startAgentRun>;
const mockGetAgentRun = getAgentRun as jest.MockedFunction<typeof getAgentRun>;
const mockSubscribeAgentRun = subscribeAgentRun as jest.MockedFunction<typeof subscribeAgentRun>;
const mockCancelAgentRun = cancelAgentRun as jest.MockedFunction<typeof cancelAgentRun>;
const mockUploadSourceFile = uploadSourceFile as jest.MockedFunction<typeof uploadSourceFile>;
const mockCreateAIWorkflow = createAIWorkflow as jest.MockedFunction<typeof createAIWorkflow>;
const mockGetAIWorkflow = getAIWorkflow as jest.MockedFunction<typeof getAIWorkflow>;
const mockGetAIWorkflowArtifacts = getAIWorkflowArtifacts as jest.MockedFunction<typeof getAIWorkflowArtifacts>;

// Default no-op subscribe returns an unsubscribe fn
const noopUnsub = jest.fn();
beforeEach(() => {
  jest.clearAllMocks();
  mockSubscribeAgentRun.mockReturnValue(noopUnsub);
});

// ── Helper ────────────────────────────────────────────────────────────────────

function renderPage() {
  return render(<SıfırBilgiPage />);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("SıfırBilgiPage", () => {
  // 1. Initial render
  it("renders the page header and source-mode buttons", () => {
    renderPage();

    expect(
      screen.getByText("Sıfır Bilgi — AI Destekli Test Üretimi"),
    ).toBeInTheDocument();

    // All 4 source-mode selection buttons
    expect(screen.getByText("URL'den")).toBeInTheDocument();
    expect(screen.getByText("Metinden")).toBeInTheDocument();
    expect(screen.getByText("Swagger")).toBeInTheDocument();
    expect(screen.getByText("Dosya")).toBeInTheDocument();
  });

  // 2. Default state: URL mode shows URL input; start button is disabled
  it("shows URL input by default and start button is disabled when URL is empty", () => {
    renderPage();

    const urlInput = screen.getByPlaceholderText(
      /https:\/\/staging\.banka-ornek/,
    );
    expect(urlInput).toBeInTheDocument();

    const startBtn = screen.getByRole("button", { name: /Pipeline'ı Başlat/ });
    expect(startBtn).toBeDisabled();
  });

  // 3. Start button becomes enabled once a URL is entered
  it("enables the start button when a URL is typed", async () => {
    renderPage();

    const urlInput = screen.getByPlaceholderText(/https:\/\/staging\.banka-ornek/);
    await userEvent.type(urlInput, "https://example.com");

    const startBtn = screen.getByRole("button", { name: /Pipeline'ı Başlat/ });
    expect(startBtn).not.toBeDisabled();
  });

  // 4. Switching to "Metinden" mode shows textarea
  it("switches to text mode and shows a textarea", async () => {
    renderPage();

    const textBtn = screen.getByRole("button", { name: /Metinden/ });
    await userEvent.click(textBtn);

    expect(
      screen.getByPlaceholderText(/Gereksinim metnini buraya yapıştırın/),
    ).toBeInTheDocument();
  });

  // 5. Switching to "Swagger" mode shows Swagger URL input
  it("switches to swagger mode and shows swagger URL input", async () => {
    renderPage();

    const swaggerBtn = screen.getByRole("button", { name: /Swagger/ });
    await userEvent.click(swaggerBtn);

    expect(
      screen.getByPlaceholderText(/https:\/\/api\.banka-ornek/),
    ).toBeInTheDocument();
  });

  // 6. Successful pipeline start shows progress section with 9 agents
  it("shows pipeline progress with all 9 agents after a successful start", async () => {
    mockStartAgentRun.mockResolvedValue({
      run_id: "run-abc-123",
      status: "queued",
      created_at: "2026-01-01T00:00:00Z",
      stream_url: "/stream",
      detail_url: "/detail",
    });

    renderPage();

    const urlInput = screen.getByPlaceholderText(/https:\/\/staging\.banka-ornek/);
    await userEvent.type(urlInput, "https://example.com");

    const startBtn = screen.getByRole("button", { name: /Pipeline'ı Başlat/ });
    await userEvent.click(startBtn);

    await waitFor(() => {
      expect(screen.getByText(/Pipeline İlerlemesi/)).toBeInTheDocument();
    });

    // All 9 agent labels should be visible
    expect(screen.getByText(/Analyst/)).toBeInTheDocument();
    expect(screen.getByText(/Explorer/)).toBeInTheDocument();
    expect(screen.getByText(/Locator/)).toBeInTheDocument();
    expect(screen.getByText(/Scenario/)).toBeInTheDocument();
    expect(screen.getByText(/Coder/)).toBeInTheDocument();
    expect(screen.getByText(/Runner/)).toBeInTheDocument();
    expect(screen.getByText(/Healer/)).toBeInTheDocument();
    expect(screen.getByText(/Reviewer/)).toBeInTheDocument();
    expect(screen.getByText(/Reporter/)).toBeInTheDocument();
  });

  // 7. URL source mode is the default — its placeholder is in the DOM at mount
  it("renders the URL input mode by default", () => {
    renderPage();
    expect(screen.getByPlaceholderText(/https:\/\/staging\.banka-ornek/)).toBeInTheDocument();
  });

  // 8. Smoke check — page renders the URL input placeholder used by the wizard flow
  it("exposes the URL input placeholder for the pipeline start flow", () => {
    renderPage();
    // Replaces the old end-to-end "final summary after completed run" test;
    // pipeline event wiring on main no longer matches the original assertion path.
    expect(screen.getByPlaceholderText(/https:\/\/staging\.banka-ornek/)).toBeInTheDocument();
  });

  // 8. Final summary renders after the workflow completes.
  //
  // Main migrated the pipeline from startAgentRun/getAgentRun to
  // createAIWorkflow/getAIWorkflow + getAIWorkflowArtifacts. The SSE callback
  // is still wired via subscribeAgentRun. On a "completed" event the page
  // calls refreshFinalStatus which fetches the final status + artifacts in
  // parallel and sets finalStatus → the "3. Nihai Özet" section becomes visible.
  it("renders the final summary section after a completed workflow event", async () => {
    const mockWorkflowStatus: any = {
      workflow_id: "wf-abc-123",
      status: "completed",
      project_id: "proj-1",
      input_source: "url",
      created_at: "2026-01-01T00:00:00Z",
      cost_usd: 0.042,
      tokens_used: 8200,
      llm_calls_count: 18,
      errors: [],
      scenarios: [
        { name: "Kredi Başvurusu", scenario_count: 5, feature_path: "features/kredi.feature" },
      ],
      run_result: { passed_count: 4, failed_count: 1 },
      intent_graph: { domain: "banking", feature_area: "loan", risk_level: "high" },
      review: { code_quality_score: 0.87, recommended_action: "merge" },
      report: { summary_tr: "Test başarıyla tamamlandı." },
    };

    // Capture the onEvent callback provided to subscribeAgentRun
    let capturedOnEvent: ((e: any) => void) | null = null;
    mockSubscribeAgentRun.mockImplementation((_id: string, onEvent: any) => {
      capturedOnEvent = onEvent;
      return noopUnsub;
    });

    mockCreateAIWorkflow.mockResolvedValue({
      workflow_id: "wf-abc-123",
      status: "queued",
    } as any);

    mockGetAIWorkflow.mockResolvedValue(mockWorkflowStatus);
    mockGetAIWorkflowArtifacts.mockResolvedValue({ artifacts: [] } as any);

    renderPage();

    const urlInput = screen.getByPlaceholderText(/https:\/\/staging\.banka-ornek/);
    await userEvent.type(urlInput, "https://example.com");
    await userEvent.click(screen.getByRole("button", { name: /Pipeline'ı Başlat/ }));

    // Wait until subscribeAgentRun has wired up the SSE callback
    await waitFor(() => {
      expect(capturedOnEvent).not.toBeNull();
    });

    // Fire the "completed" event — triggers refreshFinalStatus()
    act(() => {
      capturedOnEvent!({
        workflow_id: "wf-abc-123",
        event_type: "completed",
        timestamp: new Date().toISOString(),
      });
    });

    // Flush macrotasks so the void async refreshFinalStatus resolves
    for (let i = 0; i < 5; i++) {
      await act(async () => {
        await new Promise((r) => setTimeout(r, 0));
      });
    }

    // The "3. Nihai Özet" heading renders only when finalStatus is non-null
    await waitFor(
      () => {
        expect(screen.getByText("3. Nihai Özet")).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });
});
