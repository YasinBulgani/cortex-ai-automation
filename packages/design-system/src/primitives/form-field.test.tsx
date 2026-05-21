import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FormField } from "./form-field";
import { Input } from "./input";

describe("FormField", () => {
  it("renders label and child input", () => {
    render(
      <FormField label="E-posta">
        <Input type="email" />
      </FormField>,
    );
    expect(screen.getByLabelText("E-posta")).toBeInTheDocument();
  });

  it("marks required with asterisk", () => {
    render(
      <FormField label="Şifre" required>
        <Input type="password" />
      </FormField>,
    );
    expect(screen.getByLabelText("required")).toBeInTheDocument();
  });

  it("shows description when no error", () => {
    render(
      <FormField label="x" description="Min 8 karakter">
        <Input />
      </FormField>,
    );
    expect(screen.getByText("Min 8 karakter")).toBeInTheDocument();
  });

  it("shows error and sets aria-invalid", () => {
    render(
      <FormField label="x" error="Zorunlu alan">
        <Input />
      </FormField>,
    );
    const inp = screen.getByLabelText("x") as HTMLInputElement;
    expect(inp).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Zorunlu alan");
  });

  it("error suppresses description", () => {
    render(
      <FormField label="x" description="d" error="e">
        <Input />
      </FormField>,
    );
    expect(screen.queryByText("d")).not.toBeInTheDocument();
    expect(screen.getByText("e")).toBeInTheDocument();
  });

  it("wires aria-describedby to error id", () => {
    render(
      <FormField label="x" error="bad">
        <Input />
      </FormField>,
    );
    const inp = screen.getByLabelText("x");
    const desc = inp.getAttribute("aria-describedby");
    expect(desc).toBeTruthy();
    const errorEl = screen.getByRole("alert");
    expect(errorEl.id).toBeTruthy();
    expect(desc?.split(" ")).toContain(errorEl.id);
  });

  it("supports render-prop children", () => {
    render(
      <FormField label="x" error="e">
        {(api) => <input data-testid="raw" {...api} />}
      </FormField>,
    );
    const inp = screen.getByTestId("raw");
    expect(inp).toHaveAttribute("aria-invalid", "true");
    expect(inp.id).toBeTruthy();
  });

  it("labelHidden keeps label accessible but visually hidden", () => {
    render(
      <FormField label="Gizli" labelHidden>
        <Input />
      </FormField>,
    );
    expect(screen.getByLabelText("Gizli")).toBeInTheDocument();
  });
});
