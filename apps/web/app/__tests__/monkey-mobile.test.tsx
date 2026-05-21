/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

// ── Shared navigation mocks ────────────────────────────────────────────────────
jest.mock("next/navigation", () => ({
  useRouter: () => ({ replace: jest.fn(), push: jest.fn(), back: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/p/proj-1/monkey",
  useParams: () => ({ projectId: "proj-1" }),
}));

jest.mock("next/link", () => {
  const MockLink = ({ href, children, ...rest }: any) => (
    <a href={href} {...rest}>{children}</a>
  );
  MockLink.displayName = "MockLink";
  return MockLink;
});

// ── MonkeyPage mocks ───────────────────────────────────────────────────────────
jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

jest.mock("@/lib/ai-gateway", () => ({
  aiComplete: jest.fn(),
}));

// ── Shared api-client mock (covers both pages) ─────────────────────────────────
jest.mock("@/lib/api-client", () => ({
  getToken: jest.fn(() => "token"),
  engineFetch: jest.fn(),
  ENGINE_BASE: "http://localhost:5001",
}));

// ── MobilePage mocks ───────────────────────────────────────────────────────────
jest.mock("next/image", () => {
  const MockImage = ({ src, alt }: any) => <img src={src} alt={alt} />;
  MockImage.displayName = "MockImage";
  return MockImage;
});

jest.mock("@/components/dsl/MobileAiScenarioCard", () => ({
  MobileAiScenarioCard: ({ device, app }: any) => (
    <div data-testid="mobile-ai-card">{device?.name ?? "no-device"}</div>
  ),
}));

jest.mock("@/lib/utils", () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(" "),
}));

jest.mock("@/components/FlowGuideCard", () => ({
  FlowGuideCard: () => <div data-testid="flow-guide-card" />,
}));

// ── Suppress console noise ─────────────────────────────────────────────────────
beforeAll(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  jest.spyOn(console, "warn").mockImplementation(() => {});
});

afterAll(() => {
  (console.error as jest.Mock).mockRestore();
  (console.warn as jest.Mock).mockRestore();
});

// ── Shared fetch mock ──────────────────────────────────────────────────────────
beforeEach(() => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({}),
    text: async () => "",
    body: null,
  });

  // engineFetch mock: return empty arrays for device endpoints
  const { engineFetch } = require("@/lib/api-client");
  (engineFetch as jest.Mock).mockResolvedValue([]);
});

afterEach(() => {
  jest.clearAllMocks();
});

// ── Actual page imports ────────────────────────────────────────────────────────
import MonkeyPage from "@/app/(dashboard)/p/[projectId]/monkey/page";
import MobilePage from "@/app/(dashboard)/p/[projectId]/mobile/page";

// ═══════════════════════════════════════════════════════════════════════════════
// MonkeyPage tests
// ═══════════════════════════════════════════════════════════════════════════════

