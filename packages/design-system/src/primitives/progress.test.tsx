import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Progress } from "./progress";

describe("Progress", () => {
  it("renders with role=progressbar", () => {
    render(<Progress value={50} label="upload" />);
    expect(screen.getByRole("progressbar", { name: "upload" })).toBeInTheDocument();
  });

  it("sets aria-valuenow when value provided", () => {
    render(<Progress value={30} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "30");
  });

  it("omits aria-valuenow when indeterminate", () => {
    render(<Progress />);
    expect(screen.getByRole("progressbar")).not.toHaveAttribute("aria-valuenow");
  });

  it("respects custom max", () => {
    render(<Progress value={5} max={10} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuemax", "10");
    expect(bar).toHaveAttribute("aria-valuenow", "5");
  });

  it("clamps value to 0..100 for width", () => {
    const { container } = render(<Progress value={150} />);
    const fill = container.querySelector("span[style]") as HTMLElement;
    expect(fill?.style.width).toBe("100%");
  });

  it("renders different status colors", () => {
    const { container, rerender } = render(<Progress value={50} status="success" />);
    expect(container.querySelector(".bg-success")).toBeInTheDocument();
    rerender(<Progress value={50} status="danger" />);
    expect(container.querySelector(".bg-danger")).toBeInTheDocument();
  });
});
