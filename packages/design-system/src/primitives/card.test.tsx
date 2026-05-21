import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card, CardHeader, CardBody, CardFooter } from "./card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card><div data-testid="x">Content</div></Card>);
    expect(screen.getByTestId("x")).toBeInTheDocument();
  });

  it("adds border by default", () => {
    const { container } = render(<Card>x</Card>);
    expect(container.firstChild).toHaveClass("border");
  });

  it("removes border when borderless", () => {
    const { container } = render(<Card borderless>x</Card>);
    expect(container.firstChild).not.toHaveClass("border");
  });

  it("adds cursor and hover when interactive", () => {
    const { container } = render(<Card interactive>x</Card>);
    expect(container.firstChild).toHaveClass("cursor-pointer");
  });

  it("uses compact padding when compact", () => {
    const { container } = render(<Card compact>x</Card>);
    expect(container.firstChild).toHaveClass("p-3");
  });
});

describe("CardHeader", () => {
  it("renders title and description", () => {
    render(<CardHeader title="T" description="D" />);
    expect(screen.getByText("T")).toBeInTheDocument();
    expect(screen.getByText("D")).toBeInTheDocument();
  });

  it("renders action slot", () => {
    render(<CardHeader title="T" action={<button>act</button>} />);
    expect(screen.getByText("act")).toBeInTheDocument();
  });
});

describe("CardBody + CardFooter", () => {
  it("renders body content", () => {
    render(<CardBody><span>body</span></CardBody>);
    expect(screen.getByText("body")).toBeInTheDocument();
  });

  it("renders footer content", () => {
    render(<CardFooter><span>foot</span></CardFooter>);
    expect(screen.getByText("foot")).toBeInTheDocument();
  });
});
