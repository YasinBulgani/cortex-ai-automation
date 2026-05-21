import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Rating } from "./rating";

describe("Rating - interactive", () => {
  it("renders default 5 stars", () => {
    const { container } = render(<Rating defaultValue={3} />);
    expect(container.querySelectorAll("button")).toHaveLength(5);
  });

  it("respects custom max", () => {
    const { container } = render(<Rating defaultValue={2} max={7} />);
    expect(container.querySelectorAll("button")).toHaveLength(7);
  });

  it("role=slider when interactive", () => {
    render(<Rating defaultValue={3} label="puan" />);
    expect(screen.getByRole("slider", { name: "puan" })).toBeInTheDocument();
  });

  it("aria-valuenow reflects current", () => {
    render(<Rating defaultValue={3} />);
    expect(screen.getByRole("slider")).toHaveAttribute("aria-valuenow", "3");
  });

  it("click sets new value", () => {
    const fn = vi.fn();
    const { container } = render(<Rating defaultValue={0} onValueChange={fn} />);
    const buttons = container.querySelectorAll("button");
    fireEvent.click(buttons[2]);
    expect(fn).toHaveBeenCalledWith(3);
  });

  it("clicking same value clears (toggle to zero)", () => {
    const fn = vi.fn();
    const { container } = render(<Rating defaultValue={3} onValueChange={fn} />);
    const buttons = container.querySelectorAll("button");
    fireEvent.click(buttons[2]); // value=3 → clicked star #3
    expect(fn).toHaveBeenCalledWith(0);
  });

  it("ArrowRight increments", () => {
    const fn = vi.fn();
    render(<Rating defaultValue={2} onValueChange={fn} />);
    fireEvent.keyDown(screen.getByRole("slider"), { key: "ArrowRight" });
    expect(fn).toHaveBeenCalledWith(3);
  });

  it("ArrowLeft decrements", () => {
    const fn = vi.fn();
    render(<Rating defaultValue={3} onValueChange={fn} />);
    fireEvent.keyDown(screen.getByRole("slider"), { key: "ArrowLeft" });
    expect(fn).toHaveBeenCalledWith(2);
  });

  it("Home goes to 0, End to max", () => {
    const fn = vi.fn();
    render(<Rating defaultValue={3} onValueChange={fn} max={5} />);
    fireEvent.keyDown(screen.getByRole("slider"), { key: "End" });
    expect(fn).toHaveBeenLastCalledWith(5);
    fireEvent.keyDown(screen.getByRole("slider"), { key: "Home" });
    expect(fn).toHaveBeenLastCalledWith(0);
  });
});

describe("Rating - readOnly / disabled", () => {
  it("readOnly renders role=img and no slider role", () => {
    render(<Rating value={4} readOnly />);
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
    expect(screen.getByRole("img")).toBeInTheDocument();
  });

  it("readOnly ignores clicks", () => {
    const fn = vi.fn();
    const { container } = render(<Rating value={3} readOnly onValueChange={fn} />);
    fireEvent.click(container.querySelectorAll("button")[0]);
    expect(fn).not.toHaveBeenCalled();
  });

  it("disabled adds opacity class", () => {
    const { container } = render(<Rating value={3} disabled />);
    expect(container.firstChild).toHaveClass("opacity-50");
  });
});
