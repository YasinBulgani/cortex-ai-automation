"use client";
import React from "react";

type Cols = 2 | 3 | 4 | 5 | 6;

interface MetricRowProps {
  cols?: Cols;
  gap?: "sm" | "md";
  className?: string;
  children: React.ReactNode;
}

const colMap: Record<Cols, string> = {
  2: "grid-cols-1 sm:grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
  4: "grid-cols-2 lg:grid-cols-4",
  5: "grid-cols-2 lg:grid-cols-5",
  6: "grid-cols-2 lg:grid-cols-3 xl:grid-cols-6",
};

const gapMap = { sm: "gap-2", md: "gap-3" };

/**
 * Responsive wrapper grid for StatCards / metric tiles.
 * Keeps spacing + breakpoints consistent across P1 pages.
 */
export function MetricRow({ cols = 4, gap = "md", className = "", children }: MetricRowProps) {
  return (
    <div className={`grid ${colMap[cols]} ${gapMap[gap]} ${className}`}>
      {children}
    </div>
  );
}
