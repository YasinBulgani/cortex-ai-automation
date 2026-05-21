import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Kbd, KbdGroup } from "./kbd";

describe("Kbd", () => {
  it("renders as kbd element", () => {
    const { container } = render(<Kbd>K</Kbd>);
    expect(container.querySelector("kbd")).toBeInTheDocument();
    expect(container.querySelector("kbd")?.textContent).toBe("K");
  });

  it("renders text content", () => {
    render(<Kbd>Ctrl</Kbd>);
    expect(screen.getByText("Ctrl")).toBeInTheDocument();
  });

  it("applies sm size class", () => {
    const { container } = render(<Kbd size="sm">X</Kbd>);
    const kbd = container.querySelector("kbd");
    expect(kbd?.className).toContain("text-[10px]");
  });

  it("applies md size class by default", () => {
    const { container } = render(<Kbd>X</Kbd>);
    const kbd = container.querySelector("kbd");
    expect(kbd?.className).toContain("text-[11px]");
  });

  it("passes additional className", () => {
    const { container } = render(<Kbd className="custom-class">X</Kbd>);
    expect(container.querySelector("kbd")?.className).toContain("custom-class");
  });
});

describe("KbdGroup", () => {
  it("renders children", () => {
    render(
      <KbdGroup>
        <Kbd>⌘</Kbd>
        <Kbd>K</Kbd>
      </KbdGroup>,
    );
    expect(screen.getByText("⌘")).toBeInTheDocument();
    expect(screen.getByText("K")).toBeInTheDocument();
  });

  it("wraps in a span", () => {
    const { container } = render(<KbdGroup><Kbd>A</Kbd></KbdGroup>);
    expect(container.querySelector("span")).toBeInTheDocument();
  });
});
