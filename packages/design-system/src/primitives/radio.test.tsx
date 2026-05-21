import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Radio, RadioGroup } from "./radio";

describe("Radio", () => {
  it("renders with label", () => {
    render(<Radio name="x" value="a" label="Option A" />);
    expect(screen.getByRole("radio", { name: "Option A" })).toBeInTheDocument();
  });

  it("calls onChange on click", async () => {
    const onChange = vi.fn();
    render(<Radio name="x" value="a" label="A" onChange={onChange} />);
    await userEvent.click(screen.getByRole("radio"));
    expect(onChange).toHaveBeenCalled();
  });
});

describe("RadioGroup", () => {
  const options = [
    { value: "a", label: "Alpha" },
    { value: "b", label: "Bravo" },
    { value: "c", label: "Charlie", disabled: true },
  ];

  it("renders all options as radios", () => {
    render(<RadioGroup name="t" options={options} />);
    expect(screen.getAllByRole("radio")).toHaveLength(3);
  });

  it("respects controlled value", () => {
    render(<RadioGroup name="t" options={options} value="b" />);
    expect(screen.getByRole("radio", { name: "Bravo" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Alpha" })).not.toBeChecked();
  });

  it("calls onValueChange on selection", async () => {
    const fn = vi.fn();
    render(<RadioGroup name="t" options={options} onValueChange={fn} />);
    await userEvent.click(screen.getByRole("radio", { name: "Alpha" }));
    expect(fn).toHaveBeenCalledWith("a");
  });

  it("disables specific options", () => {
    render(<RadioGroup name="t" options={options} />);
    expect(screen.getByRole("radio", { name: "Charlie" })).toBeDisabled();
  });

  it("disables all when group disabled", () => {
    render(<RadioGroup name="t" options={options} disabled />);
    screen.getAllByRole("radio").forEach(r => expect(r).toBeDisabled());
  });
});
