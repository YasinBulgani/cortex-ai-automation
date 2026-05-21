import { describe, it, expect, vi } from "vitest";
import { render, screen, act, fireEvent } from "@testing-library/react";
import { Tooltip } from "./tooltip";

describe("Tooltip", () => {
  it("renders children without tooltip initially", () => {
    render(<Tooltip content="hint"><button>hover</button></Tooltip>);
    expect(screen.getByRole("button")).toBeInTheDocument();
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("shows tooltip on mouseEnter after delay", () => {
    vi.useFakeTimers();
    render(
      <Tooltip content="Help text" delay={100}>
        <button>trigger</button>
      </Tooltip>,
    );
    const wrapper = screen.getByRole("button").parentElement!;
    act(() => { fireEvent.mouseEnter(wrapper); });
    act(() => { vi.advanceTimersByTime(150); });
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    expect(screen.getByRole("tooltip").textContent).toContain("Help text");
    vi.useRealTimers();
  });

  it("hides tooltip on mouseLeave", () => {
    vi.useFakeTimers();
    render(<Tooltip content="tip" delay={0}><button>x</button></Tooltip>);
    const wrapper = screen.getByRole("button").parentElement!;
    act(() => { fireEvent.mouseEnter(wrapper); vi.advanceTimersByTime(10); });
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    act(() => { fireEvent.mouseLeave(wrapper); });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it("does not show tooltip when disabled", () => {
    vi.useFakeTimers();
    render(<Tooltip content="tip" delay={0} disabled><button>x</button></Tooltip>);
    const wrapper = screen.getByRole("button").parentElement!;
    act(() => { fireEvent.mouseEnter(wrapper); vi.advanceTimersByTime(10); });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it("renders shortcut in tooltip when provided", () => {
    vi.useFakeTimers();
    render(<Tooltip content="Open" shortcut="⌘K" delay={0}><button>x</button></Tooltip>);
    const wrapper = screen.getByRole("button").parentElement!;
    act(() => { fireEvent.mouseEnter(wrapper); vi.advanceTimersByTime(10); });
    expect(screen.getByRole("tooltip").textContent).toContain("⌘K");
    vi.useRealTimers();
  });

  it("respects delay — tooltip absent before delay elapses", () => {
    vi.useFakeTimers();
    render(<Tooltip content="Delayed" delay={500}><button>x</button></Tooltip>);
    const wrapper = screen.getByRole("button").parentElement!;
    act(() => { fireEvent.mouseEnter(wrapper); vi.advanceTimersByTime(200); });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    vi.useRealTimers();
  });
});
