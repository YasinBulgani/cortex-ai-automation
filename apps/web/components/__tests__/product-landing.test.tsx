/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

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
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  usePathname: () => "/",
}));

jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn().mockResolvedValue([]),
  ApiError: class extends Error {
    status: number;
    constructor(message: string, status = 500) {
      super(message);
      this.status = status;
    }
  },
}));

jest.mock("@/lib/core-runtime", () => ({
  useCoreRuntime: jest.fn(() => ({
    loading: false,
    backendReady: true,
    services: [],
    authState: "ready",
    canQueryProjects: true,
    blockingReason: null,
    error: null,
  })),
}));

const MOCK_LANDING_CONTENT = {
  eyebrow: "Test Eyebrow",
  headline: "Test Headline",
  summary: "Test Summary",
  primaryOutcome: "Test Outcome",
  startRouteKey: "overview",
  projectKeywords: ["test", "quality"],
};

jest.mock("@/lib/product", () => ({
  PRODUCT_FAMILY_STORAGE_KEY: "pf",
  PRODUCT_LANDING_CONTENT: new Proxy(
    {},
    {
      get: () => ({
        eyebrow: "Test Eyebrow",
        headline: "Test Headline",
        summary: "Test Summary",
        primaryOutcome: "Test Outcome",
        startRouteKey: "overview",
        projectKeywords: ["test", "quality"],
      }),
    }
  ),
  PRODUCT_AVAILABILITY_META: {},
  PLATFORM_BRAND: { name: "Neurex QA" },
  PRODUCT_TAGLINE: "Test operasyonlarını tek omurgada tasarla, çalıştır ve gözlemle.",
  getDefaultEntryRouteForProduct: jest.fn(() => ({
    key: "overview",
    label: "Genel Bakış",
    path: "overview",
  })),
  getProductEntryHref: jest.fn(() => "/p/test-project/overview"),
  getProductFamilyMember: jest.fn(() => ({
    id: "one",
    name: "Neurex One",
    shortName: "ONE",
    tagline: "End-to-end test platform",
    description: "Core product",
    availability: "core",
    defaultEntryKey: "overview",
    routeSegments: [],
  })),
  getRoutesForProduct: jest.fn(() => []),
}));

// ─── Suppress console noise ───────────────────────────────────────────────────

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
  // dispatchEvent is used in component — ensure it doesn't throw
  jest.spyOn(window, "dispatchEvent").mockImplementation(() => true);
});

afterEach(() => {
  (console.error as jest.Mock).mockRestore();
  (window.dispatchEvent as jest.Mock).mockRestore();
  jest.clearAllMocks();
});

// ─── Component under test ────────────────────────────────────────────────────

import { ProductLandingPage } from "../ProductLandingPage";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("ProductLandingPage", () => {
  it("renders without crash", () => {
    expect(() =>
      render(<ProductLandingPage productId="one" />)
    ).not.toThrow();
  });

  it("renders platform branding text", () => {
    render(<ProductLandingPage productId="one" />);
    // PLATFORM_BRAND.name is rendered in the header
    expect(screen.getByText("Neurex QA")).toBeInTheDocument();
  });

  it("renders without throwing even when apiFetch returns empty array", async () => {
    const { apiFetch } = jest.requireMock("@/lib/api");
    (apiFetch as jest.Mock).mockResolvedValue([]);

    let container: HTMLElement | undefined;
    expect(() => {
      const result = render(<ProductLandingPage productId="one" />);
      container = result.container;
    }).not.toThrow();

    expect(container).toBeTruthy();
  });

  it("renders a container element", () => {
    const { container } = render(<ProductLandingPage productId="one" />);
    // The root div should be present
    expect(container.firstChild).toBeTruthy();
    expect(container.firstChild).toBeInstanceOf(HTMLElement);
  });

  it("does not crash on mount and unmount", () => {
    const { unmount } = render(<ProductLandingPage productId="one" />);
    expect(() => unmount()).not.toThrow();
  });
});
