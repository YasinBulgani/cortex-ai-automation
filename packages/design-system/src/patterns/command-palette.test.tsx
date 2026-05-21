import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { CommandPalette, type CommandItem } from "./command-palette";

function makeItems(overrides: Partial<CommandItem>[] = []): CommandItem[] {
  const base: CommandItem[] = [
    { id: "n1", label: "Yeni proje",     group: "Eylemler",   onSelect: vi.fn() },
    { id: "n2", label: "Yeni senaryo",   group: "Eylemler",   keywords: ["test", "case"], onSelect: vi.fn() },
    { id: "s1", label: "Ayarlar",        group: "Navigasyon", onSelect: vi.fn() },
    { id: "h1", label: "Yardım merkezi", group: "Navigasyon", onSelect: vi.fn() },
    { id: "d1", label: "Hesabı sil",     group: "Tehlikeli",  danger: true, onSelect: vi.fn() },
    { id: "x1", label: "Pasif",          disabled: true, onSelect: vi.fn() },
  ];
  return base.map((b, i) => ({ ...b, ...(overrides[i] ?? {}) }));
}

describe("CommandPalette", () => {
  it("renders nothing when closed", () => {
    render(<CommandPalette open={false} onOpenChange={() => {}} items={makeItems()} />);
    expect(screen.queryByTestId("command-palette")).not.toBeInTheDocument();
  });

  it("renders dialog and input when open", () => {
    render(<CommandPalette open onOpenChange={() => {}} items={makeItems()} />);
    expect(screen.getByRole("dialog", { name: "Komut paleti" })).toBeInTheDocument();
    expect(screen.getByTestId("command-input")).toBeInTheDocument();
  });

  it("groups items under group headings", () => {
    render(<CommandPalette open onOpenChange={() => {}} items={makeItems()} />);
    expect(screen.getByText("Eylemler")).toBeInTheDocument();
    expect(screen.getByText("Navigasyon")).toBeInTheDocument();
  });

  it("filters by query (label substring)", () => {
    render(<CommandPalette open onOpenChange={() => {}} items={makeItems()} />);
    fireEvent.change(screen.getByTestId("command-input"), { target: { value: "ayar" } });
    expect(screen.getByText("Ayarlar")).toBeInTheDocument();
    expect(screen.queryByText("Yeni proje")).not.toBeInTheDocument();
  });

  it("filters by keywords", () => {
    render(<CommandPalette open onOpenChange={() => {}} items={makeItems()} />);
    fireEvent.change(screen.getByTestId("command-input"), { target: { value: "test" } });
    expect(screen.getByText("Yeni senaryo")).toBeInTheDocument();
    expect(screen.queryByText("Ayarlar")).not.toBeInTheDocument();
  });

  it("shows empty message when no matches", () => {
    render(
      <CommandPalette
        open
        onOpenChange={() => {}}
        items={makeItems()}
        emptyMessage="Bulunamadı"
      />,
    );
    fireEvent.change(screen.getByTestId("command-input"), { target: { value: "qwertyzz" } });
    expect(screen.getByText("Bulunamadı")).toBeInTheDocument();
  });

  it("Enter selects active item and closes", () => {
    const fn = vi.fn();
    const items = makeItems();
    items[0].onSelect = fn;
    const onClose = vi.fn();
    render(<CommandPalette open onOpenChange={onClose} items={items} />);
    fireEvent.keyDown(screen.getByTestId("command-palette"), { key: "Enter" });
    expect(fn).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledWith(false);
  });

  it("ArrowDown moves active selection", () => {
    const items = makeItems();
    const second = vi.fn();
    items[1].onSelect = second;
    render(<CommandPalette open onOpenChange={() => {}} items={items} />);
    fireEvent.keyDown(screen.getByTestId("command-palette"), { key: "ArrowDown" });
    fireEvent.keyDown(screen.getByTestId("command-palette"), { key: "Enter" });
    expect(second).toHaveBeenCalled();
  });

  it("ESC closes", () => {
    const onClose = vi.fn();
    render(<CommandPalette open onOpenChange={onClose} items={makeItems()} />);
    fireEvent.keyDown(screen.getByTestId("command-palette"), { key: "Escape" });
    expect(onClose).toHaveBeenCalledWith(false);
  });

  it("Overlay click closes", () => {
    const onClose = vi.fn();
    render(<CommandPalette open onOpenChange={onClose} items={makeItems()} />);
    fireEvent.click(screen.getByTestId("command-overlay"));
    expect(onClose).toHaveBeenCalledWith(false);
  });

  it("Disabled items are skipped on Enter", () => {
    const disabledFn = vi.fn();
    const items = makeItems();
    items[5].onSelect = disabledFn;
    // 5 selectable (0..4), End jumps to last selectable
    render(<CommandPalette open onOpenChange={() => {}} items={items} />);
    fireEvent.keyDown(screen.getByTestId("command-palette"), { key: "End" });
    fireEvent.keyDown(screen.getByTestId("command-palette"), { key: "Enter" });
    expect(disabledFn).not.toHaveBeenCalled();
  });

  it("resets query and active on reopen", () => {
    const { rerender } = render(<CommandPalette open onOpenChange={() => {}} items={makeItems()} />);
    fireEvent.change(screen.getByTestId("command-input"), { target: { value: "ayar" } });
    expect((screen.getByTestId("command-input") as HTMLInputElement).value).toBe("ayar");
    rerender(<CommandPalette open={false} onOpenChange={() => {}} items={makeItems()} />);
    rerender(<CommandPalette open onOpenChange={() => {}} items={makeItems()} />);
    expect((screen.getByTestId("command-input") as HTMLInputElement).value).toBe("");
  });

  it("body scroll locks while open", () => {
    const original = document.body.style.overflow;
    const { rerender } = render(<CommandPalette open={false} onOpenChange={() => {}} items={makeItems()} />);
    expect(document.body.style.overflow).toBe(original);
    rerender(<CommandPalette open onOpenChange={() => {}} items={makeItems()} />);
    expect(document.body.style.overflow).toBe("hidden");
  });
});
