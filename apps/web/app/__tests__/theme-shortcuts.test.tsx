/** @jest-environment jsdom */
import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";

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
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: jest.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      addListener: jest.fn(),
      removeListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
  document.documentElement.classList.remove("dark");
});

// ── ThemeToggleFull ───────────────────────────────────────────────────────

describe("ThemeToggleFull", () => {
  it("renders three theme options", async () => {
    const { ThemeToggleFull } = await import("@/components/ThemeToggleFull");
    render(<ThemeToggleFull />);
    expect(screen.getByTestId("theme-toggle-full")).toBeInTheDocument();
    expect(screen.getByTestId("theme-option-light")).toBeInTheDocument();
    expect(screen.getByTestId("theme-option-dark")).toBeInTheDocument();
    expect(screen.getByTestId("theme-option-system")).toBeInTheDocument();
  });

  it("applies 'dark' class when dark option clicked", async () => {
    const { ThemeToggleFull } = await import("@/components/ThemeToggleFull");
    render(<ThemeToggleFull />);
    fireEvent.click(screen.getByTestId("theme-option-dark"));
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("removes 'dark' class when light option clicked", async () => {
    const { ThemeToggleFull } = await import("@/components/ThemeToggleFull");
    document.documentElement.classList.add("dark");
    render(<ThemeToggleFull />);
    fireEvent.click(screen.getByTestId("theme-option-light"));
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("persists theme to localStorage", async () => {
    const { ThemeToggleFull } = await import("@/components/ThemeToggleFull");
    render(<ThemeToggleFull />);
    fireEvent.click(screen.getByTestId("theme-option-light"));
    expect(localStorage.getItem("neurex_theme_v1")).toBe("light");
  });

  it("aria-pressed matches active theme", async () => {
    const { ThemeToggleFull } = await import("@/components/ThemeToggleFull");
    render(<ThemeToggleFull />);
    fireEvent.click(screen.getByTestId("theme-option-light"));
    expect(screen.getByTestId("theme-option-light")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("theme-option-dark")).toHaveAttribute("aria-pressed", "false");
  });
});

// ── normalizeCombo ────────────────────────────────────────────────────────

describe("normalizeCombo", () => {
  it("lowercases and orders modifiers", async () => {
    const { normalizeCombo } = await import("@/lib/useKeyboardShortcuts");
    expect(normalizeCombo("Cmd+K")).toBe("mod+k");
    expect(normalizeCombo("Ctrl+Shift+P")).toBe("mod+shift+p");
    expect(normalizeCombo("shift+alt+x")).toBe("shift+alt+x");
  });

  it("treats Cmd, Ctrl, Meta as mod", async () => {
    const { normalizeCombo } = await import("@/lib/useKeyboardShortcuts");
    expect(normalizeCombo("Cmd+k")).toBe(normalizeCombo("Ctrl+k"));
    expect(normalizeCombo("meta+k")).toBe(normalizeCombo("ctrl+k"));
  });
});

// ── displayCombo ──────────────────────────────────────────────────────────

describe("displayCombo", () => {
  it("renders mod key based on platform", async () => {
    const { displayCombo } = await import("@/lib/useKeyboardShortcuts");
    const result = displayCombo("mod+k");
    // Either "⌘K" (Mac) or "Ctrl+K" (other)
    expect(/(⌘|Ctrl)/.test(result)).toBe(true);
  });
});

// ── useKeyboardShortcuts ─────────────────────────────────────────────────

describe("useKeyboardShortcuts", () => {
  function TestApp({ shortcuts }: { shortcuts: any[] }) {
    const { useKeyboardShortcuts } = require("@/lib/useKeyboardShortcuts");
    useKeyboardShortcuts(shortcuts);
    return <div data-testid="app">App</div>;
  }

  it("fires handler on matching single combo", async () => {
    const handler = jest.fn();
    render(<TestApp shortcuts={[{ combo: "mod+k", description: "Test", handler }]} />);
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(handler).toHaveBeenCalled();
  });

  it("does not fire when combo doesn't match", async () => {
    const handler = jest.fn();
    render(<TestApp shortcuts={[{ combo: "mod+k", description: "Test", handler }]} />);
    fireEvent.keyDown(window, { key: "j", ctrlKey: true });
    expect(handler).not.toHaveBeenCalled();
  });

  it("does not fire inside input by default", async () => {
    const handler = jest.fn();
    render(
      <>
        <TestApp shortcuts={[{ combo: "mod+k", description: "Test", handler }]} />
        <input data-testid="some-input" />
      </>
    );
    const input = screen.getByTestId("some-input");
    fireEvent.keyDown(input, { key: "k", ctrlKey: true });
    expect(handler).not.toHaveBeenCalled();
  });

  it("fires inside input when allowInInputs=true", async () => {
    const handler = jest.fn();
    render(
      <>
        <TestApp shortcuts={[{ combo: "mod+k", description: "Test", handler, allowInInputs: true }]} />
        <input data-testid="some-input" />
      </>
    );
    fireEvent.keyDown(screen.getByTestId("some-input"), { key: "k", ctrlKey: true });
    expect(handler).toHaveBeenCalled();
  });
});

// ── KeyboardShortcutsHelp ────────────────────────────────────────────────

describe("KeyboardShortcutsHelp", () => {
  it("hidden by default", async () => {
    const { KeyboardShortcutsHelp } = await import("@/components/KeyboardShortcutsHelp");
    render(<KeyboardShortcutsHelp shortcuts={[]} />);
    expect(screen.queryByTestId("keyboard-help-panel")).not.toBeInTheDocument();
  });

  it("opens on ? key (shift+/)", async () => {
    const { KeyboardShortcutsHelp } = await import("@/components/KeyboardShortcutsHelp");
    render(<KeyboardShortcutsHelp shortcuts={[]} />);
    act(() => {
      fireEvent.keyDown(window, { key: "/", shiftKey: true });
    });
    expect(screen.getByTestId("keyboard-help-panel")).toBeInTheDocument();
  });

  it("renders shortcut items when open", async () => {
    const { KeyboardShortcutsHelp } = await import("@/components/KeyboardShortcutsHelp");
    const shortcuts = [
      { combo: "mod+k", description: "Komut paleti", handler: () => {} },
      { combo: "mod+s", description: "Kaydet", handler: () => {} },
    ];
    render(<KeyboardShortcutsHelp shortcuts={shortcuts} />);
    act(() => {
      fireEvent.keyDown(window, { key: "/", shiftKey: true });
    });
    expect(screen.getByTestId("keyboard-help-item-0")).toBeInTheDocument();
    expect(screen.getByText("Komut paleti")).toBeInTheDocument();
  });

  it("closes on close button click", async () => {
    const { KeyboardShortcutsHelp } = await import("@/components/KeyboardShortcutsHelp");
    render(<KeyboardShortcutsHelp shortcuts={[]} />);
    act(() => {
      fireEvent.keyDown(window, { key: "/", shiftKey: true });
    });
    expect(screen.getByTestId("keyboard-help-panel")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("keyboard-help-close"));
    expect(screen.queryByTestId("keyboard-help-panel")).not.toBeInTheDocument();
  });

  it("closes on overlay click", async () => {
    const { KeyboardShortcutsHelp } = await import("@/components/KeyboardShortcutsHelp");
    render(<KeyboardShortcutsHelp shortcuts={[]} />);
    act(() => {
      fireEvent.keyDown(window, { key: "/", shiftKey: true });
    });
    fireEvent.click(screen.getByTestId("keyboard-help-overlay"));
    expect(screen.queryByTestId("keyboard-help-panel")).not.toBeInTheDocument();
  });
});
