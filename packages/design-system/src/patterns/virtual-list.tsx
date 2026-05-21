"use client";

import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { cn } from "../utils/cn";

interface VirtualListProps<T> {
  items: T[];
  estimateSize?: number;
  overscan?: number;
  renderItem: (item: T, index: number) => React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  itemKey?: (item: T, index: number) => string | number;
}

/**
 * VirtualList — büyük listeler için sanallaştırılmış render.
 *
 * 3157+ öğeyle bile akıcı kalır — sadece görünen ~20 satır DOM'a basar.
 *
 * Kullanım:
 *   <VirtualList
 *     items={projects}
 *     estimateSize={64}
 *     renderItem={(p) => <ProjectRow project={p} />}
 *     itemKey={(p) => p.id}
 *     className="h-[600px]"
 *   />
 */
export function VirtualList<T>({
  items,
  estimateSize = 60,
  overscan = 8,
  renderItem,
  className,
  style,
  itemKey,
}: VirtualListProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan,
  });

  return (
    <div
      ref={parentRef}
      className={cn("overflow-y-auto", className)}
      style={style}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: "100%",
          position: "relative",
        }}
      >
        {virtualizer.getVirtualItems().map(virtualItem => {
          const item = items[virtualItem.index];
          const key = itemKey?.(item, virtualItem.index) ?? virtualItem.key;
          return (
            <div
              key={key}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: `${virtualItem.size}px`,
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              {renderItem(item, virtualItem.index)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
