/** @jest-environment jsdom */
import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";

import { PWARegister } from "@/components/PWARegister";

// localStorage mock
const ls = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v; },
    removeItem: (k: string) => { delete store[k]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(global, "localStorage", { value: ls, configurable: true });

beforeEach(() => {
  ls.clear();
  jest.spyOn(console, "warn").mockImplementation(() => {});
});
afterEach(() => {
  (console.warn as jest.Mock).mockRestore();
});

function fireInstallPrompt(outcome: "accepted" | "dismissed" = "accepted") {
  const event: any = new Event("beforeinstallprompt");
  event.prompt = jest.fn(() => Promise.resolve());
  event.userChoice = Promise.resolve({ outcome });
  // bubble of beforeinstallprompt isn't standard, but window.dispatchEvent triggers listener
  window.dispatchEvent(event);
  return event;
}

describe("PWARegister", () => {
  it("renders nothing when no install event fired", () => {
    const { container } = render(<PWARegister />);
    expect(container.firstChild).toBeNull();
  });

  it("shows install prompt UI when beforeinstallprompt fires", async () => {
    render(<PWARegister />);
    await act(async () => {
      fireInstallPrompt();
    });
    expect(screen.getByTestId("pwa-install-prompt")).toBeInTheDocument();
    expect(screen.getByTestId("pwa-install-btn")).toBeInTheDocument();
    expect(screen.getByTestId("pwa-dismiss-btn")).toBeInTheDocument();
  });

  it("hides prompt and sets localStorage when user dismisses", async () => {
    render(<PWARegister />);
    await act(async () => {
      fireInstallPrompt();
    });
    expect(screen.getByTestId("pwa-install-prompt")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByTestId("pwa-dismiss-btn"));
    });

    expect(screen.queryByTestId("pwa-install-prompt")).not.toBeInTheDocument();
    expect(localStorage.getItem("neurex_pwa_dismissed")).toBe("1");
  });

  it("doesn't show prompt again if previously dismissed", async () => {
    localStorage.setItem("neurex_pwa_dismissed", "1");
    render(<PWARegister />);
    await act(async () => {
      fireInstallPrompt();
    });
    expect(screen.queryByTestId("pwa-install-prompt")).not.toBeInTheDocument();
  });

  it("calls prompt() and removes UI when user accepts", async () => {
    render(<PWARegister />);
    let captured: any;
    await act(async () => {
      captured = fireInstallPrompt("accepted");
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("pwa-install-btn"));
    });

    expect(captured.prompt).toHaveBeenCalled();
    expect(screen.queryByTestId("pwa-install-prompt")).not.toBeInTheDocument();
    // Accepted → NOT dismissed in localStorage
    expect(localStorage.getItem("neurex_pwa_dismissed")).toBeNull();
  });
});

describe("OfflinePage", () => {
  it("renders data-testid='offline-page'", async () => {
    const { default: Page } = await import("../offline/page");
    render(<Page />);
    expect(screen.getByTestId("offline-page")).toBeInTheDocument();
  });

  it("renders retry button", async () => {
    const { default: Page } = await import("../offline/page");
    render(<Page />);
    expect(screen.getByTestId("offline-retry")).toBeInTheDocument();
  });

  it("renders offline message", async () => {
    const { default: Page } = await import("../offline/page");
    render(<Page />);
    expect(screen.getByText(/İnternet bağlantısı yok/i)).toBeInTheDocument();
  });
});
