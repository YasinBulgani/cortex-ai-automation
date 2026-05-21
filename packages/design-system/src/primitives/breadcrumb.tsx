"use client";

import * as React from "react";
import { cn } from "../utils/cn";

export interface BreadcrumbItem {
  label: React.ReactNode;
  /** URL veya tıklama handler */
  href?: string;
  onClick?: () => void;
  /** Sol ikon */
  icon?: React.ReactNode;
}

export interface BreadcrumbProps extends Omit<React.HTMLAttributes<HTMLElement>, "children"> {
  items: ReadonlyArray<BreadcrumbItem>;
  /** Ayırıcı (default "/") */
  separator?: React.ReactNode;
  /** Maks öğe (geçilince ortadakileri "…" ile kıs) */
  maxItems?: number;
  /** Aria label */
  label?: string;
}

export function Breadcrumb({
  items,
  separator = "/",
  maxItems,
  label = "Breadcrumb",
  className,
  ...rest
}: BreadcrumbProps) {
  const collapsed = maxItems && items.length > maxItems
    ? [items[0], { label: "…", isEllipsis: true } as BreadcrumbItem & { isEllipsis: true }, ...items.slice(items.length - (maxItems - 2))]
    : items;

  return (
    <nav aria-label={label} className={cn("text-sm", className)} {...rest}>
      <ol className="flex flex-wrap items-center gap-1.5 text-fg-muted">
        {collapsed.map((it, i) => {
          const isLast = i === collapsed.length - 1;
          const isEllipsis = "isEllipsis" in it;
          return (
            <React.Fragment key={i}>
              <li className={cn("inline-flex items-center gap-1.5", isLast && "text-fg font-medium")}>
                {it.icon}
                {isEllipsis ? (
                  <span aria-hidden>{it.label}</span>
                ) : it.href ? (
                  <a
                    href={it.href}
                    onClick={it.onClick}
                    aria-current={isLast ? "page" : undefined}
                    className={cn(
                      isLast ? "" : "hover:text-fg transition-colors hover:underline underline-offset-4",
                    )}
                  >
                    {it.label}
                  </a>
                ) : (
                  <span
                    role={it.onClick ? "button" : undefined}
                    tabIndex={it.onClick ? 0 : undefined}
                    onClick={it.onClick}
                    onKeyDown={it.onClick ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); it.onClick?.(); } } : undefined}
                    aria-current={isLast ? "page" : undefined}
                    className={cn(
                      it.onClick && "cursor-pointer hover:text-fg transition-colors",
                    )}
                  >
                    {it.label}
                  </span>
                )}
              </li>
              {!isLast && (
                <li aria-hidden className="text-fg-subtle">{separator}</li>
              )}
            </React.Fragment>
          );
        })}
      </ol>
    </nav>
  );
}
