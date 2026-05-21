/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

jest.mock("@tanstack/react-query", () => ({
  QueryClient: jest.fn(() => ({ defaultOptions: {} })),
  QueryClientProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="query-client-provider">{children}</div>
  ),
}));

import { QueryProvider } from "../query-provider";

describe("QueryProvider", () => {
  it("renders without crash", () => {
    const { container } = render(
      <QueryProvider>
        <div>child</div>
      </QueryProvider>
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders children", () => {
    render(
      <QueryProvider>
        <span data-testid="inner">hello</span>
      </QueryProvider>
    );
    expect(screen.getByTestId("inner")).toBeInTheDocument();
  });

  it("wraps children in QueryClientProvider", () => {
    render(
      <QueryProvider>
        <div>test</div>
      </QueryProvider>
    );
    expect(screen.getByTestId("query-client-provider")).toBeInTheDocument();
  });
});
