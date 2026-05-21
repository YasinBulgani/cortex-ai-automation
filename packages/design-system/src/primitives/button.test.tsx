import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./button";

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Kaydet</Button>);
    expect(screen.getByRole("button", { name: "Kaydet" })).toBeInTheDocument();
  });

  it("defaults to type=button (prevents accidental form submit)", () => {
    render(<Button>X</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "button");
  });

  it("respects explicit type=submit", () => {
    render(<Button type="submit">Send</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "submit");
  });

  it("calls onClick", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click</Button>);
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("disables when loading and shows aria-busy", () => {
    render(<Button loading>Save</Button>);
    const btn = screen.getByRole("button");
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-busy", "true");
  });

  it("does not fire onClick while loading", async () => {
    const onClick = vi.fn();
    render(<Button loading onClick={onClick}>X</Button>);
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("renders leading and trailing icons", () => {
    render(
      <Button
        leadingIcon={<span data-testid="lead">L</span>}
        trailingIcon={<span data-testid="trail">T</span>}
      >
        Mid
      </Button>,
    );
    expect(screen.getByTestId("lead")).toBeInTheDocument();
    expect(screen.getByTestId("trail")).toBeInTheDocument();
  });

  it("applies fullWidth class", () => {
    const { container } = render(<Button fullWidth>X</Button>);
    expect(container.firstChild).toHaveClass("w-full");
  });

  it("forwards ref", () => {
    const ref = { current: null as HTMLButtonElement | null };
    render(<Button ref={ref}>X</Button>);
    expect(ref.current).toBeInstanceOf(HTMLButtonElement);
  });
});
