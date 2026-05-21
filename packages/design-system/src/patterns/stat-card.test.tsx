import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatCard } from "./stat-card";

describe("StatCard", () => {
  it("renders label and value", () => {
    render(<StatCard label="Test Sayısı" value={42} />);
    expect(screen.getByText("Test Sayısı")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders hint text", () => {
    render(<StatCard label="Pass Rate" value="%94" hint="son 7 gün" />);
    expect(screen.getByText("son 7 gün")).toBeInTheDocument();
  });

  it("renders positive trend with ▲", () => {
    render(<StatCard label="L" value="V" trend={12} />);
    expect(screen.getByText(/▲.*12%/)).toBeInTheDocument();
  });

  it("renders negative trend with ▼", () => {
    render(<StatCard label="L" value="V" trend={-5} />);
    expect(screen.getByText(/▼.*5%/)).toBeInTheDocument();
  });

  it("renders zero trend with — symbol", () => {
    const { container } = render(<StatCard label="L" value="V" trend={0} />);
    // trend=0 renders "—0%" inside one span; use innerHTML check
    expect(container.textContent).toContain("—");
    expect(container.textContent).toContain("0%");
  });

  it("renders icon when provided", () => {
    render(<StatCard label="L" value="V" icon={<span data-testid="ic">🚀</span>} />);
    expect(screen.getByTestId("ic")).toBeInTheDocument();
  });

  it("renders loading skeleton instead of value", () => {
    const { container } = render(<StatCard label="L" value="V" loading />);
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
    expect(screen.queryByText("V")).not.toBeInTheDocument();
  });

  it("renders as button when onClick provided", () => {
    render(<StatCard label="L" value="V" onClick={() => {}} />);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("renders as div when no onClick", () => {
    const { container } = render(<StatCard label="L" value="V" />);
    expect(container.querySelector("div")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders sparkline when data provided", () => {
    const { container } = render(
      <StatCard label="L" value="V" sparkline={[1, 2, 3, 4, 5]} />,
    );
    expect(container.querySelector("svg")).toBeInTheDocument();
  });
});
