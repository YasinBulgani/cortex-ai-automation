"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "@/lib/api";

interface UseFetchOptions {
  enabled?: boolean;
  deps?: unknown[];
}

interface UseFetchResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useFetch<T>(
  path: string | null,
  options: UseFetchOptions = {}
): UseFetchResult<T> {
  const { enabled = true, deps = [] } = options;
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetch = useCallback(() => {
    if (!path || !enabled) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    apiFetch<T>(path, { signal: controller.signal })
      .then((result) => {
        setData(result);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        setLoading(false);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, enabled, ...deps]);

  useEffect(() => {
    fetch();
    return () => abortRef.current?.abort();
  }, [fetch]);

  return { data, loading, error, refresh: fetch };
}

interface UseMutateOptions<TBody, TResult> {
  onSuccess?: (result: TResult) => void;
  onError?: (error: string) => void;
  method?: "POST" | "PUT" | "PATCH" | "DELETE";
}

interface UseMutateResult<TBody, TResult> {
  mutate: (body?: TBody) => Promise<TResult | null>;
  loading: boolean;
  error: string | null;
}

export function useMutate<TBody = unknown, TResult = unknown>(
  path: string,
  options: UseMutateOptions<TBody, TResult> = {}
): UseMutateResult<TBody, TResult> {
  const { onSuccess, onError, method = "POST" } = options;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutate = useCallback(
    async (body?: TBody): Promise<TResult | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await apiFetch<TResult>(path, {
          method,
          json: body,
        });
        onSuccess?.(result);
        return result;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
        onError?.(msg);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [path, method, onSuccess, onError]
  );

  return { mutate, loading, error };
}
