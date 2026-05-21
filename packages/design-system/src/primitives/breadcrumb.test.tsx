import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Breadcrumb } from "./breadcrumb";

describe("Breadcrumb", () => {
  it("renders nav with aria label", () => {
    render(<Breadcrumb items={[{ label: "Ana" }]} label="iz" />);
    expect(screen.getByRole("navigation", { name: "iz" })).toBeInTheDocument();
  });

  it("renders all items", () => {
    render(<Breadcrumb items={[{ label: "Ana", href: "/" }, { label: "Projeler", href: "/p" }, { label: "Detay" }]} />);
    expect(screen.getByText("Ana")).toBeInTheDocument();
    expect(screen.getByText("Projeler")).toBeInTheDocument();
    expect(screen.getByText("Detay")).toBeInTheDocument();
  });

  it("marks last item with aria-current=page", () => {
    render(<Breadcrumb items={[{ label: "Ana", href: "/" }, { label: "X", href: "/x" }]} />);
    const x = screen.getByText("X").closest("a");
    expect(x).toHaveAttribute("aria-current", "page");
  });

  it("renders custom separator", () => {
    const { container } = render(<Breadcrumb items={[{ label: "A" }, { label: "B" }]} separator=">" />);
    expect(container).toHaveTextContent("A>B");
  });

  it("collapses items when maxItems exceeded", () => {
    render(
      <Breadcrumb
        items={[
          { label: "1" }, { label: "2" }, { label: "3" }, { label: "4" }, { label: "5" },
        ]}
        maxItems={3}
      />,
    );
    expect(screen.getByText("…")).toBeInTheDocument();
    expect(screen.queryByText("2")).not.toBeInTheDocument();
    expect(screen.queryByText("3")).not.toBeInTheDocument();
  });

  it("clickable item without href fires onClick", () => {
    const fn = vi.fn();
    render(<Breadcrumb items={[{ label: "Ana", onClick: fn }, { label: "Now" }]} />);
    fireEvent.click(screen.getByText("Ana"));
    expect(fn).toHaveBeenCalled();
  });
});
