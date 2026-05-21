import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "./badge";

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>Yeni</Badge>);
    expect(screen.getByText("Yeni")).toBeInTheDocument();
  });

  it("applies status classes", () => {
    const { container, rerender } = render(<Badge status="success">OK</Badge>);
    expect(container.firstChild).toHaveClass("text-success");
    rerender(<Badge status="danger">X</Badge>);
    expect(container.firstChild).toHaveClass("text-danger");
  });

  it("renders dot indicator when dot=true", () => {
    const { container } = render(<Badge dot status="success">OK</Badge>);
    const dot = container.querySelector("span[aria-hidden]");
    expect(dot).toBeInTheDocument();
  });

  it("adds cursor when interactive", () => {
    const { container } = render(<Badge interactive>x</Badge>);
    expect(container.firstChild).toHaveClass("cursor-pointer");
  });
});
