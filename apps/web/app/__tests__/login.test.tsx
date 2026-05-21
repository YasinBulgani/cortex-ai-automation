/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ replace: jest.fn(), push: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/p/proj-1",
}));

jest.mock("@/lib/hooks/use-auth", () => ({
  useLogin: () => ({ mutateAsync: jest.fn() }),
}));

jest.mock("@/lib/api-client", () => ({
  API_BASE: "http://localhost:8000",
  ENGINE_BASE: "http://localhost:5001",
  apiFetch: jest.fn(),
}));

jest.mock("@/components/BgtestLogo", () => ({
  BgtestLogo: (props: any) => <div data-testid="mock-logo" {...props} />,
}));

jest.mock("@/components/WorldWarBackground", () => ({
  WorldWarBackground: () => <div data-testid="mock-bg" />,
}));

import LoginPage from "@/app/login/page";

describe("LoginPage", () => {
  it("renders login form with email and password fields", () => {
    render(<LoginPage />);
    expect(screen.getByTestId("login-form")).toBeInTheDocument();
    expect(screen.getByTestId("login-input-email")).toBeInTheDocument();
    expect(screen.getByTestId("login-input-password")).toBeInTheDocument();
  });

  it("renders submit button", () => {
    render(<LoginPage />);
    expect(screen.getByTestId("login-btn-submit")).toBeInTheDocument();
    expect(screen.getByTestId("login-btn-submit")).toHaveTextContent("Giriş Yap");
  });

  it("renders heading and subtitle", () => {
    render(<LoginPage />);
    expect(screen.getByTestId("login-heading")).toHaveTextContent("Giriş Yap");
    expect(screen.getByTestId("login-subtitle")).toBeInTheDocument();
  });

  it("email input accepts user input", async () => {
    render(<LoginPage />);
    const emailInput = screen.getByTestId("login-input-email") as HTMLInputElement;
    await userEvent.type(emailInput, "test@example.com");
    expect(emailInput.value).toBe("test@example.com");
  });

  it("password input is of type password", () => {
    render(<LoginPage />);
    const pwInput = screen.getByTestId("login-input-password") as HTMLInputElement;
    expect(pwInput.type).toBe("password");
  });
});
