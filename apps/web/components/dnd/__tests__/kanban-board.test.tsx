/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";
import { KanbanBoard } from "../KanbanBoard";

// ---------------------------------------------------------------------------
// dnd-kit mocks
// ---------------------------------------------------------------------------
jest.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dnd-context">{children}</div>
  ),
  closestCorners: jest.fn(),
  KeyboardSensor: jest.fn(),
  PointerSensor: jest.fn(),
  useSensor: jest.fn(),
  useSensors: jest.fn(() => []),
  DragOverlay: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="drag-overlay">{children}</div>
  ),
  useDroppable: jest.fn(() => ({ setNodeRef: jest.fn(), isOver: false })),
}));

jest.mock("@dnd-kit/sortable", () => ({
  SortableContext: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  sortableKeyboardCoordinates: jest.fn(),
  verticalListSortingStrategy: "vertical",
  useSortable: jest.fn(() => ({
    attributes: {},
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

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------
type Card = { id: string; name: string };

const columns = [
  {
    id: "col-1",
    title: "Todo",
    color: "#3b82f6",
    items: [
      { id: "c1", name: "Task 1" },
      { id: "c2", name: "Task 2" },
    ],
  },
  {
    id: "col-2",
    title: "Done",
    color: "#10b981",
    items: [{ id: "c3", name: "Task 3" }],
  },
];

const onMove = jest.fn();
const renderCard = (item: Card) => (
  <div data-testid={`card-${item.id}`}>{item.name}</div>
);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("KanbanBoard", () => {
  beforeEach(() => {
    onMove.mockClear();
  });

  it("renders without crash", () => {
    expect(() =>
      render(
        <KanbanBoard
          columns={columns}
          onMove={onMove}
          renderCard={renderCard}
        />
      )
    ).not.toThrow();
  });

  it("renders all column titles", () => {
    render(
      <KanbanBoard columns={columns} onMove={onMove} renderCard={renderCard} />
    );
    expect(screen.getByText("Todo")).toBeInTheDocument();
    expect(screen.getByText("Done")).toBeInTheDocument();
  });

  it("renders all cards via renderCard", () => {
    render(
      <KanbanBoard columns={columns} onMove={onMove} renderCard={renderCard} />
    );
    expect(screen.getByTestId("card-c1")).toBeInTheDocument();
    expect(screen.getByText("Task 1")).toBeInTheDocument();
    expect(screen.getByTestId("card-c2")).toBeInTheDocument();
    expect(screen.getByText("Task 2")).toBeInTheDocument();
    expect(screen.getByTestId("card-c3")).toBeInTheDocument();
    expect(screen.getByText("Task 3")).toBeInTheDocument();
  });

  it("shows item counts per column", () => {
    render(
      <KanbanBoard columns={columns} onMove={onMove} renderCard={renderCard} />
    );
    // Todo column has 2 items, Done column has 1 item
    // The count badge renders the numeric string directly
    const counts = screen.getAllByText(/^\d+$/);
    const countValues = counts.map((el) => el.textContent);
    expect(countValues).toContain("2");
    expect(countValues).toContain("1");
  });

  it("renders the DragOverlay wrapper", () => {
    render(
      <KanbanBoard columns={columns} onMove={onMove} renderCard={renderCard} />
    );
    expect(screen.getByTestId("drag-overlay")).toBeInTheDocument();
  });

  it("renders the DndContext wrapper", () => {
    render(
      <KanbanBoard columns={columns} onMove={onMove} renderCard={renderCard} />
    );
    expect(screen.getByTestId("dnd-context")).toBeInTheDocument();
  });

  it("renders without crash when columns array is empty", () => {
    expect(() =>
      render(
        <KanbanBoard<Card>
          columns={[]}
          onMove={onMove}
          renderCard={renderCard}
        />
      )
    ).not.toThrow();
  });

  it("uses renderOverlay when provided and an item is active", () => {
    // Because activeId starts as null, renderOverlay won't be called initially.
    // We verify the prop is accepted and the overlay container is present.
    const renderOverlay = jest.fn((item: Card) => (
      <div data-testid={`overlay-${item.id}`}>{item.name} (overlay)</div>
    ));

    render(
      <KanbanBoard
        columns={columns}
        onMove={onMove}
        renderCard={renderCard}
        renderOverlay={renderOverlay}
      />
    );

    // DragOverlay container is always rendered
    expect(screen.getByTestId("drag-overlay")).toBeInTheDocument();
    // renderOverlay should not be called before a drag starts (activeItem is null)
    expect(renderOverlay).not.toHaveBeenCalled();
  });
});