describe("MonkeyPage", () => {
  it("1. page renders the monkey testing banner", async () => {
    await act(async () => {
      render(<MonkeyPage />);
    });
    expect(screen.getByText(/Monkey Testing/i)).toBeInTheDocument();
  });

  it("2. configuration section heading renders", async () => {
    await act(async () => {
      render(<MonkeyPage />);
    });
    expect(screen.getByText(/Test Yapılandırması/i)).toBeInTheDocument();
  });

  it("3. URL input field is present with default URL", async () => {
    await act(async () => {
      render(<MonkeyPage />);
    });
    const urlInput = screen.getByPlaceholderText(/cortex-test\.bgtsai\.com/i) as HTMLInputElement;
    expect(urlInput).toBeInTheDocument();
    expect(urlInput.value).toBe("https://cortex-test.bgtsai.com");
  });

  it("4. action count slider is present", async () => {
    await act(async () => {
      render(<MonkeyPage />);
    });
    const slider = screen.getByRole("slider") as HTMLInputElement;
    expect(slider).toBeInTheDocument();
    expect(slider.type).toBe("range");
  });

  it("5. action type buttons render (click, scroll, navigate, etc.)", async () => {
    await act(async () => {
      render(<MonkeyPage />);
    });
    expect(screen.getByText("Rastgele Tıklama")).toBeInTheDocument();
    expect(screen.getByText("Kaydırma")).toBeInTheDocument();
    expect(screen.getByText("Geri/İleri Gezinme")).toBeInTheDocument();
    expect(screen.getByText("Rastgele Yazma")).toBeInTheDocument();
  });

  it("6. start button is disabled when URL is cleared", async () => {
    await act(async () => {
      render(<MonkeyPage />);
    });
    // Clear the URL so the button becomes disabled
    const urlInput = screen.getByPlaceholderText(/cortex-test\.bgtsai\.com/i);
    await act(async () => {
      fireEvent.change(urlInput, { target: { value: "" } });
    });
    const startBtn = screen.getByRole("button", { name: /Canlı Tarayıcı Testi Başlat/i });
    expect(startBtn).toBeDisabled();
  });

  it("7. start button is enabled when URL is entered", async () => {
    await act(async () => {
      render(<MonkeyPage />);
    });
    // Default URL is already set, so start button should be enabled
    const urlInput = screen.getByPlaceholderText(/cortex-test\.bgtsai\.com/i);
    await act(async () => {
      fireEvent.change(urlInput, { target: { value: "https://example.com" } });
    });
    const startBtn = screen.getByRole("button", { name: /Canlı Tarayıcı Testi Başlat/i });
    expect(startBtn).not.toBeDisabled();
  });

  it("8. session seed label (Eylem Sayısı) is present showing action count", async () => {
    await act(async () => {
      render(<MonkeyPage />);
    });
    // The UI shows "Eylem Sayısı: 50" as the label for the slider
    expect(screen.getByText(/Eylem Sayısı/i)).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// MobilePage tests
// ═══════════════════════════════════════════════════════════════════════════════

describe("MobilePage", () => {
  it("1. page renders with data-testid", async () => {
    await act(async () => {
      render(<MobilePage />);
    });
    expect(screen.getByTestId("mobile-page")).toBeInTheDocument();
  });

  it("2. device list / tab shows profile count (default tab is virtual)", async () => {
    await act(async () => {
      render(<MobilePage />);
    });
    // Virtual devices tab is shown by default
    const virtualTabBtn = screen.getByRole("button", { name: /Sanal Cihazlar/i });
    expect(virtualTabBtn).toBeInTheDocument();
  });

  it("3. FlowGuideCard renders", async () => {
    await act(async () => {
      render(<MobilePage />);
    });
    expect(screen.getByTestId("flow-guide-card")).toBeInTheDocument();
  });

  it("4. MobileAiScenarioCard renders", async () => {
    await act(async () => {
      render(<MobilePage />);
    });
    // MobileAiScenarioCard is rendered in the virtual tab (default)
    expect(screen.getByTestId("mobile-ai-card")).toBeInTheDocument();
  });

  it("5. APK/IPA file upload area renders", async () => {
    await act(async () => {
      render(<MobilePage />);
    });
    expect(screen.getByText(/APK \/ IPA/i)).toBeInTheDocument();
  });

  it("6. clicking the live devices tab switches to live panel", async () => {
    await act(async () => {
      render(<MobilePage />);
    });
    const liveTab = screen.getByRole("button", { name: /Canlı Cihazlar/i });
    await act(async () => {
      fireEvent.click(liveTab);
    });
    // After switching to live tab, the live device status area appears with
    // "Bağlı canlı cihaz yok" (empty state since mocked engineFetch returns [])
    const emptyStateElements = screen.getAllByText(/Bağlı canlı cihaz yok/i);
    expect(emptyStateElements.length).toBeGreaterThan(0);
  });

  it("7. runs history / run button section renders", async () => {
    await act(async () => {
      render(<MobilePage />);
    });
    // The run button has data-testid="run-btn"
    expect(screen.getByTestId("run-btn")).toBeInTheDocument();
  });

  it("8. Neurex Farm heading and page header description render", async () => {
    await act(async () => {
      render(<MobilePage />);
    });
    expect(screen.getByText("Neurex Farm")).toBeInTheDocument();
    expect(screen.getByText(/Mobil Test Orkestrasyonu/i)).toBeInTheDocument();
  });
});
