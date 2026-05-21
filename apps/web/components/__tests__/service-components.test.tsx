/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

jest.mock("next/link", () =>
  function MockLink({ href, children, ...rest }: { href: string; children: React.ReactNode; [k: string]: unknown }) {
    return <a href={href} {...rest}>{children}</a>;
  }
);
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/",
}));

// Suppress console.error for caught errors
beforeEach(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
});
afterEach(() => {
  (console.error as jest.Mock).mockRestore();
  jest.clearAllMocks();
});

// ─── ServiceRestartButton ─────────────────────────────────────────────────────
import { ServiceRestartButton } from "../ServiceRestartButton";

let savedConfirm: typeof window.confirm;
let savedFetch: typeof global.fetch;

describe("ServiceRestartButton", () => {
  beforeEach(() => {
    savedConfirm = window.confirm;
    savedFetch = global.fetch;
  });
  afterEach(() => {
    window.confirm = savedConfirm;
    global.fetch = savedFetch;
  });

  it("renders the restart button", () => {
    render(<ServiceRestartButton />);
    expect(screen.getByTestId("header-btn-restart-services")).toBeInTheDocument();
  });

  it("button label shows 'Servisleri Yeniden Başlat' text", () => {
    render(<ServiceRestartButton />);
    const btn = screen.getByTestId("header-btn-restart-services");
    expect(btn.textContent).toContain("Yeniden Başlat");
  });

  it("button is enabled by default", () => {
    render(<ServiceRestartButton />);
    expect(screen.getByTestId("header-btn-restart-services")).not.toBeDisabled();
  });

  it("does not call fetch when user cancels confirm dialog", async () => {
    window.confirm = jest.fn().mockReturnValue(false);
    global.fetch = jest.fn();

    render(<ServiceRestartButton />);
    fireEvent.click(screen.getByTestId("header-btn-restart-services"));

    expect(window.confirm).toHaveBeenCalledTimes(1);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("calls fetch when user confirms and shows loading state", async () => {
    window.confirm = jest.fn().mockReturnValue(true);
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, message: "Servisler yeniden başlatıldı." }),
    } as Response);

    render(<ServiceRestartButton />);
    fireEvent.click(screen.getByTestId("header-btn-restart-services"));

    // While loading, button is disabled
    expect(screen.getByTestId("header-btn-restart-services")).toBeDisabled();

    await waitFor(() => expect(global.fetch as jest.Mock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByTestId("header-btn-restart-services")).not.toBeDisabled());
  });

  it("shows success message after successful restart", async () => {
    window.confirm = jest.fn().mockReturnValue(true);
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, message: "Servisler yeniden başlatıldı." }),
    } as Response);

    render(<ServiceRestartButton />);
    await act(async () => {
      fireEvent.click(screen.getByTestId("header-btn-restart-services"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("header-restart-services-status")).toBeInTheDocument();
    });
    expect(screen.getByTestId("header-restart-services-status").textContent).toContain("başlatıldı");
  });

  it("shows error message when fetch fails", async () => {
    window.confirm = jest.fn().mockReturnValue(true);
    global.fetch = jest.fn().mockRejectedValue(new Error("Network hatası"));

    render(<ServiceRestartButton />);
    await act(async () => {
      fireEvent.click(screen.getByTestId("header-btn-restart-services"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("header-restart-services-status")).toBeInTheDocument();
    });
    expect(screen.getByTestId("header-restart-services-status").textContent).toContain("Network hatası");
  });
});

// ─── ServiceTestingGuide ──────────────────────────────────────────────────────
import { ServiceTestingGuide } from "../ServiceTestingGuide";

