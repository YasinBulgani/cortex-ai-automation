/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/",
}));

// ─── BgtestLogo ───────────────────────────────────────────────────────────────
import { BgtestLogo } from "../BgtestLogo";

describe("BgtestLogo", () => {
  it("renders an svg element", () => {
    const { container } = render(<BgtestLogo />);
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("has aria-label 'Neurex QA'", () => {
    render(<BgtestLogo />);
    expect(screen.getByLabelText("Neurex QA")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<BgtestLogo className="h-20" />);
    expect(container.querySelector("svg")).toHaveClass("h-20");
  });
});

// ─── DemoDataBanner ───────────────────────────────────────────────────────────
import { DemoDataBanner } from "../DemoDataBanner";

describe("DemoDataBanner", () => {
  it("renders children", () => {
    render(<DemoDataBanner>Örnek veri</DemoDataBanner>);
    expect(screen.getByText("Örnek veri")).toBeInTheDocument();
  });

  it("has role='status'", () => {
    render(<DemoDataBanner>msg</DemoDataBanner>);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("has data-testid='demo-data-banner'", () => {
    render(<DemoDataBanner>msg</DemoDataBanner>);
    expect(screen.getByTestId("demo-data-banner")).toBeInTheDocument();
  });

  it("renders any ReactNode children", () => {
    render(
      <DemoDataBanner>
        <strong>Dikkat:</strong> Bu örnek veridir.
      </DemoDataBanner>
    );
    expect(screen.getByText("Dikkat:")).toBeInTheDocument();
  });
});

// ─── PageErrorBoundary ────────────────────────────────────────────────────────
import { PageErrorBoundary } from "../PageErrorBoundary";

function ThrowPage({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error("Page boom");
  return <div data-testid="page-content">Sayfa içeriği</div>;
}

beforeEach(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
});
afterEach(() => {
  (console.error as jest.Mock).mockRestore();
});

describe("PageErrorBoundary", () => {
  it("renders children when no error", () => {
    render(
      <PageErrorBoundary>
        <ThrowPage shouldThrow={false} />
      </PageErrorBoundary>
    );
    expect(screen.getByTestId("page-content")).toBeInTheDocument();
  });

  it("renders error UI when child throws", () => {
    render(
      <PageErrorBoundary>
        <ThrowPage shouldThrow />
      </PageErrorBoundary>
    );
    expect(screen.queryByTestId("page-content")).not.toBeInTheDocument();
    expect(screen.getByText(/hata oluştu/i)).toBeInTheDocument();
  });

  it("shows error message in error UI", () => {
    render(
      <PageErrorBoundary>
        <ThrowPage shouldThrow />
      </PageErrorBoundary>
    );
    expect(screen.getByText("Page boom")).toBeInTheDocument();
  });

  it("renders custom fallback when provided", () => {
    render(
      <PageErrorBoundary fallback={<div data-testid="custom-fb">Özel hata sayfası</div>}>
        <ThrowPage shouldThrow />
      </PageErrorBoundary>
    );
    expect(screen.getByTestId("custom-fb")).toBeInTheDocument();
  });

  it("retry button resets error state", () => {
    render(
      <PageErrorBoundary>
        <ThrowPage shouldThrow />
      </PageErrorBoundary>
    );
    const retryBtn = screen.getByRole("button", { name: /tekrar dene/i });
    fireEvent.click(retryBtn);
    // After reset it will throw again — just verify it doesn't crash
    expect(document.body).toBeInTheDocument();
  });
});

// ─── FileDropZone ─────────────────────────────────────────────────────────────
import { FileDropZone } from "../dnd/FileDropZone";

describe("FileDropZone", () => {
  it("renders drop zone container", () => {
    render(<FileDropZone onFiles={jest.fn()} />);
    expect(screen.getByTestId("file-drop-zone")).toBeInTheDocument();
  });

  it("renders default 'sürükleyip bırakın' text", () => {
    render(<FileDropZone onFiles={jest.fn()} />);
    expect(screen.getByText(/sürükleyip bırakın/i)).toBeInTheDocument();
  });

  it("renders children when provided", () => {
    render(
      <FileDropZone onFiles={jest.fn()}>
        <span data-testid="custom-child">Özel içerik</span>
      </FileDropZone>
    );
    expect(screen.getByTestId("custom-child")).toBeInTheDocument();
  });

  it("renders file input with aria-label", () => {
    render(<FileDropZone onFiles={jest.fn()} />);
    expect(screen.getByLabelText("Dosya seçin")).toBeInTheDocument();
  });

  it("applies accept attribute to file input", () => {
    render(<FileDropZone onFiles={jest.fn()} accept=".pdf,.doc" />);
    const input = screen.getByTestId("file-drop-input") as HTMLInputElement;
    expect(input.accept).toBe(".pdf,.doc");
  });

  it("shows dragover text when dragging over", () => {
    render(<FileDropZone onFiles={jest.fn()} />);
    const zone = screen.getByTestId("file-drop-zone");
    fireEvent.dragOver(zone);
    expect(screen.getByText(/dosyayı bırakın/i)).toBeInTheDocument();
  });

  it("shows error when file exceeds maxSizeMB", async () => {
    render(<FileDropZone onFiles={jest.fn()} maxSizeMB={1} />);
    const zone = screen.getByTestId("file-drop-zone");

    // Create a file larger than 1MB
    const bigFile = new File([new ArrayBuffer(2 * 1024 * 1024)], "big.pdf");
    Object.defineProperty(bigFile, "size", { value: 2 * 1024 * 1024 });

    fireEvent.drop(zone, {
      dataTransfer: { files: [bigFile] },
    });

    expect(await screen.findByTestId("file-drop-error")).toBeInTheDocument();
  });

  it("calls onFiles when valid file is dropped", () => {
    const onFiles = jest.fn();
    render(<FileDropZone onFiles={onFiles} maxSizeMB={10} />);
    const zone = screen.getByTestId("file-drop-zone");

    const smallFile = new File(["content"], "small.txt", { type: "text/plain" });
    fireEvent.drop(zone, {
      dataTransfer: { files: [smallFile] },
    });

    expect(onFiles).toHaveBeenCalledWith([smallFile]);
  });
});

// ─── PermissionGate ───────────────────────────────────────────────────────────
jest.mock("@/lib/useCurrentUser", () => ({
  useCurrentUser: jest.fn(),
}));
import { useCurrentUser } from "@/lib/useCurrentUser";
import { PermissionGate } from "../PermissionGate";

const mockUseCurrentUser = useCurrentUser as jest.Mock;

describe("PermissionGate", () => {
  it("shows loading skeleton while loading", () => {
    mockUseCurrentUser.mockReturnValue({ hasPermission: jest.fn(() => false), loading: true });
    render(<PermissionGate permission="admin.read"><span>Admin</span></PermissionGate>);
    expect(screen.getByTestId("permission-gate-loading")).toBeInTheDocument();
  });

  it("renders children when permission granted", () => {
    mockUseCurrentUser.mockReturnValue({ hasPermission: jest.fn(() => true), loading: false });
    render(<PermissionGate permission="admin.read"><span>Admin</span></PermissionGate>);
    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  it("renders fallback when permission denied", () => {
    mockUseCurrentUser.mockReturnValue({ hasPermission: jest.fn(() => false), loading: false });
    render(
      <PermissionGate permission="admin.delete" fallback={<span>Yetkisiz</span>}>
        <span>Gizli</span>
      </PermissionGate>
    );
    expect(screen.getByText("Yetkisiz")).toBeInTheDocument();
    expect(screen.queryByText("Gizli")).not.toBeInTheDocument();
  });

  it("renders null (no fallback) when denied and no fallback prop", () => {
    mockUseCurrentUser.mockReturnValue({ hasPermission: jest.fn(() => false), loading: false });
    const { container } = render(
      <PermissionGate permission="admin.delete">
        <span>Gizli</span>
      </PermissionGate>
    );
    expect(screen.queryByText("Gizli")).not.toBeInTheDocument();
    expect(container.textContent).toBe("");
  });

  it("loading skeleton has aria-busy", () => {
    mockUseCurrentUser.mockReturnValue({ hasPermission: jest.fn(() => false), loading: true });
    render(<PermissionGate permission="x"><span /></PermissionGate>);
    expect(screen.getByTestId("permission-gate-loading")).toHaveAttribute("aria-busy", "true");
  });
});

// ─── NotificationBell ─────────────────────────────────────────────────────────
jest.mock("@/lib/useWebSocket", () => ({
  useWebSocket: jest.fn(),
}));
import { useWebSocket } from "@/lib/useWebSocket";
import { NotificationBell } from "../NotificationBell";

const mockUseWebSocket = useWebSocket as jest.Mock;

describe("NotificationBell", () => {
  beforeEach(() => {
    mockUseWebSocket.mockReturnValue({
      messages: [],
      connected: true,
      clearMessages: jest.fn(),
    });
  });

  it("renders notification button", () => {
    render(<NotificationBell />);
    expect(screen.getByTestId("header-btn-notifications")).toBeInTheDocument();
  });

  it("does not show badge when no messages", () => {
    render(<NotificationBell />);
    expect(screen.queryByText(/^\d+$/)).not.toBeInTheDocument();
  });

  it("shows badge with message count", () => {
    mockUseWebSocket.mockReturnValue({
      messages: [{ type: "test.done", payload: "ok" }, { type: "test.fail", payload: "err" }],
      connected: true,
      clearMessages: jest.fn(),
    });
    render(<NotificationBell />);
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("shows 9+ when more than 9 messages", () => {
    const messages = Array.from({ length: 12 }, (_, i) => ({ type: `msg.${i}`, payload: i }));
    mockUseWebSocket.mockReturnValue({ messages, connected: true, clearMessages: jest.fn() });
    render(<NotificationBell />);
    expect(screen.getByText("9+")).toBeInTheDocument();
  });

  it("opens dropdown on click", () => {
    render(<NotificationBell />);
    fireEvent.click(screen.getByTestId("header-btn-notifications"));
    expect(screen.getByText("Bildirimler")).toBeInTheDocument();
  });

  it("shows 'Bildirim yok' in empty state when open", () => {
    render(<NotificationBell />);
    fireEvent.click(screen.getByTestId("header-btn-notifications"));
    expect(screen.getByText("Bildirim yok")).toBeInTheDocument();
  });

  it("calls clearMessages when Temizle clicked", () => {
    const clearMessages = jest.fn();
    mockUseWebSocket.mockReturnValue({ messages: [], connected: true, clearMessages });
    render(<NotificationBell />);
    fireEvent.click(screen.getByTestId("header-btn-notifications"));
    fireEvent.click(screen.getByText("Temizle"));
    expect(clearMessages).toHaveBeenCalledTimes(1);
  });
});

// ─── AiStatusChip ─────────────────────────────────────────────────────────────
import { AiStatusChip } from "../AiStatusChip";

// Helper: assign a fetch mock and restore it after each test
// (Don't use jest.spyOn — global.fetch may not exist as an own property in jsdom)
let originalFetch: typeof global.fetch;

describe("AiStatusChip", () => {
  beforeEach(() => {
    originalFetch = global.fetch;
  });
  afterEach(() => {
    global.fetch = originalFetch;
    jest.clearAllMocks();
  });

  it("shows loading state while fetching", () => {
    // Never resolves → component stays in loading=true
    global.fetch = jest.fn().mockReturnValue(new Promise(() => {}));
    render(<AiStatusChip />);
    expect(screen.getByText(/AI \.\.\./i)).toBeInTheDocument();
  });

  it("shows success chip when providers are active", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        providers: { anthropic: true, vllm: true, groq: false },
      }),
    } as Response);

    await act(async () => {
      render(<AiStatusChip />);
    });

    expect(screen.getByTestId("ai-status-chip")).toBeInTheDocument();
    expect(screen.getByText(/Anthropic/)).toBeInTheDocument();
  });

  it("shows danger chip when fetch fails", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("network error"));

    await act(async () => {
      render(<AiStatusChip />);
    });

    expect(screen.getByTestId("ai-status-chip")).toBeInTheDocument();
    // No providers active → danger tone
    expect(screen.getByText(/AI:/)).toBeInTheDocument();
  });

  it("shows warning chip when less than 2 providers active", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        providers: { anthropic: true, vllm: false },
      }),
    } as Response);

    await act(async () => {
      render(<AiStatusChip />);
    });

    expect(screen.getByTestId("ai-status-chip")).toBeInTheDocument();
  });

  it("shows +N when more than 1 active provider", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        providers: { anthropic: true, vllm: true, groq: true },
      }),
    } as Response);

    await act(async () => {
      render(<AiStatusChip />);
    });

    expect(screen.getByText(/\+2/)).toBeInTheDocument();
  });
});
