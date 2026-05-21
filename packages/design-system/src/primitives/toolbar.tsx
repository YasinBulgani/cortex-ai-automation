"use client";

import * as React from "react";
import { cn } from "../utils/cn";

export interface ToolbarProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Aria label */
  label?: string;
  /** Yön */
  orientation?: "horizontal" | "vertical";
}

/**
 * Toolbar — grup butonları + separator için container.
 * role=toolbar; ToolbarSeparator ile parçalı.
 */
export function Toolbar({
  label,
  orientation = "horizontal",
  className,
  children,
  ...rest
}: ToolbarProps) {
  return (
    <div
      role="toolbar"
      aria-label={label}
      aria-orientation={orientation}
      className={cn(
        "inline-flex items-center gap-1 rounded-lg border border-border bg-surface-raised p-1",
        orientation === "vertical" && "flex-col",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

export interface ToolbarSeparatorProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "horizontal" | "vertical";
}

export function ToolbarSeparator({
  orientation = "vertical",
  className,
  ...rest
}: ToolbarSeparatorProps) {
  return (
    <div
      role="separator"
      aria-orientation={orientation}
      className={cn(
        "bg-border",
        orientation === "vertical" ? "self-stretch w-px mx-0.5" : "h-px w-full my-0.5",
        className,
      )}
      {...rest}
    />
  );
}

export interface ToolbarGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Aria label group için */
  label?: string;
}

export function ToolbarGroup({ label, className, children, ...rest }: ToolbarGroupProps) {
  return (
    <div
      role="group"
      aria-label={label}
      className={cn("inline-flex items-center gap-0.5", className)}
      {...rest}
    >
      {children}
    </div>
  );
}