describe("ServiceTestingGuide", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders without crashing", () => {
    const { container } = render(<ServiceTestingGuide projectId="proj-1" stage="spec" />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders stage labels (01, 02, 03)", () => {
    render(<ServiceTestingGuide projectId="proj-1" stage="spec" />);
    expect(screen.getByText("01")).toBeInTheDocument();
    expect(screen.getByText("02")).toBeInTheDocument();
    expect(screen.getByText("03")).toBeInTheDocument();
  });

  it("renders stage titles", () => {
    render(<ServiceTestingGuide projectId="proj-1" stage="spec" />);
    expect(screen.getByText("Spec ve Risk")).toBeInTheDocument();
    expect(screen.getByText("Chain Kur")).toBeInTheDocument();
    expect(screen.getByText("Kos ve Gözlemle")).toBeInTheDocument();
  });

  it("renders 'spec' description when stage is spec", () => {
    render(<ServiceTestingGuide projectId="proj-1" stage="spec" />);
    expect(screen.getByText(/OpenAPI veya Swagger/i)).toBeInTheDocument();
  });

  it("renders 'chain' description when stage is chain", () => {
    render(<ServiceTestingGuide projectId="proj-1" stage="chain" />);
    expect(screen.getByText(/zincire baglayip/i)).toBeInTheDocument();
  });

  it("renders 'run' description when stage is run", () => {
    render(<ServiceTestingGuide projectId="proj-1" stage="run" />);
    expect(screen.getByText(/çalıştırin/i)).toBeInTheDocument();
  });

  it("navigation links include projectId in href", () => {
    render(<ServiceTestingGuide projectId="my-project" stage="spec" />);
    const links = screen.getAllByRole("link");
    const hrefs = links.map(l => l.getAttribute("href") ?? "");
    expect(hrefs.some(h => h.includes("my-project"))).toBe(true);
  });
});

// ─── WorldWarBackground ───────────────────────────────────────────────────────
import { WorldWarBackground } from "../WorldWarBackground";

// jsdom doesn't implement canvas 2D context — stub it
let originalGetContext: typeof HTMLCanvasElement.prototype.getContext;
beforeAll(() => { originalGetContext = HTMLCanvasElement.prototype.getContext; });
afterAll(() => { HTMLCanvasElement.prototype.getContext = originalGetContext; });
beforeEach(() => {
  HTMLCanvasElement.prototype.getContext = jest.fn().mockReturnValue({
    // Minimal 2D context methods used by WorldWarBackground
    clearRect: jest.fn(),
    fillRect: jest.fn(),
    beginPath: jest.fn(),
    closePath: jest.fn(),
    moveTo: jest.fn(),
    lineTo: jest.fn(),
    stroke: jest.fn(),
    fill: jest.fn(),
    arc: jest.fn(),
    save: jest.fn(),
    restore: jest.fn(),
    translate: jest.fn(),
    scale: jest.fn(),
    rotate: jest.fn(),
    measureText: jest.fn().mockReturnValue({ width: 10 }),
    fillText: jest.fn(),
    strokeText: jest.fn(),
    drawImage: jest.fn(),
    setTransform: jest.fn(),
    createLinearGradient: jest.fn().mockReturnValue({
      addColorStop: jest.fn(),
    }),
    createRadialGradient: jest.fn().mockReturnValue({
      addColorStop: jest.fn(),
    }),
    createPattern: jest.fn().mockReturnValue({}),
    getImageData: jest.fn().mockReturnValue({ data: new Uint8ClampedArray() }),
    putImageData: jest.fn(),
    clip: jest.fn(),
    ellipse: jest.fn(),
    quadraticCurveTo: jest.fn(),
    bezierCurveTo: jest.fn(),
    setLineDash: jest.fn(),
    getLineDash: jest.fn().mockReturnValue([]),
    isPointInPath: jest.fn().mockReturnValue(false),
    isPointInStroke: jest.fn().mockReturnValue(false),
    resetTransform: jest.fn(),
    transform: jest.fn(),
    roundRect: jest.fn(),
    arcTo: jest.fn(),
    rect: jest.fn(),
    strokeRect: jest.fn(),
    clearRect: jest.fn(),
    canvas: { width: 800, height: 600 },
    globalAlpha: 1,
    strokeStyle: "",
    fillStyle: "",
    lineWidth: 1,
    font: "",
    textAlign: "left" as CanvasTextAlign,
    textBaseline: "alphabetic" as CanvasTextBaseline,
    shadowBlur: 0,
    shadowColor: "",
    globalCompositeOperation: "source-over" as GlobalCompositeOperation,
  });
});

describe("WorldWarBackground", () => {
  it("renders a canvas element", () => {
    const { container } = render(<WorldWarBackground />);
    expect(container.querySelector("canvas")).toBeInTheDocument();
  });

  it("does not throw on mount/unmount", () => {
    const { unmount } = render(<WorldWarBackground />);
    expect(() => unmount()).not.toThrow();
  });
});
