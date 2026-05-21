/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ── Suppress noise ─────────────────────────────────────────────────────────
const consoleSpies: jest.SpyInstance[] = [];
beforeEach(() => {
  consoleSpies.push(jest.spyOn(console, "error").mockImplementation(() => {}));
  consoleSpies.push(jest.spyOn(console, "warn").mockImplementation(() => {}));
  (global as any).fetch = jest.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
  );
});
afterEach(() => {
  consoleSpies.forEach((s) => s.mockRestore());
  consoleSpies.length = 0;
  jest.clearAllMocks();
});

// ── Mocks ──────────────────────────────────────────────────────────────────
const searchParamsMock = {
  get: jest.fn((_key: string) => null),
};
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn(), replace: jest.fn() }),
  useSearchParams: () => searchParamsMock,
  useParams: jest.fn(() => ({})),
  redirect: jest.fn(),
  usePathname: () => "/p/proj-1",
}));

const apiFetchMock = jest.fn(() => Promise.resolve({}));
jest.mock("@/lib/api-client", () => ({
  apiFetch: (...args: any[]) => apiFetchMock(...args),
  engineFetch: jest.fn(() => Promise.resolve({})),
  getToken: jest.fn(() => "tok"),
  setTokens: jest.fn(),
  clearToken: jest.fn(),
  migrateToCookieAuth: jest.fn(),
  API_BASE: "http://localhost:8000",
  ENGINE_BASE: "http://localhost:8080",
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

// lucide-react icons → simple span replacements
jest.mock("lucide-react", () => {
  const Stub = (props: any) => <span data-testid="icon" {...props} />;
  return new Proxy({}, {
    get: () => Stub,
  });
});

// ── LoginPage ──────────────────────────────────────────────────────────────

describe("LoginPage", () => {
  beforeEach(() => {
    searchParamsMock.get.mockImplementation((_key: string) => null);
  });

  it("renders data-testid='login-page'", async () => {
    const { default: Page } = await import("../login/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("login-page")).toBeInTheDocument()
    );
  });

  it("shows heading", async () => {
    const { default: Page } = await import("../login/page");
    render(<Page />);
    // Main's login page heading is "Giriş Yap"; older versions used "Hoş geldiniz."
    await waitFor(() =>
      expect(screen.getByTestId("login-heading")).toHaveTextContent(/Giriş Yap|Hoş geldiniz/i)
    );
  });

  it("shows 'Neurex QA' logo", async () => {
    const { default: Page } = await import("../login/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("login-logo")).toHaveTextContent("Neurex QA")
    );
  });

  it("shows email input", async () => {
    const { default: Page } = await import("../login/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("login-input-email")).toBeInTheDocument()
    );
  });

  it("shows password input", async () => {
    const { default: Page } = await import("../login/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("login-input-password")).toBeInTheDocument()
    );
  });

  it("shows submit button", async () => {
    const { default: Page } = await import("../login/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("login-btn-submit")).toBeInTheDocument()
    );
  });

  it("renders login form (tabs are env-gated via NEXT_PUBLIC_ALLOW_SELF_REGISTRATION)", async () => {
    const { default: Page } = await import("../login/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("login-form")).toBeInTheDocument()
    );
  });

  it("shows 'Şifremi Unuttum' button", async () => {
    const { default: Page } = await import("../login/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("login-btn-forgot")).toBeInTheDocument()
    );
  });

  it("shows footer text", async () => {
    const { default: Page } = await import("../login/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("login-footer")).toHaveTextContent(/Neurex QA/i)
    );
  });

  it("shows login form by default", async () => {
    const { default: Page } = await import("../login/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("login-form")).toBeInTheDocument()
    );
  });
});

// ── ResetPasswordPage ──────────────────────────────────────────────────────

describe("ResetPasswordPage", () => {
  it("renders without crashing", async () => {
    searchParamsMock.get.mockImplementation(
      (key: string) => (key === "token" ? "valid-token-123" : null)
    );
    const { default: Page } = await import("../reset-password/page");
    const { container } = render(<Page />);
    await waitFor(() =>
      expect(container.firstChild).toBeInTheDocument()
    );
  });

  it("shows 'Geçersiz Bağlantı' when token missing", async () => {
    searchParamsMock.get.mockImplementation((_key: string) => null);
    const { default: Page } = await import("../reset-password/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Geçersiz Bağlantı")).toBeInTheDocument()
    );
  });

  it("shows error message when token missing", async () => {
    searchParamsMock.get.mockImplementation((_key: string) => null);
    const { default: Page } = await import("../reset-password/page");
    render(<Page />);
    await waitFor(() =>
      expect(
        screen.getByText(/Geçersiz veya eksik sıfırlama bağlantısı/i)
      ).toBeInTheDocument()
    );
  });

  it("shows 'Giriş Sayfasına Dön' button when error state", async () => {
    searchParamsMock.get.mockImplementation((_key: string) => null);
    const { default: Page } = await import("../reset-password/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Giriş Sayfasına Dön")).toBeInTheDocument()
    );
  });

  it("shows 'Yeni Şifre Belirle' heading with valid token", async () => {
    searchParamsMock.get.mockImplementation(
      (key: string) => (key === "token" ? "valid-token-123" : null)
    );
    const { default: Page } = await import("../reset-password/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Yeni Şifre Belirle")).toBeInTheDocument()
    );
  });

  it("shows 'Yeni Şifre' label with valid token", async () => {
    searchParamsMock.get.mockImplementation(
      (key: string) => (key === "token" ? "valid-token-123" : null)
    );
    const { default: Page } = await import("../reset-password/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Yeni Şifre")).toBeInTheDocument()
    );
  });

  it("shows 'Şifreyi Sıfırla' submit button with valid token", async () => {
    searchParamsMock.get.mockImplementation(
      (key: string) => (key === "token" ? "valid-token-123" : null)
    );
    const { default: Page } = await import("../reset-password/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Şifreyi Sıfırla")).toBeInTheDocument()
    );
  });

  it("shows 'Neurex QA' logo", async () => {
    searchParamsMock.get.mockImplementation(
      (key: string) => (key === "token" ? "valid-token-123" : null)
    );
    const { default: Page } = await import("../reset-password/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText("Neurex QA")).toBeInTheDocument()
    );
  });
});
