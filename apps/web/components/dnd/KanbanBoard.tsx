"use client";

import { useState, useCallback } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragOverlay,
  DragStartEvent,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useDroppable } from "@dnd-kit/core";
import { SortableItem } from "./SortableItem";

export interface KanbanColumn<T> {
  id: string;
  title: string;
  color: string;
  items: T[];
}

interface KanbanBoardProps<T extends { id: string }> {
  columns: KanbanColumn<T>[];
  onMove: (itemId: string, fromColumn: string, toColumn: string) => void;
  renderCard: (item: T) => React.ReactNode;
  renderOverlay?: (item: T) => React.ReactNode;
}

function DroppableColumn({
  id,
  title,
  color,
  count,
  children,
}: {
  id: string;
  title: string;
  color: string;
  count: number;
  children: React.ReactNode;
}) {
  const { isOver, setNodeRef } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      className={`flex min-h-[300px] flex-col rounded-xl border-2 transition-all duration-200 ${
        isOver ? "border-blue-500/60 bg-blue-500/5 shadow-md" : "border-slate-800 bg-black/[0.01] dark:bg-white/[0.01]"
      }`}
      data-testid={`kanban-column-${id}`}
    >
      <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-3">
        <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
        <h3 className="text-sm font-semibold">{title}</h3>
        <span className="ml-auto rounded-full bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-400 bg-slate-700">
          {count}
        </span>
      </div>
      <div className="flex-1 space-y-2 p-3">{children}</div>
    </div>
  );
}

export function KanbanBoard<T extends { id: string }>({
  columns,
  onMove,
  renderCard,
  renderOverlay,
}: KanbanBoardProps<T>) {
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const findColumn = useCallback(
    (itemId: string) => columns.find((col) => col.items.some((item) => item.id === itemId))?.id,
    [columns]
  );

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  }, []);

  const handleDragOver = useCallback(
    (event: DragOverEvent) => {
      const { active, over } = event;
      if (!over) return;

      const activeColumn = findColumn(active.id as string);
      const overColumn = columns.find((col) => col.id === over.id)?.id ?? findColumn(over.id as string);

      if (activeColumn && overColumn && activeColumn !== overColumn) {
        onMove(active.id as string, activeColumn, overColumn);
      }
    },
    [columns, findColumn, onMove]
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveId(null);
      if (!over) return;

      const activeColumn = findColumn(active.id as string);
      const overColumn = columns.find((col) => col.id === over.id)?.id ?? findColumn(over.id as string);

      if (activeColumn && overColumn && activeColumn !== overColumn) {
        onMove(active.id as string, activeColumn, overColumn);
      }
    },
    [columns, findColumn, onMove]
  );

  const allItems = columns.flatMap((col) => col.items);
  const activeItem = activeId ? allItems.find((i) => i.id === activeId) : null;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }}>
        {columns.map((col) => (
          <SortableContext key={col.id} items={col.items.map((i) => i.id)} strategy={verticalListSortingStrategy}>
            <DroppableColumn id={col.id} title={col.title} color={col.color} count={col.items.length}>
              {col.items.map((item) => (
                <SortableItem key={item.id} id={item.id}>
                  {renderCard(item)}
                </SortableItem>
              ))}
              {col.items.length === 0 && (
                <p className="py-8 text-center text-xs text-slate-400">
                  Buraya sürükleyin
                </p>
              )}
            </DroppableColumn>
          </SortableContext>
        ))}
      </div>
      <DragOverlay>
        {activeItem && renderOverlay ? renderOverlay(activeItem) : null}
      </DragOverlay>
    </DndContext>
  );
}
