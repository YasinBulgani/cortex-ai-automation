import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Popover } from "./popover";

function renderPopover(props: Partial<React.ComponentProps<typeof Popover>> = {}) {
  return render(
    <Popover
      trigger={({ toggle, ref, ...rest }) => (
        <button ref={ref} onClick={toggle} {...rest}>Aç</button>
      )}
      {...props}
    >
      <div data-testid="content">İçerik</div>
    </Popover>,
  );
}

import * as React from "react";

describe("Popover", () => {
  it("closed by default", () => {
    renderPopover();
    expect(screen.queryByTestId("popover-content")).not.toBeInTheDocument();
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "false");
  });

  it("opens on trigger toggle", () => {
    renderPopover();
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByTestId("popover-content")).toBeInTheDocument();
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "true");
  });

  it("respects controlled open prop", () => {
    const { rerender } = renderPopover({ open: false, onOpenChange: () => {} });
    expect(screen.queryByTestId("popover-content")).not.toBeInTheDocument();
    rerender(
      <Popover
        open
        onOpenChange={() => {}}
        trigger={({ toggle, ref, ...rest }) => <button ref={ref} onClick={toggle} {...rest}>X</button>}
      >
        <div data-testid="content">y</div>
      </Popover>,
    );
    expect(screen.getByTestId("popover-content")).toBeInTheDocument();
  });

  it("calls onOpenChange when toggled", () => {
    const fn = vi.fn();
    renderPopover({ onOpenChange: fn });
    fireEvent.click(screen.getByRole("button"));
    expect(fn).toHaveBeenCalledWith(true);
  });

  it("ESC closes when closeOnEsc=true (default)", () => {
    renderPopover({ defaultOpen: true });
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByTestId("popover-content")).not.toBeInTheDocument();
  });

  it("ESC is no-op when closeOnEsc=false", () => {
    renderPopover({ defaultOpen: true, closeOnEsc: false });
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.getByTestId("popover-content")).toBeInTheDocument();
  });

  it("renders aria-haspopup=dialog", () => {
    renderPopover();
    expect(screen.getByRole("button")).toHaveAttribute("aria-haspopup", "dialog");
  });

  it("renders children content when open", () => {
    renderPopover({ defaultOpen: true });
    expect(screen.getByTestId("content")).toBeInTheDocument();
  });
});
