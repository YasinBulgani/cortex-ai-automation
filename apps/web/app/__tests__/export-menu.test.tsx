/** @jest-environment jsdom */
import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

jest.mock("@/lib/api", () => ({
  API_BASE: "http://localhost:8000",
  getToken: () => "test-token",
}));

import { ExportMenu } from "@/components/ExportMenu";

beforeEach(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  // jsdom URL.createObjectURL polyfill
  (global.URL.createObjectURL as any) = jest.fn(() => "blob:fake");
  (global.URL.revokeObjectURL as any) = jest.fn();
});
afterEach(() => {
  (console.error as jest.Mock).mockRestore();
});

function mockFetchOk(content = "exported content", headers: Record<string, string> = {}) {
  (global as any).fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      blob: () => Promise.resolve(new Blob([content], { type: "text/plain" })),
      headers: {
        get: (k: string) => headers[k.toLowerCase()] ?? null,
      },
    }),
  );
}

describe("ExportMenu", () => {
  it("renders trigger button", () => {
    render(<ExportMenu projectId="p1" runId="r1" />);
    expect(screen.getByTestId("export-menu-toggle")).toBeInTheDocument();
  });

  it("panel hidden until toggle clicked", () => {
    render(<ExportMenu projectId="p1" runId="r1" />);
    expect(screen.queryByTestId("export-menu-panel")).not.toBeInTheDocument();
  });

  it("opens panel with all 5 formats", () => {
    render(<ExportMenu projectId="p1" runId="r1" />);
    fireEvent.click(screen.getByTestId("export-menu-toggle"));
    expect(screen.getByTestId("export-menu-item-markdown")).toBeInTheDocument();
    expect(screen.getByTestId("export-menu-item-csv")).toBeInTheDocument();
    expect(screen.getByTestId("export-menu-item-json")).toBeInTheDocument();
    expect(screen.getByTestId("export-menu-item-xlsx")).toBeInTheDocument();
    expect(screen.getByTestId("export-menu-item-pdf")).toBeInTheDocument();
  });

  it("clicking a format calls fetch with correct URL + format query", async () => {
    mockFetchOk();
    render(<ExportMenu projectId="proj-1" runId="run-1" />);
    fireEvent.click(screen.getByTestId("export-menu-toggle"));
    fireEvent.click(screen.getByTestId("export-menu-item-csv"));

    await waitFor(() => {
      expect((global as any).fetch).toHaveBeenCalled();
    });
    const url = (global as any).fetch.mock.calls[0][0];
    expect(url).toContain("/api/v1/tspm/projects/proj-1/executions/run-1/export");
    expect(url).toContain("format=csv");
  });

  it("includes Authorization header when token present", async () => {
    mockFetchOk();
    render(<ExportMenu projectId="p" runId="r" />);
    fireEvent.click(screen.getByTestId("export-menu-toggle"));
    fireEvent.click(screen.getByTestId("export-menu-item-json"));
    await waitFor(() => {
      expect((global as any).fetch).toHaveBeenCalled();
    });
    const opts = (global as any).fetch.mock.calls[0][1];
    expect(opts.headers.Authorization).toBe("Bearer test-token");
    expect(opts.credentials).toBe("include");
  });

  it("shows 501 error message when optional library missing", async () => {
    (global as any).fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        status: 501,
        json: () => Promise.resolve({ detail: "reportlab kurulu değil" }),
      }),
    );
    render(<ExportMenu projectId="p" runId="r" />);
    fireEvent.click(screen.getByTestId("export-menu-toggle"));
    fireEvent.click(screen.getByTestId("export-menu-item-pdf"));
    await waitFor(() =>
      expect(screen.getByTestId("export-menu-error")).toHaveTextContent(/reportlab/i),
    );
  });

  it("shows generic error on non-2xx response", async () => {
    (global as any).fetch = jest.fn(() =>
      Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) }),
    );
    render(<ExportMenu projectId="p" runId="r" />);
    fireEvent.click(screen.getByTestId("export-menu-toggle"));
    fireEvent.click(screen.getByTestId("export-menu-item-csv"));
    await waitFor(() =>
      expect(screen.getByTestId("export-menu-error")).toHaveTextContent(/HTTP 500/i),
    );
  });

  it("closes panel after successful download", async () => {
    mockFetchOk();
    render(<ExportMenu projectId="p" runId="r" />);
    fireEvent.click(screen.getByTestId("export-menu-toggle"));
    fireEvent.click(screen.getByTestId("export-menu-item-json"));
    await waitFor(() => {
      expect(screen.queryByTestId("export-menu-panel")).not.toBeInTheDocument();
    });
  });

  it("uses Content-Disposition filename when present", async () => {
    mockFetchOk("data", { "content-disposition": 'attachment; filename="report.csv"' });

    const appendSpy = jest.spyOn(document.body, "appendChild");
    render(<ExportMenu projectId="p" runId="r" />);
    fireEvent.click(screen.getByTestId("export-menu-toggle"));
    fireEvent.click(screen.getByTestId("export-menu-item-csv"));

    await waitFor(() => {
      expect(appendSpy).toHaveBeenCalled();
    });
    const appended = appendSpy.mock.calls.find(
      ([n]) => (n as HTMLElement).tagName === "A",
    )?.[0] as HTMLAnchorElement | undefined;
    expect(appended?.download).toBe("report.csv");
    appendSpy.mockRestore();
  });
});
