/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

// ── Mock: @dnd-kit/core ───────────────────────────────────────────────────────
jest.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  closestCenter: jest.fn(),
  KeyboardSensor: jest.fn(),
  PointerSensor: jest.fn(),
  useSensor: jest.fn(),
  useSensors: jest.fn(() => []),
  DragOverlay: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="drag-overlay">{children}</div>
  ),
}));

// ── Mock: @dnd-kit/sortable ───────────────────────────────────────────────────
jest.mock("@dnd-kit/sortable", () => ({
  SortableContext: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  sortableKeyboardCoordinates: jest.fn(),
  verticalListSortingStrategy: "vertical",
  arrayMove: jest.fn(
    (arr: unknown[], oldIndex: number, newIndex: number) => {
      const result = [...arr];
      const [removed] = result.splice(oldIndex, 1);
      result.splice(newIndex, 0, removed);
      return result;
    }
  ),
}));

// ── Import under test ─────────────────────────────────────────────────────────
import { SortableList } from "../SortableList";

// ── Helpers ───────────────────────────────────────────────────────────────────
type TestItem = { id: string; name: string };

const items: TestItem[] = [
  { id: "1", name: "A" },
  { id: "2", name: "B" },
];

// ── Tests ─────────────────────────────────────────────────────────────────────
describe("SortableList", () => {
  it("renders without crash", () => {
    expect(() =>
      render(
        <SortableList
          items={items}
          onReorder={jest.fn()}
          renderItem={(item) => (
            <div key={item.id}>{item.name}</div>
          )}
        />
      )
    ).not.toThrow();
  });

  it("renders all items via renderItem", () => {
    render(
      <SortableList
        items={items}
        onReorder={jest.fn()}
        renderItem={(item) => (
          <div key={item.id} data-testid={`item-${item.id}`}>
            {item.name}
          </div>
        )}
      />
    );
    expect(screen.getByTestId("item-1")).toBeInTheDocument();
    expect(screen.getByTestId("item-2")).toBeInTheDocument();
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
  });

  it("calls renderItem with correct arguments (item, index, isDragging=false)", () => {
    const renderItem = jest.fn(
      (item: TestItem, _index: number, _isDragging: boolean) => (
        <div key={item.id}>{item.name}</div>
      )
    );

    render(
      <SortableList
        items={items}
        onReorder={jest.fn()}
        renderItem={renderItem}
      />
    );

    expect(renderItem).toHaveBeenCalledTimes(2);
    // First item: index 0, isDragging false (no active drag)
    expect(renderItem).toHaveBeenNthCalledWith(1, items[0], 0, false);
    // Second item: index 1, isDragging false
    expect(renderItem).toHaveBeenNthCalledWith(2, items[1], 1, false);
  });

  it("renders DragOverlay element", () => {
    render(
      <SortableList
        items={items}
        onReorder={jest.fn()}
        renderItem={(item) => <div key={item.id}>{item.name}</div>}
      />
    );
    expect(screen.getByTestId("drag-overlay")).toBeInTheDocument();
  });

  it("applies className to the container div", () => {
    const { container } = render(
      <SortableList
        items={items}
        onReorder={jest.fn()}
        renderItem={(item) => <div key={item.id}>{item.name}</div>}
        className="my-custom-class"
      />
    );
    // The inner div wrapping rendered items gets the className
    const el = container.querySelector(".my-custom-class");
    expect(el).not.toBeNull();
  });

  it("renders correctly with empty items array", () => {
    const { container } = render(
      <SortableList
        items={[] as TestItem[]}
        onReorder={jest.fn()}
        renderItem={(item) => <div key={item.id}>{item.name}</div>}
      />
    );
    // DragOverlay is still rendered; the item container is empty
    expect(screen.getByTestId("drag-overlay")).toBeInTheDocument();
    // No items are rendered inside
    expect(container.querySelectorAll("[data-testid^='item-']").length).toBe(0);
  });
});
