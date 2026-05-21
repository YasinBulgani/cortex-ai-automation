import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Sparkline } from "./sparkline";

describe("Sparkline", () => {
  it("renders SVG for valid data", () => {
    const { container } = render(<Sparkline data={[1, 2, 3, 4, 5]} />);
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("renders fallback for insufficient data (< 2 points)", () => {
    const { container } = render(<Sparkline data={[5]} ariaLabel="not enough" />);
    expect(container.querySelector("svg")).not.toBeInTheDocument();
    expect(container.textContent).toContain("—");
  });

  it("renders fallback for empty data", () => {
    const { container } = render(<Sparkline data={[]} />);
    expect(container.querySelector("svg")).not.toBeInTheDocument();
  });

  it("sets aria-label on SVG", () => {
    const { container } = render(<Sparkline data={[1, 2, 3]} ariaLabel="Trend" />);
    expect(container.querySelector("svg")?.getAttribute("aria-label")).toBe("Trend");
  });

  it("respects width and height props on SVG", () => {
    const { container } = render(<Sparkline data={[1, 2, 3]} width={100} height={40} />);
    const svg = container.querySelector("svg");
    expect(svg?.getAttribute("width")).toBe("100");
    expect(svg?.getAttribute("height")).toBe("40");
  });

  it("renders area variant with path element", () => {
    const { container } = render(<Sparkline data={[1, 3, 2, 4, 3]} variant="area" />);
    expect(container.querySelectorAll("path").length).toBeGreaterThan(0);
  });

  it("renders bar variant with rect elements", () => {
    const { container } = render(<Sparkline data={[1, 3, 2, 4]} variant="bar" />);
    expect(container.querySelectorAll("rect").length).toBeGreaterThan(0);
  });

  it("renders last point dot when showLast=true (default)", () => {
    const { container } = render(<Sparkline data={[1, 2, 3, 4]} showLast />);
    expect(container.querySelector("circle")).toBeInTheDocument();
  });

  it("omits last point dot when showLast=false", () => {
    const { container } = render(<Sparkline data={[1, 2, 3, 4]} showLast={false} />);
    expect(container.querySelector("circle")).not.toBeInTheDocument();
  });
});
