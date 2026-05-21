/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";

// ─── Global mocks ──────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => "/",
  useParams: () => ({}),
}));

jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn(),
  API_BASE: "http://localhost",
  getToken: jest.fn(() => "tok"),
  ApiError: class extends Error {},
}));

jest.mock("@/lib/useProject", () => ({
  useProject: jest.fn(() => ({
    project: { id: "proj-1", name: "Test" },
    projectId: "proj-1",
    setProject: jest.fn(),
  })),
  ProjectProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ─── jsdom stubs ──────────────────────────────────────────────────────────────

// jsdom does not implement scrollIntoView — stub it globally so AgentRunner
// and AiAssistantPanel don't throw when their scroll refs fire.
window.HTMLElement.prototype.scrollIntoView = jest.fn();

// ─── Save / restore fetch + WebSocket ──────────────────────────────────────────

let originalFetch: typeof global.fetch;
let originalWebSocket: typeof global.WebSocket;

beforeAll(() => {
  originalFetch = global.fetch;
  originalWebSocket = global.WebSocket;
});

afterAll(() => {
  global.fetch = originalFetch;
  global.WebSocket = originalWebSocket;
});

beforeEach(() => {
  // Default no-op fetch so tests don't accidentally hit the network
  global.fetch = jest.fn().mockResolvedValue({
    ok: false,
    status: 500,
    text: async () => "Server error",
    json: async () => ({}),
    body: null,
  }) as jest.Mock;
});

afterEach(() => {
  jest.clearAllMocks();
});

// ═══════════════════════════════════════════════════════════════════════════════
// 1. DocumentUploader
// ═══════════════════════════════════════════════════════════════════════════════

import { DocumentUploader } from "../DocumentUploader";

describe("DocumentUploader", () => {
  const defaultProps = {
    projectId: "proj-1",
    onUploaded: jest.fn(),
    onError: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // Test 1 — renders without crash
  it("renders without crashing", () => {
    const { container } = render(<DocumentUploader {...defaultProps} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  // Test 2 — default state text
  it('shows "Dosyayı sürükleyin" text in default state', () => {
    render(<DocumentUploader {...defaultProps} />);
    expect(
      screen.getByText(/Dosyayı sürükleyin veya tıklayın/i)
    ).toBeInTheDocument();
  });

  // Test 3 — format badges
  it("shows format badges PDF, DOCX, TXT, MD", () => {
    render(<DocumentUploader {...defaultProps} />);
    expect(screen.getByText("PDF")).toBeInTheDocument();
    expect(screen.getByText("DOCX")).toBeInTheDocument();
    expect(screen.getByText("TXT")).toBeInTheDocument();
    expect(screen.getByText("MD")).toBeInTheDocument();
  });

  // Test 4 — hidden file input with correct accept attribute
  it("has a hidden file input with accept='.pdf,.docx,.txt,.md'", () => {
    const { container } = render(<DocumentUploader {...defaultProps} />);
    const input = container.querySelector("input[type='file']") as HTMLInputElement;
    expect(input).toBeInTheDocument();
    expect(input.accept).toBe(".pdf,.docx,.txt,.md");
    expect(input.className).toContain("hidden");
  });

  // Test 5 — calls onError with format error when unsupported file type is dropped
  it("calls onError with format error message when unsupported file type is dropped", async () => {
    const onError = jest.fn();
    render(<DocumentUploader {...defaultProps} onError={onError} />);

    const dropZone = screen.getByText(/Dosyayı sürükleyin veya tıklayın/i)
      .closest("div[class*='rounded-xl']") as HTMLElement;

    const file = new File(["content"], "test.exe", { type: "application/octet-stream" });

    await act(async () => {
      fireEvent.drop(dropZone, {
        dataTransfer: { files: [file] },
      });
    });

    expect(onError).toHaveBeenCalledWith(
      expect.stringMatching(/Desteklenmeyen format|Kabul edilenler/i)
    );
  });

  // Test 6 — calls onError when file > 20MB
  it("calls onError when file exceeds 20MB", async () => {
    const onError = jest.fn();
    render(<DocumentUploader {...defaultProps} onError={onError} />);

    const dropZone = screen.getByText(/Dosyayı sürükleyin veya tıklayın/i)
      .closest("div[class*='rounded-xl']") as HTMLElement;

    // Create a large file (21MB)
    const largeContent = new Uint8Array(21 * 1024 * 1024);
    const file = new File([largeContent], "large.pdf", { type: "application/pdf" });

    await act(async () => {
      fireEvent.drop(dropZone, {
        dataTransfer: { files: [file] },
      });
    });

    expect(onError).toHaveBeenCalledWith(
      expect.stringMatching(/çok büyük|Maksimum/i)
    );
  });

  // Test 7 — shows uploading state (progress indicator) when a valid file is processed
  it("shows uploading state when a valid file is processed", async () => {
    // Make fetch hang so the uploading state is visible
    global.fetch = jest.fn().mockReturnValue(new Promise(() => {})) as jest.Mock;

    render(<DocumentUploader {...defaultProps} />);

    const dropZone = screen.getByText(/Dosyayı sürükleyin veya tıklayın/i)
      .closest("div[class*='rounded-xl']") as HTMLElement;

    const file = new File(["pdf content"], "test.pdf", { type: "application/pdf" });

    await act(async () => {
      fireEvent.drop(dropZone, {
        dataTransfer: { files: [file] },
      });
    });

    // The progress indicator renders an SVG with the circle and a percentage text
    await waitFor(() => {
      expect(screen.getByText(/Doküman işleniyor/i)).toBeInTheDocument();
    });
  });

  // Test 8 — after successful upload shows filename and stats
  it("shows filename and stats after successful upload", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        filename: "test.pdf",
        format: "pdf",
        page_count: 5,
        word_count: 1000,
        char_count: 5000,
        chunk_count: 3,
        needs_chunking: false,
        sections: ["Section 1"],
        preview: "Preview text",
        full_text: "full text",
        message: "Yüklendi",
      }),
    }) as jest.Mock;

    const onUploaded = jest.fn();
    render(<DocumentUploader {...defaultProps} onUploaded={onUploaded} />);

    const dropZone = screen.getByText(/Dosyayı sürükleyin veya tıklayın/i)
      .closest("div[class*='rounded-xl']") as HTMLElement;

    const file = new File(["pdf content"], "test.pdf", { type: "application/pdf" });

    await act(async () => {
      fireEvent.drop(dropZone, {
        dataTransfer: { files: [file] },
      });
    });

    await waitFor(() => {
      expect(screen.getByText("test.pdf")).toBeInTheDocument();
    });

    // Stats grid
    expect(screen.getByText("Yüklendi")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument(); // page_count
    expect(screen.getByText("3")).toBeInTheDocument(); // chunk_count

    // onUploaded callback should have been called
    expect(onUploaded).toHaveBeenCalledWith(
      expect.objectContaining({ filename: "test.pdf", page_count: 5 })
    );
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 2. AgentRunner
// ═══════════════════════════════════════════════════════════════════════════════

import { AgentRunner } from "../AgentRunner";
import { apiFetch } from "@/lib/api";

const mockApiFetch = apiFetch as jest.Mock;

describe("AgentRunner", () => {
  beforeEach(() => {
    mockApiFetch.mockResolvedValue({
      run_id: null,
      phase: "idle",
      running: false,
      progress: 0,
      logs: [],
      total: 0,
    });
  });

  // Test 1 — renders without crash
  it("renders without crashing", () => {
    const { container } = render(<AgentRunner />);
    expect(container).toBeInTheDocument();
  });

  // Test 2 — renders without throwing when apiFetch is mocked
  it("renders without throwing when apiFetch is mocked", async () => {
    let error: unknown;
    try {
      await act(async () => {
        render(<AgentRunner />);
      });
    } catch (e) {
      error = e;
    }
    expect(error).toBeUndefined();
  });

  // Test 3 — shows a start/run button
  it("shows a run button with correct text", () => {
    render(<AgentRunner />);
    // The trigger button shows "Ajanları Çalıştır" in idle state
    expect(
      screen.getByTestId("btn-run-all-agents")
    ).toBeInTheDocument();
    expect(screen.getByTestId("btn-run-all-agents")).toHaveTextContent(
      /Ajanları Çalıştır/i
    );
  });

  // Test 4 — shows log area (the drawer panel)
  it("shows the pipeline drawer with log area after clicking run", async () => {
    // apiFetch for run-all returns a run_id, then logs poll returns idle/no logs
    mockApiFetch
      .mockResolvedValueOnce({ run_id: "run-123" })    // POST /run-all
      .mockResolvedValue({                              // GET /logs polling
        run_id: "run-123",
        phase: "idle",
        running: false,
        progress: 0,
        logs: [],
        total: 0,
      });

    render(<AgentRunner />);

    await act(async () => {
      fireEvent.click(screen.getByTestId("btn-run-all-agents"));
    });

    await waitFor(() => {
      expect(screen.getByRole("dialog", { name: /Ajan Orkestratörü/i })).toBeInTheDocument();
    });
  });

  // Test 5 — correct structure (the dialog element exists in DOM even when closed via CSS)
  it("has a drawer dialog element in the DOM", () => {
    render(<AgentRunner />);
    // The drawer is always in the DOM (visibility controlled by CSS translate)
    expect(
      screen.getByRole("dialog", { name: /Ajan Orkestratörü/i })
    ).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 3. AiAssistantPanel
// ═══════════════════════════════════════════════════════════════════════════════

import { AiAssistantPanel } from "../AiAssistantPanel";

// The component manages its own open/closed state internally via Cmd+J.
// We test the rendered output: floating button always present, panel hidden/visible.

describe("AiAssistantPanel", () => {
  beforeEach(() => {
    // No-op fetch — prevents network calls from send()
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => "",
      json: async () => ({}),
      body: null,
    }) as jest.Mock;

    mockApiFetch.mockResolvedValue({ id: "session-1", title: "Test Session" });
  });

  // Test 1 — panel is in translate-x-full (hidden) on initial render (open=false)
  it("renders the panel element with translate-x-full class when closed by default", () => {
    render(<AiAssistantPanel />);
    const panel = screen.getByTestId("ai-panel");
    expect(panel.className).toMatch(/translate-x-full/);
  });

  // Test 2 — clicking the FAB opens the panel
  it("renders the panel visible when FAB is clicked", async () => {
    render(<AiAssistantPanel />);

    const fab = screen.getByTestId("ai-fab");
    await act(async () => {
      fireEvent.click(fab);
    });

    const panel = screen.getByTestId("ai-panel");
    // When open, translate-x-0 class is applied (no translate-x-full)
    expect(panel.className).not.toMatch(/translate-x-full/);
  });

  // Test 3 — shows a text input for messages when panel is open
  it("shows a textarea input for messages when panel is open", async () => {
    render(<AiAssistantPanel />);

    await act(async () => {
      fireEvent.click(screen.getByTestId("ai-fab"));
    });

    expect(
      screen.getByPlaceholderText(/Bir şey sor/i)
    ).toBeInTheDocument();
  });

  // Test 4 — shows "Kapat" aria-label close button when open
  it('shows a close button with aria-label "Kapat" when open', async () => {
    render(<AiAssistantPanel />);

    await act(async () => {
      fireEvent.click(screen.getByTestId("ai-fab"));
    });

    expect(screen.getByRole("button", { name: /Kapat/i })).toBeInTheDocument();
  });

  // Test 5 — clicking close button hides the panel
  it("hides the panel when the close button is clicked", async () => {
    render(<AiAssistantPanel />);

    // Open the panel
    await act(async () => {
      fireEvent.click(screen.getByTestId("ai-fab"));
    });

    const panel = screen.getByTestId("ai-panel");
    expect(panel.className).not.toMatch(/translate-x-full/);

    // Close the panel
    const closeBtn = screen.getByRole("button", { name: /Kapat/i });
    await act(async () => {
      fireEvent.click(closeBtn);
    });

    expect(panel.className).toMatch(/translate-x-full/);
  });

  // Test 6 — shows quick prompt buttons when panel is open
  it("shows quick prompt buttons when panel is open", async () => {
    render(<AiAssistantPanel />);

    await act(async () => {
      fireEvent.click(screen.getByTestId("ai-fab"));
    });

    // The default pathname is "/" so we expect the default quick prompts to render
    // "Sonraki adım" and "Yardım et" are the default quick prompt labels
    await waitFor(() => {
      const promptButtons = screen.getAllByRole("button");
      // At minimum we should have more than just the FAB and close button
      expect(promptButtons.length).toBeGreaterThan(2);
    });

    // Check for at least one quick prompt text (defaults for pathname="/")
    // pathname "/" matches key "/" which has "Sistem durumu" and "Son aktiviteler"
    const quickPromptMatches = screen.getAllByText(
      /Sistem durumu|Son aktiviteler|Sonraki adım|Yardım et/i
    );
    expect(quickPromptMatches.length).toBeGreaterThan(0);
  });
});
