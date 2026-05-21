"use client";

import { useParams } from "next/navigation";

export function useRouteParam(name: string): string {
  const params = useParams<Record<string, string | string[]>>();
  const value = params?.[name];

  if (Array.isArray(value)) {
    return value[0] ?? "";
  }

  return value ?? "";
}
