import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Stepper } from "./stepper";

const steps = [
  { key: "1", title: "Hesap" },
  { key: "2", title: "Profil" },
  { key: "3", title: "Onay" },
];

describe("Stepper", () => {
  it("renders all steps as list items", () => {
    render(<Stepper steps={steps} active={0} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });

  it("marks current step with aria-current=step", () => {
    render(<Stepper steps={steps} active={1} />);
    const items = screen.getAllByRole("listitem");
    expect(items[1]).toHaveAttribute("aria-current", "step");
    expect(items[0]).not.toHaveAttribute("aria-current");
  });

  it("renders checkmark for completed steps", () => {
    render(<Stepper steps={steps} active={2} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toHaveTextContent("✓");
    expect(buttons[1]).toHaveTextContent("✓");
    expect(buttons[2]).toHaveTextContent("3");
  });

  it("calls onStepClick for clickable (complete) steps", () => {
    const fn = vi.fn();
    render(<Stepper steps={steps} active={2} onStepClick={fn} />);
    fireEvent.click(screen.getAllByRole("button")[0]);
    expect(fn).toHaveBeenCalledWith(0, steps[0]);
  });

  it("upcoming steps are disabled when onStepClick provided", () => {
    const fn = vi.fn();
    render(<Stepper steps={steps} active={0} onStepClick={fn} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons[2]).toBeDisabled();
    fireEvent.click(buttons[2]);
    expect(fn).not.toHaveBeenCalled();
  });

  it("error status renders ! and danger color", () => {
    const withError = [
      { key: "1", title: "OK",  status: "complete" as const },
      { key: "2", title: "Bad", status: "error" as const },
      { key: "3", title: "Next" },
    ];
    render(<Stepper steps={withError} active={1} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons[1]).toHaveTextContent("!");
  });
});
