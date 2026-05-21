/** @jest-environment jsdom */

// ─── Required mocks (must be before imports) ─────────────────────────────────

jest.mock("next/link", () =>
  function MockLink({ href, children, ...rest }: { href: string; children: React.ReactNode; [k: string]: unknown }) {
    return <a href={href} {...rest}>{children}</a>;
  }
);

const mockRouterPush = jest.fn();
const mockRouterReplace = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(() => ({ push: mockRouterPush, replace: mockRouterReplace })),
  usePathname: () => "/",
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
}));

jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn(() => ({ data: [], isLoading: false, error: null, refetch: jest.fn() })),
  useMutation: jest.fn(() => ({ mutate: jest.fn(), mutateAsync: jest.fn(), isPending: false })),
  useQueryClient: jest.fn(() => ({ invalidateQueries: jest.fn() })),
}));

jest.mock("@/lib/api-client", () => ({
  apiFetch: jest.fn(),
  getToken: jest.fn(() => "tok"),
  setTokens: jest.fn(),
  clearTokens: jest.fn(),
  API_BASE: "http://localhost",
  getTokenExpiresAt: jest.fn(() => Date.now() + 999999),
}));

jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn(),
  ApiError: class ApiError extends Error {},
  ENGINE_BASE: "http://engine",
  clearTokens: jest.fn(),
  getToken: jest.fn(() => "tok"),
}));

jest.mock("@/lib/hooks", () => ({
  useProjects: jest.fn(() => ({ data: [], isLoading: false })),
}));

