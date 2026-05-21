/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

// ─── jsdom polyfills ──────────────────────────────────────────────────────────
// AppShell uses ThemeToggle which calls window.matchMedia for the system theme.
beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: jest.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
});

// ─── Mocks ────────────────────────────────────────────────────────────────────

jest.mock("next/link", () =>
  function MockLink({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [k: string]: unknown;
  }) {
    return (
      <a href={href} {...rest}>
        {children}
      </a>
    );
  }
);

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => "/",
}));

jest.mock("@/lib/useProject", () => ({
  useProject: jest.fn(() => ({
    project: null,
    projectId: null,
    setProject: jest.fn(),
  })),
}));

jest.mock("@/lib/api", () => ({
  ENGINE_BASE: "http://engine",
  clearTokens: jest.fn(),
  apiFetch: jest.fn(),
}));

jest.mock("@/lib/product", () => ({
  PRODUCT_SHORT: "NX",
  PRODUCT_FAMILY: [],
  PRODUCT_FAMILY_STORAGE_KEY: "pf",
  PRODUCT_AVAILABILITY_META: {},
  PROJECT_NAV_DEFINITIONS: [],
  NAV_GROUP_LABELS: {},
}));

jest.mock("@/components/NotificationBell", () => ({
  NotificationBell: () => <div data-testid="notification-bell" />,
}));

jest.mock("@/components/ServiceRestartButton", () => ({
  ServiceRestartButton: () => <div data-testid="service-restart-btn" />,
}));

jest.mock("@/components/AiAssistantPanel", () => ({
  AiAssistantPanel: ({ open }: { open: boolean }) => (
    <div data-testid="ai-assistant-panel" data-open={open} />
  ),
}));

jest.mock("@/components/AiStatusChip", () => ({
  AiStatusChip: () => <div data-testid="ai-status-chip" />,
}));

jest.mock("@/components/OnboardingTour", () => ({
  OnboardingTour: () => null,
}));

jest.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) =>
    args
      .filter(Boolean)
      .join(" ")
      .trim(),
}));

// ─── Component under test ────────────────────────────────────────────────────

import { AppShell } from "../AppShell";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function renderAppShell(children = <div data-testid="child-content">Hello</div>) {
  return render(
    <AppShell projects={[]} >
      {children}
    </AppShell>
  );
}

// Suppress localStorage errors and console.error noise in jsdom
beforeEach(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  const localStorageMock = (() => {
    let store: Record<string, string> = {};
    return {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = value; },
      removeItem: (key: string) => { delete store[key]; },
      clear: () => { store = {}; },
    };
  })();
  Object.defineProperty(window, "localStorage", {
    value: localStorageMock,
    writable: true,
  });
});

afterEach(() => {
  (console.error as jest.Mock).mockRestore();
  jest.clearAllMocks();
});

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("AppShell", () => {
  it("renders without crash", () => {
    expect(() => renderAppShell()).not.toThrow();
  });

  it("renders sidebar-logo", () => {
    renderAppShell();
    expect(screen.getByTestId("sidebar-logo")).toBeInTheDocument();
  });

  it("renders sidebar-nav", () => {
    renderAppShell();
    expect(screen.getByTestId("sidebar-nav")).toBeInTheDocument();
  });

  it("renders children content", () => {
    renderAppShell(<div data-testid="child-content">Hello</div>);
    expect(screen.getByTestId("child-content")).toBeInTheDocument();
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("renders the notification bell component", () => {
    renderAppShell();
    expect(screen.getByTestId("notification-bell")).toBeInTheDocument();
  });

  it("renders the service restart button", () => {
    renderAppShell();
    expect(screen.getByTestId("service-restart-btn")).toBeInTheDocument();
  });

  it("shows logout button in the sidebar", () => {
    renderAppShell();
    // The sidebar logout button has data-testid="sidebar-btn-logout"
    const logoutBtn = screen.getByTestId("sidebar-btn-logout");
    expect(logoutBtn).toBeInTheDocument();
    expect(logoutBtn).toHaveTextContent("Çıkış");
  });
});
