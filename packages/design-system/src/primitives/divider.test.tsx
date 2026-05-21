import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Divider } from "./divider";

describe("Divider", () => {
  it("renders horizontal by default", () => {
    render(<Divider />);
    expect(screen.getByRole("separator")).toHaveAttribute("aria-orientation", "horizontal");
  });

  it("renders vertical", () => {
    render(<Divider orientation="vertical" />);
    expect(screen.getByRole("separator")).toHaveAttribute("aria-orientation", "vertical");
  });

  it("renders label in middle", () => {
    render(<Divider label="VEYA" />);
    expect(screen.getByText("VEYA")).toBeInTheDocument();
  });

  it("uses subtle border when subtle prop set", () => {
    const { container } = render(<Divider subtle />);
    expect(container.querySelector(".border-border\\/40")).toBeInTheDocument();
  });
});
