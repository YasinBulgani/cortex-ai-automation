import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Input, Textarea } from "./input";

describe("Input", () => {
  it("renders with placeholder", () => {
    render(<Input placeholder="Email" />);
    expect(screen.getByPlaceholderText("Email")).toBeInTheDocument();
  });

  it("accepts user typing", async () => {
    const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      (e.target as HTMLInputElement).dataset.last = e.target.value;
    };
    render(<Input onChange={onChange} aria-label="x" />);
    const el = screen.getByLabelText("x") as HTMLInputElement;
    await userEvent.type(el, "hello");
    expect(el.value).toBe("hello");
  });

  it("sets aria-invalid when invalid", () => {
    render(<Input invalid aria-label="x" />);
    expect(screen.getByLabelText("x")).toHaveAttribute("aria-invalid", "true");
  });

  it("renders leading and trailing icon wrappers", () => {
    render(
      <Input
        aria-label="x"
        leadingIcon={<span data-testid="L">L</span>}
        trailingIcon={<span data-testid="T">T</span>}
      />,
    );
    expect(screen.getByTestId("L")).toBeInTheDocument();
    expect(screen.getByTestId("T")).toBeInTheDocument();
  });

  it("forwards ref", () => {
    const ref = { current: null as HTMLInputElement | null };
    render(<Input ref={ref} aria-label="x" />);
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
  });
});

describe("Textarea", () => {
  it("renders with default rows", () => {
    render(<Textarea aria-label="t" />);
    expect(screen.getByLabelText("t")).toHaveAttribute("rows", "4");
  });

  it("accepts invalid prop", () => {
    render(<Textarea invalid aria-label="t" />);
    expect(screen.getByLabelText("t")).toHaveAttribute("aria-invalid", "true");
  });
});