jest.mock("@/lib/useProject", () => ({
  useProject: jest.fn(() => ({ project: null, projectId: null, setProject: jest.fn() })),
  ProjectProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

jest.mock("@/lib/core-runtime", () => ({
  useCoreRuntime: jest.fn(() => ({
    loading: false, backendReady: true, services: [],
    authState: "ready", canQueryProjects: true, blockingReason: null,
  })),
}));

jest.mock("@/lib/product", () => ({
  PRODUCT_FAMILY: [],
  PRODUCT_FAMILY_STORAGE_KEY: "pf",
  PRODUCT_AVAILABILITY_META: {},
  PROJECT_NAV_DEFINITIONS: [],
  NAV_GROUP_LABELS: {},
  PRODUCT_SHORT: {},
  PRODUCT_LANDING_CONTENT: {},
  PLATFORM_BRAND: "Neurex QA",
  PRODUCT_TAGLINE: {},
  getDefaultEntryRouteForProduct: jest.fn(() => "/"),
  getProductEntryHref: jest.fn(() => "/"),
  getProductFamilyMember: jest.fn(() => null),
  getRoutesForProduct: jest.fn(() => []),
  getSegmentLabel: jest.fn(() => ""),
}));

jest.mock("cmdk", () => ({
  Command: Object.assign(
    ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    {
      Dialog: ({ open, children }: { open: boolean; children: React.ReactNode }) =>
        open ? <div role="dialog">{children}</div> : null,
      Input: ({ placeholder, ...rest }: React.InputHTMLAttributes<HTMLInputElement>) =>
        <input placeholder={placeholder} {...rest} />,
      List: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
      Empty: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
      Group: ({ children, heading }: { children: React.ReactNode; heading?: React.ReactNode }) =>
        <div>{heading}{children}</div>,
      Item: ({ children, onSelect }: { children: React.ReactNode; onSelect?: () => void }) =>
        <div onClick={onSelect}>{children}</div>,
    }
  ),
}));

jest.mock("@/lib/design-tokens", () => ({
  productMeta: {},
  surfaces: {},
  text: {},
  density: {},
  focusRing: "",
  focusRingDanger: "",
  interactive: {},
  animate: {},
}));

// ─── Imports ──────────────────────────────────────────────────────────────────

import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";

// ─── Global stubs ─────────────────────────────────────────────────────────────

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (q: string) => ({
    matches: false,
    media: q,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }),
});

beforeEach(() => {
  localStorage.clear();
  jest.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
  (console.error as jest.Mock).mockRestore();
});

// ─── 1. OnboardingTour ────────────────────────────────────────────────────────

import { OnboardingTour } from "../OnboardingTour";

describe("OnboardingTour", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
    localStorage.clear();
  });

  it("does not render when localStorage has neurex_onboarding_done set", () => {
    localStorage.setItem("neurex_onboarding_done", String(Date.now()));
    render(<OnboardingTour />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders the tour dialog after 800ms delay when no localStorage entry", () => {
    render(<OnboardingTour />);
    // Before timer fires — should not be visible
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    act(() => {
      jest.advanceTimersByTime(800);
    });

    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("shows step 1 title 'Neurex QA'a Hoş Geldin'", () => {
    render(<OnboardingTour />);
    act(() => {
      jest.advanceTimersByTime(800);
    });

    expect(screen.getByText("Neurex QA'a Hoş Geldin")).toBeInTheDocument();
  });

  it("'Atla' button dismisses the tour and sets localStorage", () => {
    render(<OnboardingTour />);
    act(() => {
      jest.advanceTimersByTime(800);
    });

    const atlaBtn = screen.getByRole("button", { name: /atla/i });
    fireEvent.click(atlaBtn);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(localStorage.getItem("neurex_onboarding_done")).not.toBeNull();
  });

  it("clicking the backdrop closes the tour", () => {
    render(<OnboardingTour />);
    act(() => {
      jest.advanceTimersByTime(800);
    });

    // The backdrop is the outer div with role="dialog"
    const backdrop = screen.getByRole("dialog");
    fireEvent.click(backdrop);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("'Başla' button advances to the next step", () => {
    render(<OnboardingTour />);
    act(() => {
      jest.advanceTimersByTime(800);
    });

    // Step 1 shows "Başla" as CTA
    const baslaBtn = screen.getByRole("button", { name: /başla/i });
    fireEvent.click(baslaBtn);

    // After advancing, step 2 should be visible
    expect(screen.getByText("Her şey klavyeden")).toBeInTheDocument();
  });
});

// ─── 2. ProjectSwitcher ───────────────────────────────────────────────────────

import { ProjectSwitcher } from "../ProjectSwitcher";

const SAMPLE_PROJECTS = [
  { id: "proj-1", name: "Alpha Projesi" },
  { id: "proj-2", name: "Beta Projesi" },
];

describe("ProjectSwitcher", () => {
  it("renders without crash", () => {
    render(<ProjectSwitcher projects={[]} />);
  });

  it("shows data-testid='header-project-switcher'", () => {
    render(<ProjectSwitcher projects={[]} />);
    expect(screen.getByTestId("header-project-switcher")).toBeInTheDocument();
  });

  it("shows data-testid='header-select-project'", () => {
    render(<ProjectSwitcher projects={[]} />);
    expect(screen.getByTestId("header-select-project")).toBeInTheDocument();
  });

  it("shows project names in the select options", () => {
    render(<ProjectSwitcher projects={SAMPLE_PROJECTS} />);
    expect(screen.getByRole("option", { name: "Alpha Projesi" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Beta Projesi" })).toBeInTheDocument();
  });

  it("shows data-testid='header-btn-new-project'", () => {
    render(<ProjectSwitcher projects={[]} />);
    expect(screen.getByTestId("header-btn-new-project")).toBeInTheDocument();
  });

  it("new project link href contains '/projects'", () => {
    render(<ProjectSwitcher projects={[]} />);
    const link = screen.getByTestId("header-btn-new-project");
    expect(link.getAttribute("href")).toContain("/projects");
  });

  it("fires router.push when select value changes", () => {
    mockRouterPush.mockClear();

    render(<ProjectSwitcher projects={SAMPLE_PROJECTS} currentId="proj-1" />);
    const select = screen.getByTestId("header-select-project");
    fireEvent.change(select, { target: { value: "proj-2" } });

    expect(mockRouterPush).toHaveBeenCalledWith(expect.stringContaining("proj-2"));
  });
});

// ─── 3. CommandPalette ────────────────────────────────────────────────────────

import { CommandPalette } from "../CommandPalette";

describe("CommandPalette", () => {
  it("does not render dialog when closed (no Cmd+K pressed)", () => {
    render(<CommandPalette />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders dialog when Cmd+K is pressed", () => {
    render(<CommandPalette />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("shows search input when open", () => {
    render(<CommandPalette />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(screen.getByPlaceholderText(/komut yaz/i)).toBeInTheDocument();
  });

  it("shows navigation commands list when open", () => {
    render(<CommandPalette />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    // "Git" group heading from NAV_COMMANDS group
    expect(screen.getByText("Git")).toBeInTheDocument();
  });

  it("closes dialog when Escape is pressed", () => {
    render(<CommandPalette />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows empty state text 'Sonuç bulunamadı' when open", () => {
    render(<CommandPalette />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    // Command.Empty always renders in our mock (no filtering)
    expect(screen.getByText(/sonuç bulunamadı/i)).toBeInTheDocument();
  });
});

// ─── 4. AuthBootstrap ────────────────────────────────────────────────────────

import AuthBootstrap from "../AuthBootstrap";

describe("AuthBootstrap", () => {
  it("returns null — renders nothing", () => {
    const { container } = render(<AuthBootstrap />);
    expect(container).toBeEmptyDOMElement();
  });

  it("does not throw on mount", () => {
    expect(() => render(<AuthBootstrap />)).not.toThrow();
  });

  it("does not throw on unmount", () => {
    const { unmount } = render(<AuthBootstrap />);
    expect(() => unmount()).not.toThrow();
  });
});
