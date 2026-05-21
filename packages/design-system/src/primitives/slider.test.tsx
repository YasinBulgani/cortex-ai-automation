import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Slider } from "./slider";

describe("Slider", () => {
  it("renders with aria-label", () => {
    render(<Slider aria-label="volume" defaultValue={50} />);
    expect(screen.getByRole("slider", { name: "volume" })).toBeInTheDocument();
  });

  it("uses label prop as aria-label when no aria-label", () => {
    render(<Slider label="speed" defaultValue={10} />);
    expect(screen.getByRole("slider", { name: "speed" })).toBeInTheDocument();
  });

  it("respects min/max/step on native input", () => {
    render(<Slider aria-label="x" min={10} max={20} step={2} defaultValue={14} />);
    const input = screen.getByRole("slider") as HTMLInputElement;
    expect(input.min).toBe("10");
    expect(input.max).toBe("20");
    expect(input.step).toBe("2");
    expect(input.value).toBe("14");
  });

  it("calls onValueChange on change (uncontrolled)", () => {
    const fn = vi.fn();
    render(<Slider aria-label="x" defaultValue={0} onValueChange={fn} />);
    fireEvent.change(screen.getByRole("slider"), { target: { value: "75" } });
    expect(fn).toHaveBeenCalledWith(75);
  });

  it("shows formatted value when showValue is set", () => {
    render(
      <Slider
        aria-label="x"
        defaultValue={64}
        showValue
        formatValue={(v) => `${v}%`}
      />,
    );
    expect(screen.getByText("64%")).toBeInTheDocument();
  });

  it("aria-invalid when invalid prop set", () => {
    render(<Slider aria-label="x" invalid defaultValue={0} />);
    expect(screen.getByRole("slider")).toHaveAttribute("aria-invalid", "true");
  });

  it("controlled value reflects re-render", () => {
    const { rerender } = render(<Slider aria-label="x" value={20} onValueChange={() => {}} />);
    expect((screen.getByRole("slider") as HTMLInputElement).value).toBe("20");
    rerender(<Slider aria-label="x" value={80} onValueChange={() => {}} />);
    expect((screen.getByRole("slider") as HTMLInputElement).value).toBe("80");
  });

  it("disabled prevents change", () => {
    render(<Slider aria-label="x" disabled defaultValue={0} />);
    expect(screen.getByRole("slider")).toBeDisabled();
  });
});
