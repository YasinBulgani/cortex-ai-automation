import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Accordion } from "./accordion";

const items = [
  { value: "a", title: "Alpha", content: <span>A content</span> },
  { value: "b", title: "Bravo", content: <span>B content</span> },
  { value: "c", title: "Charlie", content: <span>C content</span> },
];

describe("Accordion", () => {
  it("renders all triggers collapsed by default (single)", () => {
    render(<Accordion items={items} />);
    const triggers = screen.getAllByRole("button");
    expect(triggers).toHaveLength(3);
    triggers.forEach(t => expect(t).toHaveAttribute("aria-expanded", "false"));
    expect(screen.queryByText("A content")).not.toBeInTheDocument();
  });

  it("expands clicked item (single)", () => {
    render(<Accordion items={items} />);
    fireEvent.click(screen.getByRole("button", { name: "Alpha" }));
    expect(screen.getByText("A content")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Alpha" })).toHaveAttribute("aria-expanded", "true");
  });

  it("collapses on second click when collapsible=true (default)", () => {
    render(<Accordion items={items} />);
    fireEvent.click(screen.getByRole("button", { name: "Alpha" }));
    fireEvent.click(screen.getByRole("button", { name: "Alpha" }));
    expect(screen.queryByText("A content")).not.toBeInTheDocument();
  });

  it("stays open when collapsible=false", () => {
    render(<Accordion items={items} collapsible={false} defaultValue="a" />);
    fireEvent.click(screen.getByRole("button", { name: "Alpha" }));
    expect(screen.getByText("A content")).toBeInTheDocument();
  });

  it("multiple type allows several open", () => {
    render(<Accordion items={items} type="multiple" />);
    fireEvent.click(screen.getByRole("button", { name: "Alpha" }));
    fireEvent.click(screen.getByRole("button", { name: "Bravo" }));
    expect(screen.getByText("A content")).toBeInTheDocument();
    expect(screen.getByText("B content")).toBeInTheDocument();
  });

  it("calls onValueChange on toggle", () => {
    const fn = vi.fn();
    render(<Accordion items={items} onValueChange={fn} />);
    fireEvent.click(screen.getByRole("button", { name: "Bravo" }));
    expect(fn).toHaveBeenCalledWith("b");
  });

  it("disabled item cannot be toggled", () => {
    const fn = vi.fn();
    render(
      <Accordion
        items={[{ value: "x", title: "X", content: <span>X</span>, disabled: true }]}
        onValueChange={fn}
      />,
    );
    fireEvent.click(screen.getByRole("button"));
    expect(fn).not.toHaveBeenCalled();
  });
});
