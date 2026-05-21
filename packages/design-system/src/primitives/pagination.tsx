"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing } from "../tokens/design-tokens";

export interface PaginationProps extends Omit<React.HTMLAttributes<HTMLElement>, "onChange"> {
  /** 1-tabanlı mevcut sayfa */
  page: number;
  /** Toplam sayfa sayısı */
  totalPages: number;
  /** Sayfa değişti */
  onPageChange: (page: number) => void;
  /** Sayfa numaralarının her iki tarafında kaç sayfa göster (default 1) */
  siblingCount?: number;
  /** İlk ve son sayfa her zaman görünsün mü (default true) */
  showEdges?: boolean;
  /** Aria label */
  label?: string;
}

const ELLIPSIS = "…";

function range(start: number, end: number): number[] {
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
}

function paginationRange(
  page: number,
  totalPages: number,
  siblingCount: number,
  showEdges: boolean,
): Array<number | "…"> {
  const totalNumbers = siblingCount * 2 + (showEdges ? 5 : 3); // first + last + current + siblings + 2 ellipsis
  if (totalPages <= totalNumbers) return range(1, totalPages);

  const leftSibling = Math.max(page - siblingCount, showEdges ? 2 : 1);
  const rightSibling = Math.min(page + siblingCount, showEdges ? totalPages - 1 : totalPages);

  const showLeftEllipsis = leftSibling > (showEdges ? 2 : 1) + 1;
  const showRightEllipsis = rightSibling < (showEdges ? totalPages - 1 : totalPages) - 1;

  const out: Array<number | "…"> = [];
  if (showEdges) out.push(1);
  if (showLeftEllipsis) out.push(ELLIPSIS);
  else if (showEdges) {
    // contiguous: fill in 2..leftSibling-1
    for (let i = 2; i < leftSibling; i++) out.push(i);
  }
  for (let i = leftSibling; i <= rightSibling; i++) out.push(i);
  if (showRightEllipsis) out.push(ELLIPSIS);
  else if (showEdges) {
    for (let i = rightSibling + 1; i < totalPages; i++) out.push(i);
  }
  if (showEdges) out.push(totalPages);
  return out;
}

export function Pagination({
  page,
  totalPages,
  onPageChange,
  siblingCount = 1,
  showEdges = true,
  label = "Sayfalama",
  className,
  ...rest
}: PaginationProps) {
  const goTo = (p: number) => {
    if (p < 1 || p > totalPages || p === page) return;
    onPageChange(p);
  };

  if (totalPages <= 1) return null;
  const pages = paginationRange(page, totalPages, siblingCount, showEdges);

  return (
    <nav aria-label={label} className={cn("inline-flex items-center gap-1", className)} {...rest}>
      <PageButton
        ariaLabel="Önceki sayfa"
        disabled={page <= 1}
        onClick={() => goTo(page - 1)}
      >
        ‹
      </PageButton>
      {pages.map((p, i) =>
        p === ELLIPSIS ? (
          <span
            key={`e-${i}`}
            aria-hidden
            className="px-2 text-fg-subtle"
          >
            {ELLIPSIS}
          </span>
        ) : (
          <PageButton
            key={p}
            ariaLabel={`Sayfa ${p}`}
            active={p === page}
            ariaCurrent={p === page ? "page" : undefined}
            onClick={() => goTo(p)}
          >
            {p}
          </PageButton>
        ),
      )}
      <PageButton
        ariaLabel="Sonraki sayfa"
        disabled={page >= totalPages}
        onClick={() => goTo(page + 1)}
      >
        ›
      </PageButton>
    </nav>
  );
}

function PageButton({
  children,
  active,
  disabled,
  ariaLabel,
  ariaCurrent,
  onClick,
}: {
  children: React.ReactNode;
  active?: boolean;
  disabled?: boolean;
  ariaLabel: string;
  ariaCurrent?: "page";
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      aria-current={ariaCurrent}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "inline-flex h-8 min-w-8 items-center justify-center rounded px-2 text-sm transition-colors",
        active
          ? "bg-brand-primary text-brand-on-primary"
          : "text-fg-muted hover:bg-surface-overlay hover:text-fg",
        "disabled:cursor-not-allowed disabled:opacity-40",
        focusRing,
      )}
    >
      {children}
    </button>
  );
}
