import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Spinner } from "./spinner";

describe("Spinner", () => {
  it("renders with default label and status role", () => {
    render(<Spinner />);
    expect(screen.getByRole("status", { name: "Yükleniyor" })).toBeInTheDocument();
  });

  it("hides from a11y when label=null", () => {
    const { container } = render(<Spinner label={null} />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden");
    expect(svg).not.toHaveAttribute("role");
  });

  it("respects numeric size", () => {
    const { container } = render(<Spinner size={48} />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("width", "48");
    expect(svg).toHaveAttribute("height", "48");
  });

  it("respects keyword size", () => {
    const { container } = render(<Spinner size="xs" />);
    expect(container.querySelector("svg")).toHaveAttribute("width", "12");
  });
});
