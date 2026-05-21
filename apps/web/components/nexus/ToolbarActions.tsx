"use client";
import React from "react";

interface ToolbarActionsProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Standard horizontal action group for PageHeader `right` slot.
 * Handles spacing + shrink behavior; consumers supply buttons/links.
 */
export function ToolbarActions({ children, className = "" }: ToolbarActionsProps) {
  return (
    <div className={`flex items-center gap-2 shrink-0 ${className}`}>
      {children}
    </div>
  );
}
