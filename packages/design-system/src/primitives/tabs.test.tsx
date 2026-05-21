import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Tabs, TabPanel } from "./tabs";

const items = [
  { value: "a", label: "Alpha" },
  { value: "b", label: "Bravo" },
  { value: "c", label: "Charlie", disabled: true },
  { value: "d", label: "Delta" },
];

describe("Tabs", () => {
  it("renders tabs with role + first selected by default", () => {
    render(<Tabs items={items} label="x" />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(4);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(tabs[1]).toHaveAttribute("aria-selected", "false");
  });

  it("honors defaultValue", () => {
    render(<Tabs items={items} defaultValue="b" />);
    expect(screen.getByRole("tab", { name: "Bravo" })).toHaveAttribute("aria-selected", "true");
  });

  it("calls onValueChange and updates selection (uncontrolled)", () => {
    const onChange = vi.fn();
    render(<Tabs items={items} onValueChange={onChange} />);
    fireEvent.click(screen.getByRole("tab", { name: "Bravo" }));
    expect(onChange).toHaveBeenCalledWith("b");
    expect(screen.getByRole("tab", { name: "Bravo" })).toHaveAttribute("aria-selected", "true");
  });

  it("respects controlled value (does not change without onValueChange wiring)", () => {
    const { rerender } = render(<Tabs items={items} value="a" onValueChange={() => {}} />);
    fireEvent.click(screen.getByRole("tab", { name: "Bravo" }));
    expect(screen.getByRole("tab", { name: "Alpha" })).toHaveAttribute("aria-selected", "true");
    rerender(<Tabs items={items} value="d" onValueChange={() => {}} />);
    expect(screen.getByRole("tab", { name: "Delta" })).toHaveAttribute("aria-selected", "true");
  });

  it("skips disabled tabs with arrow keys", () => {
    render(<Tabs items={items} defaultValue="b" />);
    const bravo = screen.getByRole("tab", { name: "Bravo" });
    bravo.focus();
    fireEvent.keyDown(bravo, { key: "ArrowRight" });
    expect(screen.getByRole("tab", { name: "Delta" })).toHaveAttribute("aria-selected", "true");
  });

  it("Home/End jump to first/last enabled", () => {
    render(<Tabs items={items} defaultValue="b" />);
    const bravo = screen.getByRole("tab", { name: "Bravo" });
    bravo.focus();
    fireEvent.keyDown(bravo, { key: "End" });
    expect(screen.getByRole("tab", { name: "Delta" })).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(screen.getByRole("tab", { name: "Delta" }), { key: "Home" });
    expect(screen.getByRole("tab", { name: "Alpha" })).toHaveAttribute("aria-selected", "true");
  });
});

describe("TabPanel", () => {
  it("renders content when value matches active", () => {
    render(<TabPanel value="a" activeValue="a">content</TabPanel>);
    expect(screen.getByRole("tabpanel")).toHaveTextContent("content");
  });

  it("hides content when value differs", () => {
    render(<TabPanel value="a" activeValue="b">content</TabPanel>);
    expect(screen.queryByText("content")).not.toBeInTheDocument();
  });
});
