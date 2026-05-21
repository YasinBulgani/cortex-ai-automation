/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

beforeEach(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  (global as any).fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          overall: "operational",
          uptime_90d: 99.987,
          services: [
            {
              name: "API",
              status: "operational",
              latency_ms: 42,
              last_checked: "2026-05-19T00:00:00Z",
              uptime_30d: 99.9,
            },
            {
              name: "Engine",
              status: "degraded",
              latency_ms: 1200,
              last_checked: "2026-05-19T00:00:00Z",
            },
          ],
          active_incidents: [],
          recent_incidents: [],
        }),
    })
  );
});

afterEach(() => {
  (console.error as jest.Mock).mockRestore();
  jest.clearAllMocks();
});

describe("StatusPage", () => {
  it("renders data-testid='status-page'", async () => {
    const { default: Page } = await import("../status/page");
    render(<Page />);
    expect(screen.getByTestId("status-page")).toBeInTheDocument();
  });

  it("shows page heading", async () => {
    const { default: Page } = await import("../status/page");
    render(<Page />);
    expect(screen.getByText(/Neurex QA Status/i)).toBeInTheDocument();
  });

  it("shows loading state initially", async () => {
    const { default: Page } = await import("../status/page");
    render(<Page />);
    expect(screen.getByTestId("status-loading")).toBeInTheDocument();
  });

  it("shows overall operational banner after data loads", async () => {
    const { default: Page } = await import("../status/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("status-overall")).toBeInTheDocument()
    );
    expect(screen.getByText(/Tüm sistemler çalışıyor/i)).toBeInTheDocument();
  });

  it("renders service rows for each service", async () => {
    const { default: Page } = await import("../status/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("service-API")).toBeInTheDocument()
    );
    expect(screen.getByTestId("service-Engine")).toBeInTheDocument();
  });

  it("shows 90d uptime percentage", async () => {
    const { default: Page } = await import("../status/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByText(/99.987/)).toBeInTheDocument()
    );
  });

  it("shows error banner when fetch fails", async () => {
    (global as any).fetch = jest.fn(() =>
      Promise.resolve({ ok: false, status: 500, statusText: "Server Error" })
    );
    const { default: Page } = await import("../status/page");
    render(<Page />);
    await waitFor(() =>
      expect(screen.getByTestId("status-error")).toBeInTheDocument()
    );
  });
});
