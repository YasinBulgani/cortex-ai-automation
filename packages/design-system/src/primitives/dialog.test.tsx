import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { Dialog } from "./dialog";

describe("Dialog", () => {
  it("does not render when open=false", () => {
    render(<Dialog open={false} onOpenChange={() => {}} title="t">body</Dialog>);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders when open=true with title and aria props", () => {
    render(<Dialog open onOpenChange={() => {}} title="Onayla" description="açıklama">body</Dialog>);
    const dlg = screen.getByRole("dialog");
    expect(dlg).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("Onayla")).toBeInTheDocument();
    expect(screen.getByText("açıklama")).toBeInTheDocument();
  });

  it("renders close button by default and calls onOpenChange(false)", () => {
    const onOpenChange = vi.fn();
    render(<Dialog open onOpenChange={onOpenChange} title="t">body</Dialog>);
    fireEvent.click(screen.getByTestId("dialog-close"));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("hides close button when showCloseButton=false", () => {
    render(<Dialog open onOpenChange={() => {}} title="t" showCloseButton={false}>x</Dialog>);
    expect(screen.queryByTestId("dialog-close")).not.toBeInTheDocument();
  });

  it("overlay click closes when closeOnOverlayClick=true (default)", () => {
    const onOpenChange = vi.fn();
    render(<Dialog open onOpenChange={onOpenChange} title="t">x</Dialog>);
    fireEvent.click(screen.getByTestId("dialog-overlay"));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("overlay click is no-op when closeOnOverlayClick=false", () => {
    const onOpenChange = vi.fn();
    render(<Dialog open onOpenChange={onOpenChange} title="t" closeOnOverlayClick={false}>x</Dialog>);
    fireEvent.click(screen.getByTestId("dialog-overlay"));
    expect(onOpenChange).not.toHaveBeenCalled();
  });

  it("ESC key closes when closeOnEsc=true (default)", () => {
    const onOpenChange = vi.fn();
    render(<Dialog open onOpenChange={onOpenChange} title="t">x</Dialog>);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("ESC key is no-op when closeOnEsc=false", () => {
    const onOpenChange = vi.fn();
    render(<Dialog open onOpenChange={onOpenChange} title="t" closeOnEsc={false}>x</Dialog>);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onOpenChange).not.toHaveBeenCalled();
  });

  it("locks body scroll while open", () => {
    const original = document.body.style.overflow;
    const { rerender } = render(<Dialog open={false} onOpenChange={() => {}}>x</Dialog>);
    expect(document.body.style.overflow).toBe(original);
    rerender(<Dialog open onOpenChange={() => {}}>x</Dialog>);
    expect(document.body.style.overflow).toBe("hidden");
    rerender(<Dialog open={false} onOpenChange={() => {}}>x</Dialog>);
    expect(document.body.style.overflow).toBe(original);
  });

  it("renders footer slot", () => {
    render(
      <Dialog open onOpenChange={() => {}} title="t" footer={<button>Tamam</button>}>
        x
      </Dialog>,
    );
    expect(screen.getByRole("button", { name: "Tamam" })).toBeInTheDocument();
  });

  it("focuses initial focus ref when provided", async () => {
    function H() {
      const ref = React.useRef<HTMLButtonElement>(null);
      return (
        <Dialog open onOpenChange={() => {}} title="t" initialFocusRef={ref}>
          <button>noop</button>
          <button ref={ref}>target</button>
        </Dialog>
      );
    }
    render(<H />);
    await act(async () => { await new Promise(r => setTimeout(r, 1)); });
    expect(document.activeElement).toHaveTextContent("target");
  });
});

import * as React from "react";
