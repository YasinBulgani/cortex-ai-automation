import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Checkbox } from "./checkbox";

describe("Checkbox", () => {
  it("renders unchecked by default", () => {
    render(<Checkbox aria-label="agree" />);
    expect(screen.getByRole("checkbox")).not.toBeChecked();
  });

  it("renders with label", () => {
    render(<Checkbox label="Şartları kabul ediyorum" />);
    expect(screen.getByRole("checkbox", { name: "Şartları kabul ediyorum" })).toBeInTheDocument();
  });

  it("toggles on click", async () => {
    const onChange = vi.fn();
    render(<Checkbox label="x" onChange={onChange} />);
    await userEvent.click(screen.getByRole("checkbox"));
    expect(onChange).toHaveBeenCalled();
  });

  it("supports indeterminate state", () => {
    const ref = { current: null as HTMLInputElement | null };
    render(<Checkbox aria-label="x" ref={ref} indeterminate />);
    expect(ref.current?.indeterminate).toBe(true);
  });

  it("flags invalid via aria-invalid", () => {
    render(<Checkbox aria-label="x" invalid />);
    expect(screen.getByRole("checkbox")).toHaveAttribute("aria-invalid", "true");
  });
});
