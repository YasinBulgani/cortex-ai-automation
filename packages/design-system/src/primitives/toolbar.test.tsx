import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Toolbar, ToolbarSeparator, ToolbarGroup } from "./toolbar";

describe("Toolbar", () => {
  it("renders with role=toolbar and aria label", () => {
    render(
      <Toolbar label="Düzenleyici araçları">
        <button>B</button>
      </Toolbar>,
    );
    expect(screen.getByRole("toolbar", { name: "Düzenleyici araçları" })).toBeInTheDocument();
  });

  it("aria-orientation defaults to horizontal", () => {
    render(<Toolbar><button>x</button></Toolbar>);
    expect(screen.getByRole("toolbar")).toHaveAttribute("aria-orientation", "horizontal");
  });

  it("supports vertical orientation", () => {
    render(<Toolbar orientation="vertical"><button>x</button></Toolbar>);
    expect(screen.getByRole("toolbar")).toHaveAttribute("aria-orientation", "vertical");
  });

  it("renders children", () => {
    render(
      <Toolbar>
        <button>One</button>
        <ToolbarSeparator />
        <button>Two</button>
      </Toolbar>,
    );
    expect(screen.getByRole("button", { name: "One" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Two" })).toBeInTheDocument();
    expect(screen.getByRole("separator")).toBeInTheDocument();
  });
});

describe("ToolbarGroup", () => {
  it("renders with role=group + aria-label", () => {
    render(
      <Toolbar>
        <ToolbarGroup label="Hizalama">
          <button>L</button>
          <button>C</button>
          <button>R</button>
        </ToolbarGroup>
      </Toolbar>,
    );
    expect(screen.getByRole("group", { name: "Hizalama" })).toBeInTheDocument();
  });
});

describe("ToolbarSeparator", () => {
  it("respects orientation", () => {
    const { rerender } = render(<ToolbarSeparator orientation="vertical" />);
    expect(screen.getByRole("separator")).toHaveAttribute("aria-orientation", "vertical");
    rerender(<ToolbarSeparator orientation="horizontal" />);
    expect(screen.getByRole("separator")).toHaveAttribute("aria-orientation", "horizontal");
  });
});
