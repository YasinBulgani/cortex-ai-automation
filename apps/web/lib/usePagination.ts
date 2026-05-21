"use client";

import { useState, useMemo } from "react";

interface UsePaginationOptions {
  initialPage?: number;
  pageSize?: number;
}

interface UsePaginationResult<T> {
  page: number;
  pageSize: number;
  totalPages: number;
  paginated: T[];
  setPage: (page: number) => void;
  next: () => void;
  prev: () => void;
  first: () => void;
  last: () => void;
  hasNext: boolean;
  hasPrev: boolean;
}

export function usePagination<T>(
  data: T[],
  options: UsePaginationOptions = {}
): UsePaginationResult<T> {
  const { initialPage = 1, pageSize = 20 } = options;
  const [page, setPageState] = useState(initialPage);

  const totalPages = Math.max(1, Math.ceil(data.length / pageSize));

  const safePage = Math.min(Math.max(1, page), totalPages);

  const paginated = useMemo(
    () => data.slice((safePage - 1) * pageSize, safePage * pageSize),
    [data, safePage, pageSize]
  );

  const setPage = (p: number) => setPageState(Math.min(Math.max(1, p), totalPages));

  return {
    page: safePage,
    pageSize,
    totalPages,
    paginated,
    setPage,
    next: () => setPage(safePage + 1),
    prev: () => setPage(safePage - 1),
    first: () => setPage(1),
    last: () => setPage(totalPages),
    hasNext: safePage < totalPages,
    hasPrev: safePage > 1,
  };
}
