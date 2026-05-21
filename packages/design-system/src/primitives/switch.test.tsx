import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Switch } from "./switch";

describe("Switch", () => {
  it("renders without label", () => {
    render(<Switch aria-label="dark mode" />);
    expect(screen.getByRole("switch", { name: "dark mode" })).toBeInTheDocument();
  });

  it("associates label with input", () => {
    render(<Switch label="Dark mode" />);
    const sw = screen.getByRole("switch", { name: "Dark mode" });
    expect(sw).toBeInTheDocument();
  });

  it("toggles on click", async () => {
    const onChange = vi.fn();
    render(<Switch aria-label="x" onChange={onChange} />);
    await userEvent.click(screen.getByRole("switch"));
    expect(onChange).toHaveBeenCalled();
  });

  it("is disabled when prop set", () => {
    render(<Switch aria-label="x" disabled />);
    expect(screen.getByRole("switch")).toBeDisabled();
  });
});
