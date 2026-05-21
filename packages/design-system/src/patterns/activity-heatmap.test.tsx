import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ActivityHeatmap } from "./activity-heatmap";

function daysAgoISO(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

describe("ActivityHeatmap", () => {
  it("renders without crashing with empty data", () => {
    render(<ActivityHeatmap data={[]} />);
  });

  it("renders correct number of grid cells (weeks × 7)", () => {
    const { container } = render(<ActivityHeatmap data={[]} weeks={4} />);
    // Each cell is a span with "h-2.5 w-2.5 rounded-sm"
    const cells = container.querySelectorAll("span.h-2\\.5.w-2\\.5.rounded-sm");
    // 4 weeks × 7 days = 28 cells
    expect(cells.length).toBeGreaterThanOrEqual(28);
  });

  it("renders title", () => {
    render(<ActivityHeatmap data={[]} title="Koşu Geçmişi" />);
    expect(screen.getByText("Koşu Geçmişi")).toBeInTheDocument();
  });

  it("renders legend text 'az' and 'çok'", () => {
    render(<ActivityHeatmap data={[]} />);
    expect(screen.getByText("az")).toBeInTheDocument();
    expect(screen.getByText("çok")).toBeInTheDocument();
  });

  it("renders total count in subtitle", () => {
    const data = [{ date: daysAgoISO(1), value: 7 }];
    render(<ActivityHeatmap data={data} label="test" />);
    expect(screen.getByText(/7 test/)).toBeInTheDocument();
  });

  it("renders level-0 cells (bg-surface-overlay) for days with no activity", () => {
    const { container } = render(<ActivityHeatmap data={[]} weeks={1} />);
    const level0 = container.querySelectorAll(".bg-surface-overlay.h-2\\.5");
    expect(level0.length).toBeGreaterThan(0);
  });

  it("renders higher-level cells for days with activity", () => {
    const data = [
      { date: daysAgoISO(0), value: 10 },
      { date: daysAgoISO(1), value: 20 },
    ];
    const { container } = render(<ActivityHeatmap data={data} weeks={2} />);
    // Level 4 cells use bg-brand-primary (without opacity)
    const activeCells = container.querySelectorAll(".bg-brand-primary.h-2\\.5");
    expect(activeCells.length).toBeGreaterThan(0);
  });

  it("renders 7 row divs for days of the week", () => {
    const { container } = render(<ActivityHeatmap data={[]} weeks={2} />);
    // The outer grid has one div per day-of-week (7 rows)
    const rows = container.querySelectorAll(".flex.gap-0\\.5");
    expect(rows.length).toBe(7);
  });
});
