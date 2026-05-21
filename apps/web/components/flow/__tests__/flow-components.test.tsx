/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// ─── SortableItem ─────────────────────────────────────────────────────────────
// Mock @dnd-kit/sortable so we don't need a DndContext
jest.mock("@dnd-kit/sortable", () => ({
  useSortable: jest.fn(() => ({
    attributes: { role: "button" },
    listeners: {},
    setNodeRef: jest.fn(),
    transform: null,
    transition: undefined,
    isDragging: false,
  })),
}));
jest.mock("@dnd-kit/utilities", () => ({
  CSS: { Transform: { toString: jest.fn(() => "") } },
}));

import { SortableItem } from "../../dnd/SortableItem";

describe("SortableItem", () => {
  it("renders children", () => {
    render(
      <SortableItem id="item-1">
        <span data-testid="child">İçerik</span>
      </SortableItem>
    );
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("renders as 'div' by default", () => {
    const { container } = render(
      <SortableItem id="item-1">content</SortableItem>
    );
    expect(container.querySelector("div")).toBeInTheDocument();
  });

  it("renders as 'tr' when as='tr'", () => {
    const { container } = render(
      <table><tbody>
        <SortableItem id="item-1" as="tr"><td>row</td></SortableItem>
      </tbody></table>
    );
    expect(container.querySelector("tr")).toBeInTheDocument();
  });

  it("renders as 'li' when as='li'", () => {
    const { container } = render(
      <ul><SortableItem id="item-1" as="li">list item</SortableItem></ul>
    );
    expect(container.querySelector("li")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <SortableItem id="item-1" className="my-custom-class">content</SortableItem>
    );
    expect(container.querySelector(".my-custom-class")).toBeInTheDocument();
  });

  it("applies reduced opacity when isDragging", () => {
    const { useSortable } = require("@dnd-kit/sortable");
    (useSortable as jest.Mock).mockReturnValueOnce({
      attributes: {},
      listeners: {},
      setNodeRef: jest.fn(),
      transform: null,
      transition: undefined,
      isDragging: true,
    });
    const { container } = render(
      <SortableItem id="item-1">dragging</SortableItem>
    );
    // When isDragging=true, opacity: 0.4 is set inline
    const el = container.firstChild as HTMLElement;
    expect(el.style.opacity).toBe("0.4");
  });
});

// ─── NodePalette ──────────────────────────────────────────────────────────────
import { NodePalette } from "../NodePalette";

describe("NodePalette", () => {
  it("renders 'Düğümler' heading", () => {
    render(<NodePalette />);
    expect(screen.getByText("Düğümler")).toBeInTheDocument();
  });

  it("renders 'Sürükleyip bırakın' hint", () => {
    render(<NodePalette />);
    expect(screen.getByText("Sürükleyip bırakın")).toBeInTheDocument();
  });

  it("renders node type labels (Tetikleyici, Koşul, etc.)", () => {
    render(<NodePalette />);
    // At least one node type should be visible
    expect(screen.getByText("Tetikleyici")).toBeInTheDocument();
  });

  it("renders multiple draggable items", () => {
    const { container } = render(<NodePalette />);
    const draggables = container.querySelectorAll("[draggable]");
    expect(draggables.length).toBeGreaterThan(3);
  });

  it("sets dataTransfer on dragStart", () => {
    render(<NodePalette />);
    const draggables = document.querySelectorAll("[draggable]");
    const setData = jest.fn();
    // Simulate dragStart on first draggable
    fireEvent.dragStart(draggables[0], {
      dataTransfer: { setData, effectAllowed: "" },
    });
    expect(setData).toHaveBeenCalledWith("application/reactflow-type", expect.any(String));
  });
});

// ─── NodePropertiesPanel ──────────────────────────────────────────────────────
import { NodePropertiesPanel } from "../NodePropertiesPanel";
import type { Node } from "reactflow";
import type { FlowNodeData } from "../FlowNode";

describe("NodePropertiesPanel", () => {
  const mockNode: Node<FlowNodeData> = {
    id: "node-1",
    type: "default",
    position: { x: 0, y: 0 },
    data: {
      label: "Test Node",
      nodeType: "trigger",
      config: {},
    },
  };

  it("renders without crashing", () => {
    const { container } = render(
      <NodePropertiesPanel
        node={mockNode}
        onChange={jest.fn()}
        onDelete={jest.fn()}
        onClose={jest.fn()}
      />
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders the node label (Tetikleyici)", () => {
    render(
      <NodePropertiesPanel
        node={mockNode}
        onChange={jest.fn()}
        onDelete={jest.fn()}
        onClose={jest.fn()}
      />
    );
    expect(screen.getByText("Tetikleyici")).toBeInTheDocument();
  });

  it("calls onClose when close button clicked (× button)", () => {
    const onClose = jest.fn();
    render(
      <NodePropertiesPanel
        node={mockNode}
        onChange={jest.fn()}
        onDelete={jest.fn()}
        onClose={onClose}
      />
    );
    // The close button renders "×" as its text
    const closeBtn = screen.getByText("×");
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onDelete when 'Düğümü Sil' button clicked", () => {
    const onDelete = jest.fn();
    render(
      <NodePropertiesPanel
        node={mockNode}
        onChange={jest.fn()}
        onDelete={onDelete}
        onClose={jest.fn()}
      />
    );
    const deleteBtn = screen.getByText("Düğümü Sil");
    fireEvent.click(deleteBtn);
    expect(onDelete).toHaveBeenCalledWith("node-1");
  });

  it("returns null for unknown nodeType", () => {
    const badNode = { ...mockNode, data: { ...mockNode.data, nodeType: "unknown_type" as FlowNodeData["nodeType"] } };
    const { container } = render(
      <NodePropertiesPanel
        node={badNode}
        onChange={jest.fn()}
        onDelete={jest.fn()}
        onClose={jest.fn()}
      />
    );
    expect(container.firstChild).toBeNull();
  });
});
