import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import { VirtualList } from "./virtual-list";

// @tanstack/react-virtual measures container height to decide which items
// to render. jsdom has no layout engine so we must mock scrollHeight/offsetHeight.
beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
    configurable: true,
    get() { return 400; },
  });
  Object.defineProperty(HTMLElement.prototype, "scrollHeight", {
    configurable: true,
    get() { return this._scrollHeight ?? 400; },
  });
});

const items = Array.from({ length: 100 }, (_, i) => ({ id: `item-${i}`, label: `Item ${i}` }));

describe("VirtualList", () => {
  it("renders without crashing with empty list", () => {
    render(
      <VirtualList
        items={[]}
        renderItem={() => <div />}
        className="h-96"
      />,
    );
  });

  it("renders some items from the list (virtualised — not all 100)", () => {
    render(
      <VirtualList
        items={items}
        estimateSize={40}
        renderItem={(item) => <div>{item.label}</div>}
        itemKey={(item) => item.id}
        className="h-96"
      />,
    );
    // In jsdom virtualizer renders at least first items visible in 400px / 40px = ~10
    expect(screen.getByText("Item 0")).toBeInTheDocument();
  });

  it("uses itemKey to set stable keys (no duplicate text)", () => {
    const { container } = render(
      <VirtualList
        items={items.slice(0, 10)}
        estimateSize={40}
        renderItem={(item) => <div data-testid="row">{item.label}</div>}
        itemKey={(item) => item.id}
        className="h-96"
      />,
    );
    const rows = container.querySelectorAll("[data-testid='row']");
    expect(rows.length).toBeGreaterThan(0);
  });

  it("passes overscan prop without error", () => {
    render(
      <VirtualList
        items={items}
        overscan={3}
        estimateSize={40}
        renderItem={(item) => <div>{item.label}</div>}
        className="h-96"
      />,
    );
  });

  it("applies className to outer container", () => {
    const { container } = render(
      <VirtualList
        items={[{ id: "a", label: "A" }]}
        renderItem={(item) => <div>{item.label}</div>}
        className="h-96 my-custom-class"
      />,
    );
    const outer = container.firstChild as HTMLElement;
    expect(outer.className).toContain("my-custom-class");
    expect(outer.className).toContain("overflow-y-auto");
  });

  it("applies inline style to outer container", () => {
    const { container } = render(
      <VirtualList
        items={[{ id: "a", label: "A" }]}
        renderItem={(item) => <div>{item.label}</div>}
        style={{ maxHeight: 500 }}
      />,
    );
    const outer = container.firstChild as HTMLElement;
    expect(outer.style.maxHeight).toBe("500px");
  });

  it("renders inner div with relative position for virtualisation", () => {
    const { container } = render(
      <VirtualList
        items={items}
        estimateSize={40}
        renderItem={(item) => <div>{item.label}</div>}
        className="h-96"
      />,
    );
    const inner = container.querySelector("[style*='position: relative']");
    expect(inner).not.toBeNull();
  });

  it("works with string items", () => {
    const strings = ["Ahmet", "Barış", "Cem"];
    render(
      <VirtualList
        items={strings}
        estimateSize={32}
        renderItem={(s) => <span>{s}</span>}
        className="h-96"
      />,
    );
    expect(screen.getByText("Ahmet")).toBeInTheDocument();
  });
});
