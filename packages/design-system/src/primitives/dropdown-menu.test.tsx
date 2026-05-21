import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DropdownMenu, type DropdownEntry } from "./dropdown-menu";

function makeItems(handlers: Record<string, () => void> = {}): DropdownEntry[] {
  return [
    { key: "header", heading: "İşlemler" },
    { key: "edit", label: "Düzenle", onSelect: handlers.edit, shortcut: "E" },
    { key: "copy", label: "Kopyala", onSelect: handlers.copy },
    { key: "sep1", separator: true },
    { key: "delete", label: "Sil", danger: true, onSelect: handlers.delete },
    { key: "disabled", label: "Pasif", disabled: true, onSelect: handlers.disabled },
  ];
}

function renderMenu(items: DropdownEntry[]) {
  return render(
    <DropdownMenu
      items={items}
      trigger={({ open, toggle, ...rest }) => (
        <button type="button" onClick={toggle} {...rest}>
          {open ? "Açık" : "Kapalı"}
        </button>
      )}
    />,
  );
}

describe("DropdownMenu", () => {
  it("renders trigger and is closed initially", () => {
    renderMenu(makeItems());
    expect(screen.getByRole("button", { name: "Kapalı" })).toBeInTheDocument();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("opens on trigger click", () => {
    renderMenu(makeItems());
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("menu")).toBeInTheDocument();
  });

  it("sets aria-expanded on trigger", () => {
    renderMenu(makeItems());
    const btn = screen.getByRole("button");
    expect(btn).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(btn);
    expect(btn).toHaveAttribute("aria-expanded", "true");
  });

  it("renders heading + separator + items + danger", () => {
    renderMenu(makeItems());
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("İşlemler")).toBeInTheDocument();
    expect(screen.getAllByRole("separator")).toHaveLength(1);
    expect(screen.getByRole("menuitem", { name: /Düzenle/ })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /Sil/ })).toHaveClass("text-danger");
  });

  it("clicking item calls onSelect and closes menu", () => {
    const handlers = { edit: vi.fn() };
    renderMenu(makeItems(handlers));
    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByRole("menuitem", { name: /Düzenle/ }));
    expect(handlers.edit).toHaveBeenCalledOnce();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("disabled item is not invoked on click", () => {
    const handlers = { disabled: vi.fn() };
    renderMenu(makeItems(handlers));
    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByRole("menuitem", { name: /Pasif/ }));
    expect(handlers.disabled).not.toHaveBeenCalled();
  });

  it("ESC closes the menu", () => {
    renderMenu(makeItems());
    fireEvent.click(screen.getByRole("button"));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("ArrowDown / Enter selects first item", () => {
    const handlers = { edit: vi.fn() };
    renderMenu(makeItems(handlers));
    fireEvent.click(screen.getByRole("button"));
    fireEvent.keyDown(document, { key: "ArrowDown" });
    fireEvent.keyDown(document, { key: "Enter" });
    expect(handlers.edit).toHaveBeenCalledOnce();
  });

  it("End key jumps to last selectable item", () => {
    const handlers = { delete: vi.fn() };
    renderMenu(makeItems(handlers));
    fireEvent.click(screen.getByRole("button"));
    fireEvent.keyDown(document, { key: "End" });
    fireEvent.keyDown(document, { key: "Enter" });
    expect(handlers.delete).toHaveBeenCalledOnce();
  });
});
