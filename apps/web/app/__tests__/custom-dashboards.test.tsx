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

jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

jest.mock("next/link", () =>
  function MockLink({ href, children, ...rest }: any) {
    return <a href={href} {...rest}>{children}</a>;
  }
);

beforeEach(() => {
  ls.clear();
  // window.confirm mock
  (window as any).confirm = jest.fn(() => true);
});

describe("CustomDashboardsPage", () => {
  it("renders data-testid='custom-dashboards-page'", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/dashboards/page");
    render(<Page />);
    expect(screen.getByTestId("custom-dashboards-page")).toBeInTheDocument();
  });

  it("shows empty state when no dashboards exist", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/dashboards/page");
    render(<Page />);
    expect(screen.getByTestId("dashboard-empty")).toBeInTheDocument();
    expect(screen.getByText(/Henüz dashboard yok/i)).toBeInTheDocument();
  });

  it("creates a new dashboard via input + button", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/dashboards/page");
    render(<Page />);
    const input = screen.getByTestId("dashboard-new-name-input");
    fireEvent.change(input, { target: { value: "My Dashboard" } });
    fireEvent.click(screen.getByTestId("dashboard-create-btn"));
    expect(screen.getByTestId("dashboard-no-widgets")).toBeInTheDocument();
    expect(screen.getByTestId("dashboard-name")).toHaveTextContent("My Dashboard");
  });

  it("create button is disabled when name is empty", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/dashboards/page");
    render(<Page />);
    const btn = screen.getByTestId("dashboard-create-btn");
    expect(btn).toBeDisabled();
  });

  it("opens widget library when '+ Widget Ekle' clicked", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/dashboards/page");
    render(<Page />);
    fireEvent.change(screen.getByTestId("dashboard-new-name-input"), { target: { value: "D" } });
    fireEvent.click(screen.getByTestId("dashboard-create-btn"));
    fireEvent.click(screen.getByTestId("dashboard-add-widget-btn"));
    expect(screen.getByTestId("widget-library")).toBeInTheDocument();
    expect(screen.getByTestId("widget-add-pass-rate")).toBeInTheDocument();
  });

  it("adds a widget when library item clicked", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/dashboards/page");
    render(<Page />);
    fireEvent.change(screen.getByTestId("dashboard-new-name-input"), { target: { value: "D" } });
    fireEvent.click(screen.getByTestId("dashboard-create-btn"));
    fireEvent.click(screen.getByTestId("dashboard-add-widget-btn"));
    fireEvent.click(screen.getByTestId("widget-add-pass-rate"));
    expect(screen.getByTestId("dashboard-grid")).toBeInTheDocument();
    // Pass Rate widget body
    expect(screen.getByText("98.7%")).toBeInTheDocument();
  });

  it("removes a widget when × clicked", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/dashboards/page");
    render(<Page />);
    fireEvent.change(screen.getByTestId("dashboard-new-name-input"), { target: { value: "D" } });
    fireEvent.click(screen.getByTestId("dashboard-create-btn"));
    fireEvent.click(screen.getByTestId("dashboard-add-widget-btn"));
    fireEvent.click(screen.getByTestId("widget-add-execution-count"));

    // Find the dynamically-id'd widget
    const widget = screen.getByText("147").closest('[data-testid^="widget-"]');
    expect(widget).toBeInTheDocument();
    const removeBtn = widget!.querySelector('[data-testid^="widget-remove-"]') as HTMLButtonElement;
    fireEvent.click(removeBtn);
    expect(screen.getByTestId("dashboard-no-widgets")).toBeInTheDocument();
  });

  it("can switch between multiple dashboards via tabs", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/dashboards/page");
    render(<Page />);
    fireEvent.change(screen.getByTestId("dashboard-new-name-input"), { target: { value: "Alpha" } });
    fireEvent.click(screen.getByTestId("dashboard-create-btn"));
    fireEvent.change(screen.getByTestId("dashboard-new-name-input"), { target: { value: "Beta" } });
    fireEvent.click(screen.getByTestId("dashboard-create-btn"));

    expect(screen.getByTestId("dashboard-tabs")).toBeInTheDocument();
    // Alpha appears in tabs only; Beta in tab + active heading
    expect(screen.getAllByText("Alpha").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Beta").length).toBeGreaterThanOrEqual(1);
  });

  it("renames dashboard when name clicked + new value entered", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/dashboards/page");
    render(<Page />);
    fireEvent.change(screen.getByTestId("dashboard-new-name-input"), { target: { value: "Original" } });
    fireEvent.click(screen.getByTestId("dashboard-create-btn"));

    fireEvent.click(screen.getByTestId("dashboard-name"));
    const input = screen.getByTestId("dashboard-rename-input");
    fireEvent.change(input, { target: { value: "Renamed" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(screen.getByTestId("dashboard-name")).toHaveTextContent("Renamed");
  });

  it("persists dashboards across mount", async () => {
    // Pre-populate localStorage
    localStorage.setItem(
      "neurex_dashboards_v1",
      JSON.stringify([
        {
          id: "dash-test",
          name: "Persisted",
          widgets: [],
          createdAt: 0,
          updatedAt: 0,
        },
      ]),
    );
    const { default: Page } = await import("../(dashboard)/p/[projectId]/dashboards/page");
    render(<Page />);
    expect(screen.getAllByText("Persisted").length).toBeGreaterThanOrEqual(1);
  });

  it("deletes dashboard when confirmation accepted", async () => {
    const { default: Page } = await import("../(dashboard)/p/[projectId]/dashboards/page");
    render(<Page />);
    fireEvent.change(screen.getByTestId("dashboard-new-name-input"), { target: { value: "ToDelete" } });
    fireEvent.click(screen.getByTestId("dashboard-create-btn"));
    fireEvent.click(screen.getByTestId("dashboard-delete-btn"));
    expect(screen.queryByText("ToDelete")).not.toBeInTheDocument();
    expect(screen.getByTestId("dashboard-empty")).toBeInTheDocument();
  });
});
