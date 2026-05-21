"use client";

import * as React from "react";
import { cn } from "../utils/cn";

export type SkeletonShape = "rect" | "circle" | "text";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  shape?: SkeletonShape;
  /** Animasyonu kapat (test/snapshot kararlılığı için) */
  noAnimation?: boolean;
}

export function Skeleton({ shape = "rect", noAnimation, className, ...rest }: SkeletonProps) {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-live="polite"
      className={cn(
        "bg-border/50",
        !noAnimation && "animate-pulse",
        shape === "circle" && "rounded-full",
        shape === "rect"   && "rounded",
        shape === "text"   && "rounded h-3 w-full",
        className,
      )}
      {...rest}
    >
      <span className="sr-only">Yükleniyor</span>
    </div>
  );
}

export interface SkeletonTextProps {
  lines?: number;
  className?: string;
  /** Son satır kısa olsun mu (gerçek metin gibi) */
  lastShorter?: boolean;
}

export function SkeletonText({ lines = 3, className, lastShorter = true }: SkeletonTextProps) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, i) => {
        const isLast = i === lines - 1;
        return (
          <Skeleton
            key={i}
            shape="text"
            className={cn(isLast && lastShorter && "w-3/4")}
          />
        );
      })}
    </div>
  );
}

export interface SkeletonCardProps {
  className?: string;
  /** Avatar + 2 satır metin örnek deseni */
  withAvatar?: boolean;
}

export function SkeletonCard({ className, withAvatar }: SkeletonCardProps) {
  return (
    <div className={cn("rounded-lg border border-border p-4", className)}>
      {withAvatar ? (
        <div className="flex items-center gap-3">
          <Skeleton shape="circle" className="h-10 w-10" />
          <div className="min-w-0 flex-1 space-y-2">
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-3 w-20" />
          </div>
        </div>
      ) : (
        <>
          <Skeleton className="h-3 w-20" />
          <Skeleton className="mt-3 h-8 w-16" />
        </>
      )}
    </div>
  );
}
