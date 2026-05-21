/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button onClick={onClick} {...rest}>{children}</button>
  ),
}));

jest.mock("@/lib/errors", () => ({
  copyToClipboard: jest.fn().mockResolvedValue(true),
  friendlyError: jest.fn((err: unknown) => ({
    title: err instanceof Error ? `Hata: ${err.message}` : "Bir hata oluştu",
    message: "Beklenmeyen bir hata oluştu.",
    detail: err instanceof Error ? err.message : undefined,
  })),
}));

import { ErrorBoundary } from "../ErrorBoundary";
import { copyToClipboard } from "@/lib/errors";

const ThrowingComponent = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) throw new Error("Test hatası");
  return <div data-testid="child">Normal içerik</div>;
};

const originalConsoleError = console.error;
beforeEach(() => { console.error = jest.fn(); });
afterEach(() => { console.error = originalConsoleError; });

describe("ErrorBoundary", () => {
  it("hata yoksa children render edilir", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ErrorBoundary>
    );
    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.queryByTestId("error-boundary")).not.toBeInTheDocument();
  });

  it("hata yakalanınca hata UI gösterilir", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow />
      </ErrorBoundary>
    );
    expect(screen.getByTestId("error-boundary")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.queryByTestId("child")).not.toBeInTheDocument();
  });

  it("'Tekrar Dene' butonu state'i sıfırlar ve children'ı yeniden render eder", () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow />
      </ErrorBoundary>
    );

    expect(screen.getByTestId("error-boundary")).toBeInTheDocument();

    // Switch the children to non-throwing BEFORE clicking retry, otherwise
    // the boundary catches the error again immediately on re-render.
    rerender(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ErrorBoundary>
    );

    fireEvent.click(screen.getByTestId("error-boundary-btn-retry"));

    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.queryByTestId("error-boundary")).not.toBeInTheDocument();
  });

  it("'Detayları göster' butonu teknik detayı açar", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow />
      </ErrorBoundary>
    );

    expect(screen.queryByTestId("error-boundary-btn-copy")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("error-boundary-btn-toggle-details"));

    expect(screen.getByTestId("error-boundary-btn-copy")).toBeInTheDocument();
    expect(screen.getByText("Detayları gizle")).toBeInTheDocument();
  });

  it("'Kopyala' butonu copyToClipboard çağırır", async () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow />
      </ErrorBoundary>
    );

    fireEvent.click(screen.getByTestId("error-boundary-btn-toggle-details"));
    fireEvent.click(screen.getByTestId("error-boundary-btn-copy"));

    await waitFor(() => {
      expect(copyToClipboard).toHaveBeenCalledWith("Test hatası");
    });
  });

  it("fallback prop sağlandığında custom fallback gösterilir", () => {
    render(
      <ErrorBoundary fallback={<div data-testid="custom-fallback">Özel hata ekranı</div>}>
        <ThrowingComponent shouldThrow />
      </ErrorBoundary>
    );

    expect(screen.getByTestId("custom-fallback")).toBeInTheDocument();
    expect(screen.queryByTestId("error-boundary")).not.toBeInTheDocument();
  });

  it("componentDidCatch console.error ile loglar", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow />
      </ErrorBoundary>
    );
    expect(console.error).toHaveBeenCalled();
  });
});
