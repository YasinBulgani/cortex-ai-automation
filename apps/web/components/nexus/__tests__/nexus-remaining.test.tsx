/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

import { EmptyState } from "../EmptyState";
import { MetricRow } from "../MetricRow";
import { PageHeader } from "../PageHeader";
import { ProgressBar } from "../ProgressBar";
import { StatusBadge } from "../StatusBadge";
import { TrendBadge } from "../TrendBadge";

// ---------------------------------------------------------------------------
// 1. EmptyState
// ---------------------------------------------------------------------------
describe("EmptyState", () => {
  it("renders title text", () => {
    render(<EmptyState title="No results found" />);
    expect(screen.getByText("No results found")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(<EmptyState title="Empty" description="Nothing here yet." />);
    expect(screen.getByText("Nothing here yet.")).toBeInTheDocument();
  });

  it("renders action when provided", () => {
    render(
      <EmptyState title="Empty" action={<button>Create new</button>} />
    );
    expect(screen.getByRole("button", { name: "Create new" })).toBeInTheDocument();
  });

  it("renders SVG icon for known key 'folder'", () => {
    const { container } = render(<EmptyState icon="folder" title="Folder" />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    // The path inside SVG should have the folder path data
    const path = container.querySelector("path");
    expect(path).not.toBeNull();
    expect(path!.getAttribute("d")).toContain("M3 7a2 2 0 012-2h4");
  });

  it("renders emoji as text for unknown key like '🚀'", () => {
    const { container } = render(<EmptyState icon="🚀" title="Launch" />);
    // Should NOT render an SVG
    expect(container.querySelector("svg")).toBeNull();
    // The emoji div should be in the DOM
    expect(container.textContent).toContain("🚀");
  });

  it("renders without description/action (minimal props)", () => {
    const { container } = render(<EmptyState title="Minimal" />);
    expect(screen.getByText("Minimal")).toBeInTheDocument();
    // description paragraph should not be present
    expect(container.querySelector("p")).toBeNull();
    // action wrapper should not be present (no extra div after title)
    const buttons = container.querySelectorAll("button");
    expect(buttons.length).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// 2. MetricRow
// ---------------------------------------------------------------------------
describe("MetricRow", () => {
  it("renders children", () => {
    render(
      <MetricRow>
        <div>Child One</div>
        <div>Child Two</div>
      </MetricRow>
    );
    expect(screen.getByText("Child One")).toBeInTheDocument();
    expect(screen.getByText("Child Two")).toBeInTheDocument();
  });

  it("applies default grid columns (cols=4 → grid-cols-2)", () => {
    const { container } = render(
      <MetricRow>
        <div>A</div>
      </MetricRow>
    );
    const grid = container.firstChild as HTMLElement;
    expect(grid.className).toContain("grid-cols-2");
  });

  it("applies custom className", () => {
    const { container } = render(
      <MetricRow className="my-custom-class">
        <div>A</div>
      </MetricRow>
    );
    const grid = container.firstChild as HTMLElement;
    expect(grid.className).toContain("my-custom-class");
  });

  it("renders with cols=2 (contains 'grid-cols-1')", () => {
    const { container } = render(
      <MetricRow cols={2}>
        <div>A</div>
      </MetricRow>
    );
    const grid = container.firstChild as HTMLElement;
    expect(grid.className).toContain("grid-cols-1");
  });

  it("renders with gap='sm' (contains 'gap-2')", () => {
    const { container } = render(
      <MetricRow gap="sm">
        <div>A</div>
      </MetricRow>
    );
    const grid = container.firstChild as HTMLElement;
    expect(grid.className).toContain("gap-2");
  });
});

// ---------------------------------------------------------------------------
// 3. PageHeader
// ---------------------------------------------------------------------------
describe("PageHeader", () => {
  it("renders title as h1", () => {
    render(<PageHeader title="Dashboard" />);
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading).toBeInTheDocument();
    expect(heading).toHaveTextContent("Dashboard");
  });

  it("renders description when provided", () => {
    render(<PageHeader title="Dashboard" description="Overview of metrics" />);
    expect(screen.getByText("Overview of metrics")).toBeInTheDocument();
  });

  it("renders right slot content", () => {
    render(
      <PageHeader title="Dashboard" right={<button>Export</button>} />
    );
    expect(screen.getByRole("button", { name: "Export" })).toBeInTheDocument();
  });

  it("renders badge next to title", () => {
    render(
      <PageHeader title="Dashboard" badge={<span>Beta</span>} />
    );
    expect(screen.getByText("Beta")).toBeInTheDocument();
    // Badge should be inside the same flex container as the h1
    const heading = screen.getByRole("heading", { level: 1 });
    const badgeEl = screen.getByText("Beta");
    expect(heading.parentElement!.contains(badgeEl)).toBe(true);
  });

  it("renders icon slot", () => {
    render(
      <PageHeader title="Dashboard" icon={<svg data-testid="header-icon" />} />
    );
    expect(screen.getByTestId("header-icon")).toBeInTheDocument();
  });

  it("renders without optional props", () => {
    const { container } = render(<PageHeader title="Bare" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Bare");
    // No description paragraph
    expect(container.querySelector("p")).toBeNull();
    // No right slot buttons
    expect(container.querySelectorAll("button").length).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// 4. ProgressBar
// ---------------------------------------------------------------------------
describe("ProgressBar", () => {
  it("renders without crash in simple mode (value=75)", () => {
    const { container } = render(<ProgressBar value={75} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("in simple mode, the progress div has inline style width '75%'", () => {
    const { container } = render(<ProgressBar value={75} />);
    // Structure: RTL-wrapper > div.w-full > div.track > div.bar[style]
    const inner = container.querySelector<HTMLElement>("[style]");
    expect(inner).not.toBeNull();
    expect(inner!.style.width).toBe("75%");
  });

  it("showLabel=true renders the percentage text", () => {
    render(<ProgressBar value={60} showLabel />);
    expect(screen.getByText("60%")).toBeInTheDocument();
  });

  it("in segmented mode (total=10, passed=7, failed=2, skipped=1) renders multiple colored segments", () => {
    const { container } = render(
      <ProgressBar total={10} passed={7} failed={2} skipped={1} />
    );
    // Three colored segments should appear inside the track
    const segments = container.querySelectorAll<HTMLElement>("div[style]");
    // At least 3 segments with non-zero widths
    const withWidth = Array.from(segments).filter(
      (el) => el.style.width && el.style.width !== "0%"
    );
    expect(withWidth.length).toBeGreaterThanOrEqual(3);
  });

  it("segmented mode with showLabel shows '7 geçti'", () => {
    render(
      <ProgressBar total={10} passed={7} failed={2} skipped={1} showLabel />
    );
    expect(screen.getByText("7 geçti")).toBeInTheDocument();
  });

  it("value is clamped to 0-100 (value=150 → 100%)", () => {
    const { container } = render(<ProgressBar value={150} showLabel />);
    expect(screen.getByText("100%")).toBeInTheDocument();
    // The bar div carries the inline width style
    const inner = container.querySelector<HTMLElement>("[style]");
    expect(inner!.style.width).toBe("100%");
  });
});

// ---------------------------------------------------------------------------
// 5. StatusBadge
// ---------------------------------------------------------------------------
describe("StatusBadge", () => {
  it("renders 'Aktif' for status='active'", () => {
    render(<StatusBadge status="active" />);
    expect(screen.getByText("Aktif")).toBeInTheDocument();
  });

  it("renders 'Koşuyor' for status='running'", () => {
    render(<StatusBadge status="running" />);
    expect(screen.getByText("Koşuyor")).toBeInTheDocument();
  });

  it("renders 'Hata' for status='error'", () => {
    render(<StatusBadge status="error" />);
    expect(screen.getByText("Hata")).toBeInTheDocument();
  });

  it("renders custom label when label prop provided", () => {
    render(<StatusBadge status="active" label="Custom Label" />);
    expect(screen.getByText("Custom Label")).toBeInTheDocument();
    expect(screen.queryByText("Aktif")).toBeNull();
  });

  it("dot=false hides the dot span", () => {
    const { container } = render(<StatusBadge status="active" dot={false} />);
    // The dot is a w-1.5 h-1.5 rounded-full span; with dot=false it should not exist
    const dotSpan = container.querySelector("span > span");
    expect(dotSpan).toBeNull();
  });

  it("unknown status renders the status string as label", () => {
    render(<StatusBadge status="my-custom-status" />);
    expect(screen.getByText("my-custom-status")).toBeInTheDocument();
  });

  it("renders 'Tamamlandı' for status='completed'", () => {
    render(<StatusBadge status="completed" />);
    expect(screen.getByText("Tamamlandı")).toBeInTheDocument();
  });

  it("renders 'Bekliyor' for status='pending'", () => {
    render(<StatusBadge status="pending" />);
    expect(screen.getByText("Bekliyor")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 6. TrendBadge
// ---------------------------------------------------------------------------
describe("TrendBadge", () => {
  it("positive value shows '↑' arrow and '+X%'", () => {
    render(<TrendBadge value={10} />);
    expect(screen.getByText("↑")).toBeInTheDocument();
    expect(screen.getByText("+10%")).toBeInTheDocument();
  });

  it("negative value shows '↓' arrow", () => {
    render(<TrendBadge value={-5} />);
    expect(screen.getByText("↓")).toBeInTheDocument();
  });

  it("zero shows '→' arrow", () => {
    render(<TrendBadge value={0} />);
    expect(screen.getByText("→")).toBeInTheDocument();
  });

  it("custom label overrides computed label", () => {
    render(<TrendBadge value={10} label="Improved" />);
    expect(screen.getByText("Improved")).toBeInTheDocument();
    expect(screen.queryByText("+10%")).toBeNull();
  });

  it("direction='down' overrides sign (positive value but down direction)", () => {
    render(<TrendBadge value={5} direction="down" />);
    // Icon should be ↓ regardless of positive value
    expect(screen.getByText("↓")).toBeInTheDocument();
  });

  it("integer value shows no decimal (value=12 → '+12%')", () => {
    render(<TrendBadge value={12} />);
    expect(screen.getByText("+12%")).toBeInTheDocument();
  });

  it("float value shows 1 decimal (value=3.14 → '+3.1%')", () => {
    render(<TrendBadge value={3.14} />);
    expect(screen.getByText("+3.1%")).toBeInTheDocument();
  });
});
