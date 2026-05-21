/** @jest-environment jsdom */
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

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

beforeEach(() => {
  ls.clear();
});

// ── CoverageHeatmap ───────────────────────────────────────────────────────

describe("CoverageHeatmap", () => {
  it("renders empty state when no modules", async () => {
    const { CoverageHeatmap } = await import("@/components/CoverageHeatmap");
    render(<CoverageHeatmap modules={[]} testTypes={[]} cells={[]} />);
    expect(screen.getByTestId("coverage-heatmap-empty")).toBeInTheDocument();
  });

  it("renders cells in grid", async () => {
    const { CoverageHeatmap } = await import("@/components/CoverageHeatmap");
    render(
      <CoverageHeatmap
        modules={["auth", "billing"]}
        testTypes={["unit", "e2e"]}
        cells={[
          { module: "auth", testType: "unit", coveragePct: 90, testCount: 12 },
          { module: "billing", testType: "e2e", coveragePct: 35, testCount: 4 },
        ]}
      />,
    );
    expect(screen.getByTestId("coverage-heatmap")).toBeInTheDocument();
    expect(screen.getByTestId("heatmap-cell-auth-unit")).toHaveTextContent("90");
    expect(screen.getByTestId("heatmap-cell-billing-e2e")).toHaveTextContent("35");
  });

  it("shows empty placeholder for unspecified cells", async () => {
    const { CoverageHeatmap } = await import("@/components/CoverageHeatmap");
    render(
      <CoverageHeatmap
        modules={["auth"]}
        testTypes={["unit", "e2e"]}
        cells={[
          { module: "auth", testType: "unit", coveragePct: 80, testCount: 5 },
        ]}
      />,
    );
    expect(screen.getByTestId("heatmap-cell-auth-e2e-empty")).toBeInTheDocument();
  });
});

// ── DataParameterTable ────────────────────────────────────────────────────

describe("DataParameterTable", () => {
  it("renders empty row state", async () => {
    const { DataParameterTable } = await import("@/components/DataParameterTable");
    render(<DataParameterTable />);
    expect(screen.getByTestId("data-param-empty")).toBeInTheDocument();
  });

  it("adds row via + Satır button", async () => {
    const { DataParameterTable } = await import("@/components/DataParameterTable");
    render(<DataParameterTable />);
    fireEvent.click(screen.getByTestId("data-param-add-row"));
    expect(screen.getByTestId("data-param-row-0")).toBeInTheDocument();
  });

  it("removes row via X button", async () => {
    const { DataParameterTable } = await import("@/components/DataParameterTable");
    render(<DataParameterTable />);
    fireEvent.click(screen.getByTestId("data-param-add-row"));
    fireEvent.click(screen.getByTestId("data-param-add-row"));
    fireEvent.click(screen.getByTestId("data-param-remove-row-0"));
    expect(screen.queryByTestId("data-param-row-1")).not.toBeInTheDocument();
  });

  it("updates cell value", async () => {
    const { DataParameterTable } = await import("@/components/DataParameterTable");
    render(<DataParameterTable />);
    fireEvent.click(screen.getByTestId("data-param-add-row"));
    const input = screen.getByTestId("data-param-cell-0-param1") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "test-value" } });
    expect(input.value).toBe("test-value");
  });

  it("calls onChange when cell updated", async () => {
    const { DataParameterTable } = await import("@/components/DataParameterTable");
    const onChange = jest.fn();
    render(<DataParameterTable onChange={onChange} />);
    fireEvent.click(screen.getByTestId("data-param-add-row"));
    fireEvent.change(screen.getByTestId("data-param-cell-0-param1"), { target: { value: "v1" } });
    expect(onChange).toHaveBeenCalled();
  });

  it("persists to localStorage when storageKey set", async () => {
    const { DataParameterTable } = await import("@/components/DataParameterTable");
    render(<DataParameterTable storageKey="test-key" />);
    fireEvent.click(screen.getByTestId("data-param-add-row"));
    fireEvent.change(screen.getByTestId("data-param-cell-0-param1"), { target: { value: "x" } });
    const stored = localStorage.getItem("test-key");
    expect(stored).toBeTruthy();
    expect(stored).toContain("x");
  });

  it("loads from localStorage on mount", async () => {
    localStorage.setItem(
      "test-key-2",
      JSON.stringify({
        columns: ["foo"],
        rows: [{ foo: "loaded-val" }],
      }),
    );
    const { DataParameterTable } = await import("@/components/DataParameterTable");
    render(<DataParameterTable storageKey="test-key-2" />);
    const input = screen.getByTestId("data-param-cell-0-foo") as HTMLInputElement;
    expect(input.value).toBe("loaded-val");
  });

  it("imports CSV via textarea", async () => {
    const { DataParameterTable } = await import("@/components/DataParameterTable");
    render(<DataParameterTable />);
    const ta = screen.getByTestId("data-param-csv-input") as HTMLTextAreaElement;
    fireEvent.change(ta, { target: { value: "a,b\n1,2\n3,4" } });
    fireEvent.blur(ta);
    // Two rows should now exist
    expect(screen.getByTestId("data-param-row-0")).toBeInTheDocument();
    expect(screen.getByTestId("data-param-row-1")).toBeInTheDocument();
  });
});

// ── classifyRoi (utility) ─────────────────────────────────────────────────

describe("classifyRoi + roiBadgeClass", () => {
  it("high-value when roi > 5", async () => {
    const { classifyRoi } = await import("@/lib/useTestEconomics");
    expect(classifyRoi(10)).toBe("high-value");
    expect(classifyRoi(6)).toBe("high-value");
  });

  it("neutral when roi 1-5", async () => {
    const { classifyRoi } = await import("@/lib/useTestEconomics");
    expect(classifyRoi(3)).toBe("neutral");
    expect(classifyRoi(1)).toBe("neutral");
  });

  it("wasteful when roi < 1", async () => {
    const { classifyRoi } = await import("@/lib/useTestEconomics");
    expect(classifyRoi(0.5)).toBe("wasteful");
    expect(classifyRoi(0)).toBe("wasteful");
  });

  it("roiBadgeClass returns distinct classes", async () => {
    const { roiBadgeClass } = await import("@/lib/useTestEconomics");
    expect(roiBadgeClass("high-value")).toContain("emerald");
    expect(roiBadgeClass("neutral")).toContain("slate");
    expect(roiBadgeClass("wasteful")).toContain("red");
  });
});

// ── coverageColorClass ────────────────────────────────────────────────────

describe("coverageColorClass", () => {
  it("emerald for 85+%", async () => {
    const { coverageColorClass } = await import("@/lib/useTraceabilityMatrix");
    expect(coverageColorClass(85)).toContain("emerald");
    expect(coverageColorClass(100)).toContain("emerald");
  });

  it("yellow for 60-84%", async () => {
    const { coverageColorClass } = await import("@/lib/useTraceabilityMatrix");
    expect(coverageColorClass(60)).toContain("yellow");
    expect(coverageColorClass(80)).toContain("yellow");
  });

  it("amber for 30-59%", async () => {
    const { coverageColorClass } = await import("@/lib/useTraceabilityMatrix");
    expect(coverageColorClass(30)).toContain("amber");
    expect(coverageColorClass(50)).toContain("amber");
  });

  it("red for < 30%", async () => {
    const { coverageColorClass } = await import("@/lib/useTraceabilityMatrix");
    expect(coverageColorClass(0)).toContain("red");
    expect(coverageColorClass(29)).toContain("red");
  });
});
